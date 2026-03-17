import json
from collections import Counter

with open('data/output/aggregate_metrics.json') as f:
    data = json.load(f)

by_run = data['by_run']

# Check instability values
react_instability = [r.get('decision', {}).get('decision_instability', 0) for r in by_run if r['strategy'] == 'react']
sg_instability = [r.get('decision', {}).get('decision_instability', 0) for r in by_run if r['strategy'] == 'stategraph']

print(f'ReAct instability: mean={sum(react_instability)/len(react_instability):.2f}, median={sorted(react_instability)[len(react_instability)//2]}')
print(f'StateGraph instability: mean={sum(sg_instability)/len(sg_instability):.2f}, median={sorted(sg_instability)[len(sg_instability)//2]}')

# Count runs with flips
react_with_flips = sum(1 for x in react_instability if x > 0)
sg_with_flips = sum(1 for x in sg_instability if x > 0)

print(f'\nReAct runs with flips: {react_with_flips}/{len(react_instability)}')
print(f'StateGraph runs with flips: {sg_with_flips}/{len(sg_instability)}')

# Distribution
print(f'\nReAct distribution: {dict(Counter(react_instability))}')
print(f'StateGraph distribution: {dict(Counter(sg_instability))}')
