import csv
import re
from pathlib import Path

CSV_PATH = r"raw_data\MTS-Dialog-Automatic-Summaries-ValidationSet.csv"
OUTPUT_DIR = "examples"

Path(OUTPUT_DIR).mkdir(exist_ok=True)

seen_ids = set()

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    total = skipped_dup = skipped_no_patient = skipped_short = saved = 0

    for row in reader:
        total += 1
        dialogue_id = row["ID"]

        # dedublication
        if dialogue_id in seen_ids:
            skipped_dup += 1
            continue
        seen_ids.add(dialogue_id)

        dialogue = row["Dialogue"]

        patient_turns = re.findall(
            r"Patient:\s*(.+?)(?=\n\s*Doctor:|\n\s*Patient:|\Z)",
            dialogue,
            flags=re.DOTALL,
        )
        patient_turns = [t.strip() for t in patient_turns if t.strip()]

        if not patient_turns:
            print(f"[SKIP] dialogue_{dialogue_id}: no patient turns")
            skipped_no_patient += 1
            continue

        if len(patient_turns) < 3:
            print(f"[SKIP] dialogue_{dialogue_id}: only {len(patient_turns)} turn(s), too short")
            skipped_short += 1
            continue

        text = "\n".join(patient_turns)
        out_path = Path(OUTPUT_DIR) / f"dialogue_{dialogue_id}.txt"
        out_path.write_text(text, encoding="utf-8")
        print(f"[OK]   dialogue_{dialogue_id}.txt — {len(patient_turns)} turns")
        saved += 1

print(f"""
--- Summary ---
Total CSV rows  : {total}
Duplicates      : {skipped_dup}
No patient turns: {skipped_no_patient}
Too short (<3)  : {skipped_short}
Saved           : {saved}
""")


# import csv
# with open(r"raw_data\MTS-Dialog-Automatic-Summaries-ValidationSet.csv", encoding="utf-8-sig") as f:
#     rows = list(csv.DictReader(f))
# print(f"Total rows: {len(rows)}")
# print(f"Unique IDs: {len(set(r['ID'] for r in rows))}")

# seen_ids = {}
# with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
#     for row in csv.DictReader(f):
#         id_ = row["ID"]
#         if id_ in seen_ids:
#             # проверяем что Dialogue идентичен
#             assert seen_ids[id_] == row["Dialogue"], f"ID {id_} has different content!"
#         else:
#             seen_ids[id_] = row["Dialogue"]

# print("All duplicates are identical — safe to dedup")
