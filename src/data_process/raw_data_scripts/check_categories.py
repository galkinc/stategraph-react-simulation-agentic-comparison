import json
from pathlib import Path
from collections import defaultdict

RAW_DIR = r"data\raw_comprehend\19_02_2026_1"
MIN_SCORE = 0.5 

# category -> type -> set of dialogue_ids (coverage)
category_coverage   = defaultdict(set)
type_coverage       = defaultdict(lambda: defaultdict(set))
trait_coverage      = defaultdict(set)
negation_coverage   = defaultdict(set)  # trait NEGATION

total_dialogues = 0

for folder in sorted(Path(RAW_DIR).iterdir()):
    output_path = folder / "output.json"
    if not output_path.exists():
        continue

    dialogue_id = folder.name  # e.g. "1_dialogue_0"
    total_dialogues += 1

    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)

    for entity in data.get("Entities", []):
        if entity.get("Score", 0) < MIN_SCORE:
            continue

        cat  = entity["Category"]
        typ  = entity["Type"]
        traits = [t["Name"] for t in entity.get("Traits", []) if t.get("Score", 0) >= MIN_SCORE]

        category_coverage[cat].add(dialogue_id)
        type_coverage[cat][typ].add(dialogue_id)

        for trait in traits:
            trait_coverage[trait].add(dialogue_id)
            if trait == "NEGATION":
                negation_coverage[cat].add(dialogue_id)


print(f"Total dialogues: {total_dialogues}\n")

print("=== Category coverage (% of dialogues) ===")
for cat, ids in sorted(category_coverage.items(), key=lambda x: -len(x[1])):
    pct = len(ids) / total_dialogues * 100
    print(f"  {cat:<35} {len(ids):>3} / {total_dialogues}  ({pct:.0f}%)")

print("\n=== Type coverage (% of dialogues) ===")
for cat, types in sorted(type_coverage.items(), key=lambda x: -len(x[1])):
    for typ, ids in sorted(types.items(), key=lambda x: -len(x[1])):
        pct = len(ids) / total_dialogues * 100
        print(f"  {cat:<30} | {typ:<35} {len(ids):>3} / {total_dialogues}  ({pct:.0f}%)")

print("\n=== Trait coverage (% of dialogues) ===")
for trait, ids in sorted(trait_coverage.items(), key=lambda x: -len(x[1])):
    pct = len(ids) / total_dialogues * 100
    print(f"  {trait:<25} {len(ids):>3} / {total_dialogues}  ({pct:.0f}%)")

print("\n=== NEGATION by category (% of dialogues) ===")
for cat, ids in sorted(negation_coverage.items(), key=lambda x: -len(x[1])):
    pct = len(ids) / total_dialogues * 100
    print(f"  {cat:<35} {len(ids):>3} / {total_dialogues}  ({pct:.0f}%)")
