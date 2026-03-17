# src/dialogue/build_dataset.py
#!/usr/bin/env python3
import json
import argparse
import logging
from pathlib import Path

from dialogue.parser import DialogueCSVParser
from src.dialogue.schemas import ParsedDialogue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_parsed_dialogues(dialogues: list[ParsedDialogue]) -> dict:
    """Run consistency checks and return report"""
    report = {
        "total": len(dialogues),
        "valid": 0,
        "warnings": [],
        "errors": []
    }
    
    for d in dialogues:
        if not d.patient_utterances:
            report["errors"].append(f"ID {d.dialogue_id}: No patient utterances found")
            continue
        
        speakers = [t.speaker for t in d.turns]
        for i in range(len(speakers) - 1):
            if speakers[i] == speakers[i+1]:
                report["warnings"].append(
                    f"ID {d.dialogue_id}: Consecutive {speakers[i]} turns at index {i}"
                )
                break
        
        total_words = sum(len(t.text.split()) for t in d.turns)
        if total_words < 20:
            report["warnings"].append(f"ID {d.dialogue_id}: Very short dialogue ({total_words} words)")
        elif total_words > 2000:
            report["warnings"].append(f"ID {d.dialogue_id}: Very long dialogue ({total_words} words)")
        
        report["valid"] += 1
    
    return report


def main(input_csv: str, output_jsonl: str, overwrite: bool = False, deduplicate: bool = True):
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if output_path.exists() and not overwrite:
        logger.warning(f"{output_path} exists. Use --overwrite to replace.")
        return
    
    parser = DialogueCSVParser(input_csv)
    dialogues = []
    seen_ids = set()
    
    logger.info(f"Parsing {input_csv} (deduplicate={deduplicate})...")
    with open(output_path, 'w', encoding='utf-8') as out:
        # Здесь вызывается обновлённый метод parse_all
        for parsed in parser.parse_all(deduplicate=deduplicate):
            dialogues.append(parsed)
            seen_ids.add(parsed.dialogue_id)
            out.write(parsed.model_dump_json(ensure_ascii=False) + '\n')
    
    logger.info(f"🆔 Unique dialogue IDs written: {len(seen_ids)}")
    logger.info(f"📝 Total records written: {len(dialogues)}")
    
    report = validate_parsed_dialogues(dialogues)
    
    report_path = output_path.with_suffix('.report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Valid: {report['valid']}/{report['total']}")
    if report['warnings']:
        logger.warning(f"⚠️  {len(report['warnings'])} warnings")
    if report['errors']:
        logger.error(f"❌ {len(report['errors'])} errors")
    
    if dialogues:
        sample = dialogues[0]
        print(f"\n📋 Sample (ID {sample.dialogue_id}):")
        print(f"   Patient utterances: {len(sample.patient_utterances)}")
        
if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--input", required=True, help="Path to input CSV")
    argparser.add_argument("--output", required=True, help="Path to output JSONL")
    argparser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    argparser.add_argument("--no-dedup", action="store_true", help="Keep duplicate dialogue IDs")
    args = argparser.parse_args()
    
    main(
        args.input, 
        args.output, 
        args.overwrite, 
        deduplicate=not args.no_dedup
    )