
import json
from pathlib import Path

print('=== TOP 10 SYMBOLS COM MAIOR SCORE ===')

metric_state = Path('logs/metric_state.json')
if not metric_state.exists():
    print('metric_state.json não encontrado')
    exit()

with open(metric_state, encoding='utf-8') as f:
    data = json.load(f)

scores = []
for sym, d in data.get('data', {}).items():
    score = d.get('score', 0)
    exp = d.get('exp:5m', 0)
    oi_trend = d.get('oi_trend:5m', 0)
    lsr_trend = d.get('lsr_trend:5m', 0)
    if score > 0:
        scores.append((sym, score, exp, oi_trend, lsr_trend))

scores.sort(key=lambda x: x[1], reverse=True)

for sym, score, exp, oi, lsr in scores[:10]:
    print(f'{sym}: score={score:.0f} | exp:5m={exp:.4f} | oi_trend={oi:.4f} | lsr_trend={lsr:.4f}')
