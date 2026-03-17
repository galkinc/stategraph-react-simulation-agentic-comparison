# debug_errors.py
import json

with open('data/processed/dialogues_parsed.report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)

print(f"📊 Total: {report['total']}")
print(f"✅ Valid: {report['valid']}")
print(f"⚠️  Warnings: {len(report['warnings'])}")
print(f"❌ Errors: {len(report['errors'])}")

print("\n--- First 10 Errors ---")
for err in report['errors'][:10]:
    print(f"  • {err}")

print("\n--- First 10 Warnings ---")
for warn in report['warnings'][:10]:
    print(f"  • {warn}")