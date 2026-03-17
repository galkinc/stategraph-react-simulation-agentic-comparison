# src/profiles/builder.py
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, List

from src.profile.schemas import PatientProfile, ComprehendEntity

logger = logging.getLogger(__name__)


class PatientProfileBuilder:
    """
    Builds PatientProfile by merging:
    1. Parsed dialogues from JSONL
    2. Comprehend Medical entities from output.json files
    """
    
    CATEGORY_MAPPING = {
        "MEDICAL_CONDITION": "conditions",
        "ANATOMY": "anatomy", 
        "MEDICATION": "medications",
        "TEST_TREATMENT_PROCEDURE": "treatments",
        "TIME_EXPRESSION": "time_expressions",
        "DX_NAME": "conditions",
        "SYMPTOM": "conditions",
        "AGE": "age",
    }
    
    def __init__(self, 
                 comprehend_dir: str | Path, 
                 dialogues_jsonl: str | Path | None = None):
        self.comprehend_path = Path(comprehend_dir)
        self.dialogues_path = Path(dialogues_jsonl) if dialogues_jsonl else None
        self.dialogues_cache: Dict[str, dict] = {}  # dialogue_id -> parsed dialogue
        
        if self.dialogues_path and self.dialogues_path.exists():
            self._load_dialogues_cache()
    
    def _load_dialogues_cache(self) -> None:
        """Load all parsed dialogues into memory for fast lookup"""
        logger.info(f"Loading dialogues from {self.dialogues_path}...")
        count = 0
        with open(self.dialogues_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    dialogue = json.loads(line)
                    dialogue_id = dialogue.get('dialogue_id', '')
                    self.dialogues_cache[dialogue_id] = dialogue
                    count += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse dialogue line: {e}")
        logger.info(f"✅ Loaded {count} dialogues into cache")
    
    def _extract_dialogue_id(self, folder_name: str) -> str:
        """
        Parse dialogue ID from folder name like '48_dialogue_99'.
        Returns '99' from '48_dialogue_99'
        """
        parts = folder_name.split('_')
        return parts[-1] if len(parts) >= 2 else folder_name
    
    def _parse_comprehend_output(self, output_path: Path) -> List[ComprehendEntity]:
        """Parse single output.json and normalize entities"""
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entities = []
            for item in data.get("Entities", []):
                traits = [t.get("Name") for t in item.get("Traits", []) if t.get("Name")]
                
                entities.append(ComprehendEntity(
                    text=item["Text"],
                    category=item["Category"],
                    entity_type=item.get("Type"),
                    score=item["Score"],
                    traits=traits,
                    begin_offset=item.get("BeginOffset"),
                    end_offset=item.get("EndOffset")
                ))
            return entities
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Failed to parse {output_path}: {e}")
            return []
    
    def _aggregate_entities(self, entities: List[ComprehendEntity], 
                           score_threshold: float = 0.6) -> dict:
        """Group entities by category with score filtering and negation handling"""
        aggregated = {
            "conditions": [], "negated_conditions": [], "anatomy": [],
            "medications": [], "treatments": [], "time_expressions": [],
            "age": None, "gender": None
        }
        
        for ent in entities:
            if ent.score < score_threshold:
                continue
            
            category = ent.category
            text = ent.text
            
            # Handle age separately
            if category == "AGE":
                if not aggregated["age"]:
                    aggregated["age"] = text
                continue
            
            # Handle gender detection
            if text.lower() in ["male", "female", "man", "woman", "boy", "girl"]:
                if not aggregated["gender"]:
                    aggregated["gender"] = text.capitalize()
                continue
            
            target_field = self.CATEGORY_MAPPING.get(category)
            if not target_field:
                continue
            
            # Handle negation for medical conditions
            if "NEGATION" in ent.traits and target_field == "conditions":
                aggregated["negated_conditions"].append(text)
            else:
                aggregated[target_field].append(text)
        
        # Deduplicate while preserving order
        for key in ["conditions", "negated_conditions", "anatomy", "medications", "treatments", "time_expressions"]:
            aggregated[key] = list(dict.fromkeys(aggregated[key]))
            
        return aggregated
    
    def _extract_demographics_from_dialogue(self, dialogue_data: dict) -> dict:
        """Extract age/gender from parsed dialogue text"""
        demo = {"age": None, "gender": None}
        
        raw_text = dialogue_data.get('raw_text', '')
        ref_summary = dialogue_data.get('reference_summary', '')
        
        # Combine sources for better extraction
        search_text = f"{raw_text} {ref_summary}".lower()
        
        # Age extraction
        age_patterns = [
            r'(\d+)-?year(?:\s*-|\s+old)',
            r'(\d+)\s+years?\s+old',
            r'age\s*(\d+)',
            r"(\d+)-year-old",
        ]
        for pattern in age_patterns:
            match = re.search(pattern, search_text, re.I)
            if match:
                demo["age"] = match.group(1)
                break
        
        # Gender extraction
        gender_keywords = {
            "female": ["female", "woman", "mother", "daughter", "she", "her"],
            "male": ["male", "man", "father", "son", "he", "him"],
        }
        for gender, keywords in gender_keywords.items():
            if any(kw in search_text for kw in keywords):
                demo["gender"] = gender.capitalize()
                break
        
        return demo
    
    def build_profile(self, 
                     dialogue_folder_name: str, 
                     score_threshold: float = 0.6,
                     require_dialogue: bool = True) -> Optional[PatientProfile]:
        """
        Build a complete PatientProfile by merging dialogue + Comprehend data.
        
        Args:
            dialogue_folder_name: e.g. '48_dialogue_99'
            score_threshold: Minimum confidence score for entity inclusion
            require_dialogue: If True, skip profile if dialogue not found
            
        Returns:
            PatientProfile or None if building failed
        """
        # 1. Extract dialogue ID from folder name
        dialogue_id = self._extract_dialogue_id(dialogue_folder_name)
        
        # 2. Load parsed dialogue from cache
        dialogue_data = self.dialogues_cache.get(dialogue_id)
        if not dialogue_data:
            if require_dialogue:
                logger.warning(f"No dialogue found for ID {dialogue_id} (folder: {dialogue_folder_name})")
                return None
            else:
                dialogue_data = {}
                logger.info(f"Creating minimal profile for ID {dialogue_id} (no dialogue)")
        
        # 3. Load Comprehend entities
        folder_path = self.comprehend_path / dialogue_folder_name
        output_file = folder_path / "output.json"
        entities = self._parse_comprehend_output(output_file) if folder_path.exists() else []
        
        # 4. Aggregate entities
        aggregated = self._aggregate_entities(entities, score_threshold)
        
        # 5. Extract demographics from dialogue
        demo_from_dialogue = self._extract_demographics_from_dialogue(dialogue_data)
        
        # Merge demographics (Comprehend entities take precedence)
        age = aggregated["age"] or demo_from_dialogue["age"]
        gender = aggregated["gender"] or demo_from_dialogue["gender"]
        
        # 6. Build allowed/forbidden topics
        allowed = (
            aggregated["conditions"] + 
            aggregated["anatomy"] + 
            aggregated["medications"] +
            aggregated["treatments"]
        )
        forbidden = aggregated["negated_conditions"]
        
        # 7. Create profile
        return PatientProfile(
            dialogue_id=dialogue_id,
            raw_dialogue=dialogue_data.get('raw_text', ''),
            conditions=aggregated["conditions"],
            negated_conditions=aggregated["negated_conditions"],
            anatomy=aggregated["anatomy"],
            medications=aggregated["medications"],
            treatments=aggregated["treatments"],
            time_expressions=aggregated["time_expressions"],
            patient_utterances=dialogue_data.get('patient_utterances', []),
            doctor_utterances=dialogue_data.get('doctor_utterances', []),
            age=age,
            gender=gender,
            allowed_topics=list(dict.fromkeys(allowed)),
            forbidden_facts=list(dict.fromkeys(forbidden)),
            comprehend_entities_count=len(entities),
            dialogue_turns_count=len(dialogue_data.get('turns', []))
        )
    
    def build_all_profiles(self, 
                          output_path: str | Path,
                          score_threshold: float = 0.6,
                          overwrite: bool = False) -> dict:
        """
        Build profiles for all dialogue folders and save to JSONL.
        
        Returns:
            Statistics dict with counts
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.exists() and not overwrite:
            logger.warning(f"{output_path} exists. Use overwrite=True to replace.")
            return {"status": "skipped"}
        
        # Find all dialogue folders
        folders = [d.name for d in self.comprehend_path.iterdir() if d.is_dir()]
        logger.info(f"Found {len(folders)} Comprehend folders")
        
        stats = {
            "total_folders": len(folders),
            "profiles_built": 0,
            "skipped_no_dialogue": 0,
            "skipped_no_entities": 0,
            "errors": 0
        }
        
        with open(output_path, 'w', encoding='utf-8') as out:
            for folder_name in sorted(folders):
                try:
                    profile = self.build_profile(
                        folder_name, 
                        score_threshold=score_threshold,
                        require_dialogue=True
                    )
                    
                    if profile:
                        out.write(profile.model_dump_json(ensure_ascii=False) + '\n')
                        stats["profiles_built"] += 1
                        
                        if profile.comprehend_entities_count == 0:
                            stats["skipped_no_entities"] += 1
                    else:
                        stats["skipped_no_dialogue"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to build profile for {folder_name}: {e}")
                    stats["errors"] += 1
        
        logger.info(f"✅ Built {stats['profiles_built']} profiles -> {output_path}")
        return stats