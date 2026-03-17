# src/dialogue/dialogue_parser.py
import csv
import re
import logging
from pathlib import Path
from typing import Iterator, Optional, List, Dict
from io import StringIO

from src.dialogue.schemas import ParsedDialogue, DialogueTurn

logger = logging.getLogger(__name__)


class DialogueCSVParser:
    """
    Parses MTS-Dialog CSV into structured ParsedDialogue objects.
    Supports deduplication of dialogue IDs.
    """
    
    SPEAKER_PATTERN = re.compile(
        r'\n*\s*(Doctor|Patient)\s*:\s*', 
        re.IGNORECASE | re.MULTILINE
    )
    
    COLUMN_MAPPINGS = {
        'id': ['id', 'dialogue_id', 'dialogueid', '\ufeffid'],
        'dialogue': ['dialogue', 'text', 'conversation', 'dialog'],
        'reference_summary': ['reference summary', 'reference_summary', 'summary'],
        'automatic_summary': ['automatic summary', 'automatic_summary', 'auto_summary'],
    }
    
    def __init__(self, csv_path: str | Path, encoding: str = 'utf-8-sig'):
        self.csv_path = Path(csv_path)
        self.encoding = encoding
        self.column_map = {}
        
    def _detect_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Map actual CSV column names to our internal names"""
        mapping = {}
        fieldnames_lower = [f.lower().strip() if f else '' for f in fieldnames]
        
        for internal_name, variants in self.COLUMN_MAPPINGS.items():
            for variant in variants:
                if variant.lower() in fieldnames_lower:
                    idx = fieldnames_lower.index(variant.lower())
                    mapping[internal_name] = fieldnames[idx]
                    break
        
        # Fallbacks
        if 'id' not in mapping and fieldnames:
            mapping['id'] = fieldnames[0]
        if 'dialogue' not in mapping and len(fieldnames) > 1:
            mapping['dialogue'] = fieldnames[1]
            
        return mapping
    
    def _parse_turns(self, raw_dialogue: str) -> List[DialogueTurn]:
        """Split raw dialogue text into structured turns"""
        text = raw_dialogue.strip()
        if not text:
            return []
            
        parts = self.SPEAKER_PATTERN.split(text)
        
        turns = []
        i = 1
        turn_idx = 0
        
        while i < len(parts) - 1:
            speaker = parts[i].strip().capitalize()
            utterance = parts[i + 1].strip()
            
            if speaker in ['Doctor', 'Patient'] and utterance:
                turns.append(DialogueTurn(
                    speaker=speaker,
                    text=utterance,
                    turn_index=turn_idx
                ))
                turn_idx += 1
            
            i += 2
        
        # Fallback: line-by-line alternation if no speaker labels found
        if not turns:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for idx, line in enumerate(lines):
                speaker = "Doctor" if idx % 2 == 0 else "Patient"
                turns.append(DialogueTurn(speaker=speaker, text=line, turn_index=idx))
        
        return turns
    
    def _check_consistency(self, turns: List[DialogueTurn]) -> Dict[str, bool]:
        """Simple quality checks"""
        if not turns:
            return {"is_balanced": False, "has_patient_responses": False}
        
        speakers = [t.speaker for t in turns]
        patient_count = speakers.count("Patient")
        doctor_count = speakers.count("Doctor")
        
        return {
            "is_balanced": 0.33 <= (patient_count / max(doctor_count, 1)) <= 3.0,
            "has_patient_responses": patient_count > 0
        }
    
    def parse_one(self, row: Dict, row_num: int) -> Optional[ParsedDialogue]:
        """Parse single CSV row into ParsedDialogue"""
        try:
            dialogue_id = row.get(self.column_map.get('id', 'ID'), '').strip()
            raw = row.get(self.column_map.get('dialogue', 'Dialogue'), '').strip()
            ref_summary = row.get(self.column_map.get('reference_summary', 'Reference Summary'), '')
            auto_summary = row.get(self.column_map.get('automatic_summary', 'Automatic Summary'), '')
            
            if not dialogue_id:
                logger.warning(f"Row {row_num}: Empty ID")
                return None
                
            if not raw:
                logger.warning(f"Row {row_num} (ID {dialogue_id}): Empty dialogue")
                return None
            
            turns = self._parse_turns(raw)
            quality = self._check_consistency(turns)
            
            return ParsedDialogue(
                dialogue_id=dialogue_id,
                raw_text=raw,
                turns=turns,
                patient_utterances=[t.text for t in turns if t.speaker == "Patient"],
                doctor_utterances=[t.text for t in turns if t.speaker == "Doctor"],
                reference_summary=ref_summary,
                automatic_summary=auto_summary,
                is_balanced=quality["is_balanced"],
                has_patient_responses=quality["has_patient_responses"]
            )
        except Exception as e:
            dialogue_id = row.get(self.column_map.get('id', 'ID'), 'UNKNOWN')
            logger.error(f"Row {row_num} (ID {dialogue_id}): {e}")
            return None
    
    def parse_all(self, deduplicate: bool = True) -> Iterator[ParsedDialogue]:
        """
        Generator: parse entire CSV file with optional deduplication.
        
        Args:
            deduplicate: If True, keep only first occurrence of each dialogue_id
        """
        with open(self.csv_path, 'r', encoding=self.encoding, newline='') as f:
            content = f.read()
        
        with StringIO(content) as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                logger.error("CSV file has no headers")
                return
            
            self.column_map = self._detect_columns(reader.fieldnames)
            logger.info(f"Column mapping: {self.column_map}")
            
            seen_ids = {}  # dialogue_id -> first row_num seen
            total_rows = 0
            for row_num, row in enumerate(reader, 1):
                total_rows = row_num
                dialogue_id = row.get(self.column_map.get('id', 'ID'), '').strip()
                
                if deduplicate and dialogue_id in seen_ids:
                    logger.debug(f"Skipping duplicate ID {dialogue_id} (first seen at row {seen_ids[dialogue_id]}, now row {row_num})")
                    continue
                
                if deduplicate:
                    seen_ids[dialogue_id] = row_num
                    
                parsed = self.parse_one(row, row_num)
                if parsed:
                    yield parsed
            
            if deduplicate:
                logger.info(f"✅ Deduplication: {len(seen_ids)} unique IDs kept, {total_rows - len(seen_ids)} duplicates skipped")
            else:
                logger.info(f"📊 Processed {total_rows} rows (no deduplication)")