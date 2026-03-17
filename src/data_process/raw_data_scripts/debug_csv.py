import csv

with open('data/raw/MTS-Dialog-Automatic-Summaries-ValidationSet.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print("✅ Column names:", reader.fieldnames)
    print("✅ First row keys:", list(next(reader).keys()))