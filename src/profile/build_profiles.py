# src/profiles/build_profiles.py
#!/usr/bin/env python3
"""
Build patient profiles by merging parsed dialogues with Comprehend entities.

Usage:
    uv run python -m src.profiles.build_profiles \
      --comprehend-dir data/raw_comprehend/19_02_2026_1 \
      --dialogues-jsonl data/processed/dialogues_parsed.jsonl \
      --output data/processed/patient_profiles.jsonl
"""
import argparse
import json
import logging
from pathlib import Path

from src.profile.builder import PatientProfileBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(comprehend_dir: str, 
         dialogues_jsonl: str, 
         output: str, 
         overwrite: bool = False,
         score_threshold: float = 0.6):
    
    logger.info("=" * 60)
    logger.info("PATIENT PROFILE BUILDER")
    logger.info("=" * 60)
    
    # Validate inputs
    if not Path(comprehend_dir).exists():
        logger.error(f"Comprehend directory not found: {comprehend_dir}")
        return
    
    if not Path(dialogues_jsonl).exists():
        logger.error(f"Dialogues JSONL not found: {dialogues_jsonl}")
        return
    
    # Build profiles
    builder = PatientProfileBuilder(
        comprehend_dir=comprehend_dir,
        dialogues_jsonl=dialogues_jsonl
    )
    
    stats = builder.build_all_profiles(
        output_path=output,
        score_threshold=score_threshold,
        overwrite=overwrite
    )
    
    # Log summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"📁 Total Comprehend folders: {stats.get('total_folders', 0)}")
    logger.info(f"✅ Profiles built: {stats.get('profiles_built', 0)}")
    logger.info(f"⏭️  Skipped (no dialogue): {stats.get('skipped_no_dialogue', 0)}")
    logger.info(f"⏭️  Skipped (no entities): {stats.get('skipped_no_entities', 0)}")
    logger.info(f"❌ Errors: {stats.get('errors', 0)}")
    
    # Validate output
    output_path = Path(output)
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
        logger.info(f"📄 Output file lines: {line_count}")
        
        # Show sample
        with open(output_path, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line:
                sample = json.loads(first_line)
                logger.info(f"\n📋 Sample profile (ID {sample.get('dialogue_id')}):")
                logger.info(f"   Conditions: {len(sample.get('conditions', []))}")
                logger.info(f"   Medications: {len(sample.get('medications', []))}")
                logger.info(f"   Patient utterances: {len(sample.get('patient_utterances', []))}")
                logger.info(f"   Age: {sample.get('age')}")
                logger.info(f"   Gender: {sample.get('gender')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build patient profiles from dialogues + Comprehend")
    parser.add_argument("--comprehend-dir", required=True, help="Path to Comprehend output directories")
    parser.add_argument("--dialogues-jsonl", required=True, help="Path to parsed dialogues JSONL")
    parser.add_argument("--output", required=True, help="Path to output profiles JSONL")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    parser.add_argument("--score-threshold", type=float, default=0.6, help="Comprehend entity score threshold")
    
    args = parser.parse_args()
    
    main(
        comprehend_dir=args.comprehend_dir,
        dialogues_jsonl=args.dialogues_jsonl,
        output=args.output,
        overwrite=args.overwrite,
        score_threshold=args.score_threshold
    )