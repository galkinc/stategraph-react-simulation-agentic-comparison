# debug_csv_structure.py
import csv

csv_path = 'data/raw/MTS-Dialog-Automatic-Summaries-ValidationSet.csv'

with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    
    ids = []
    row_count = 0
    for row in reader:
        row_count += 1
        ids.append(row.get('ID', 'MISSING'))
        if row_count <= 5:
            print(f"Row {row_count}: ID={row.get('ID')}, Dialogue length={len(row.get('Dialogue', ''))}")
    
    print(f"\n📊 Total CSV records: {row_count}")
    print(f"🔢 Unique IDs: {len(set(ids))}")
    print(f"📋 First 10 IDs: {ids[:10]}")
    print(f"📋 Last 10 IDs: {ids[-10:]}")