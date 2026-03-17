import json

profiles = []
with open('data/processed/patient_profiles.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        profiles.append(json.loads(line))

print(f'📊 Total profiles: {len(profiles)}')
print()

# Статистика по полям
print('📋 Field coverage:')
print(f'  • With age: {sum(1 for p in profiles if p.get("age"))} ({sum(1 for p in profiles if p.get("age"))/len(profiles)*100:.0f}%)')
print(f'  • With gender: {sum(1 for p in profiles if p.get("gender"))} ({sum(1 for p in profiles if p.get("gender"))/len(profiles)*100:.0f}%)')
print(f'  • With conditions: {sum(1 for p in profiles if p.get("conditions"))} ({sum(1 for p in profiles if p.get("conditions"))/len(profiles)*100:.0f}%)')
print(f'  • With medications: {sum(1 for p in profiles if p.get("medications"))} ({sum(1 for p in profiles if p.get("medications"))/len(profiles)*100:.0f}%)')
print(f'  • With anatomy: {sum(1 for p in profiles if p.get("anatomy"))} ({sum(1 for p in profiles if p.get("anatomy"))/len(profiles)*100:.0f}%)')
print()

# Средние значения
print('📈 Averages per profile:')
print(f'  • Conditions: {sum(len(p.get("conditions", [])) for p in profiles) / len(profiles):.1f}')
print(f'  • Medications: {sum(len(p.get("medications", [])) for p in profiles) / len(profiles):.1f}')
print(f'  • Anatomy: {sum(len(p.get("anatomy", [])) for p in profiles) / len(profiles):.1f}')
print(f'  • Patient utterances: {sum(len(p.get("patient_utterances", [])) for p in profiles) / len(profiles):.1f}')
print()

# Показать 3 случайных профиля
import random
print('🎲 Sample profiles:')
for p in random.sample(profiles, min(3, len(profiles))):
    print(f'  ID {p["dialogue_id"]}: age={p.get("age")}, gender={p.get("gender")}, conditions={len(p.get("conditions", []))}')