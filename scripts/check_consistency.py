import re

files = [
    'docs/parts/01_introduction.md',
    'docs/parts/02_experimental_design.md',
    'docs/parts/03_metrics.md',
]

print('Проверка консистентности...')
print()

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Проверка N = 135
    has_n = 'N = 135' in content or 'N=135' in content
    
    # Проверка Coverage > 1.0
    has_coverage_note = 'exceed 1.0' in content or 'exceed 1' in content
    
    # Проверка McNemar exact
    has_exact = 'exact' in content.lower() and 'mcnemar' in content.lower()
    
    # Проверка missing data
    has_missing = 'missing' in content.lower() and ('latency' in content.lower() or '4 runs' in content)
    
    print(f'{f}:')
    print(f'  N = 135: {"✅" if has_n else "❌"}')
    print(f'  Coverage > 1.0: {"✅" if has_coverage_note else "❌"}')
    print(f'  McNemar exact: {"✅" if has_exact else "❌"}')
    print(f'  Missing data: {"✅" if has_missing else "❌"}')
    print()
