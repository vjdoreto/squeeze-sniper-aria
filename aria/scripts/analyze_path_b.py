"""
ARIA - Análise Path B E-01 e E-04
Gerado: 12/06/2026
"""
import json
import sys

def load_snap(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

snaps = {
    'S1': load_snap('aria/eAssets/dados_eassets/eassets-panel-20260610-215848.json'),
    'S2': load_snap('aria/eAssets/dados_eassets/eassets-panel-20260611-011545.json'),
    'S3': load_snap('aria/eAssets/dados_eassets/eassets-panel-20260611-061006.json'),
    'S4': load_snap('aria/eAssets/dados_eassets/eassets-panel-20260611-143919.json'),
}

def get_candidates(snap):
    data = snap['data']
    cands = []
    for sym, d in data.items():
        ema4h = d.get('ema_trend:4h')
        range1h = d.get('range_level:1h')
        exp1h = d.get('exp_btc:1h')
        if ema4h is None or range1h is None or exp1h is None:
            continue
        if ema4h >= 4 and range1h >= 3 and exp1h > 10:
            cands.append({
                'sym': sym,
                'price': d.get('price'),
                'ema4h': ema4h,
                'ema1h': d.get('ema_trend:1h'),
                'range1h': range1h,
                'exp1h': exp1h,
                'lsr_trend1h': d.get('lsr_trend:1h'),
                'lsr_trend5m': d.get('lsr_trend:5m'),
                'fr': d.get('fr'),
                'rsi1h': d.get('rsi:1h'),
                'oi_trend1h': d.get('oi_trend:1h'),
            })
    return cands

def price_move(sym, snap_from, snap_to):
    d_from = snap_from['data'].get(sym)
    d_to = snap_to['data'].get(sym)
    if d_from is None or d_to is None:
        return None
    p_from = d_from.get('price')
    p_to = d_to.get('price')
    if not p_from or not p_to:
        return None
    return (p_to - p_from) / p_from * 100

out = []
def pr(s=''):
    out.append(s)

pr("=" * 70)
pr("E-01 -- VALIDACAO DE EDGE PATH B: MOVE APOS CRITERIO SATISFEITO")
pr("Criterios: ema_trend:4h >= +4, range_level:1h >= 3, exp_btc:1h > 10")
pr("=" * 70)

pairs = [
    ('S1', 'S2', '00:58->04:15 (+3h17)'),
    ('S2', 'S3', '04:15->09:10 (+4h55)'),
    ('S3', 'S4', '09:10->17:39 (+8h29)'),
]

all_cases = []

for from_key, to_key, label in pairs:
    snap_from = snaps[from_key]
    snap_to = snaps[to_key]
    cands = get_candidates(snap_from)

    pr(f"\n--- Par {label} | {len(cands)} candidatos ---")
    results = []
    for c in cands:
        move = price_move(c['sym'], snap_from, snap_to)
        if move is None:
            continue
        d_next = snap_to['data'].get(c['sym'], {})
        ema4h_next = d_next.get('ema_trend:4h')
        results.append({**c, 'move_pct': move, 'ema4h_next': ema4h_next})
        all_cases.append({**c, 'pair': label, 'move_pct': move, 'ema4h_next': ema4h_next})

    results.sort(key=lambda x: -x['move_pct'])
    for r in results:
        flag = 'OK+' if r['move_pct'] >= 5.0 else ('NEG' if r['move_pct'] < -2.0 else 'FLT')
        lsr = str(r['lsr_trend1h']) if r['lsr_trend1h'] is not None else 'N/A'
        pr(f"  [{flag}] {r['sym']:22s} move={r['move_pct']:+7.2f}%  exp1h={r['exp1h']:6.1f}  lsr1h={lsr:>8s}  fr={r['fr']:.6f}  rsi1h={r['rsi1h']:.1f}  ema4h_dep={r['ema4h_next']}")

pr("")
pr("=" * 70)
pr("SUMARIO E-01 -- DISTRIBUICAO DE MOVES")
pr("=" * 70)
total = len(all_cases)
above5 = [c for c in all_cases if c['move_pct'] >= 5.0]
above3 = [c for c in all_cases if c['move_pct'] >= 3.0]
flat   = [c for c in all_cases if -2.0 <= c['move_pct'] < 3.0]
negative = [c for c in all_cases if c['move_pct'] < -2.0]

pr(f"\nTotal de observacoes: {total}")
pr(f"Move >= +5%     : {len(above5):2d} ({100*len(above5)//total}%)")
pr(f"Move >= +3%     : {len(above3):2d} ({100*len(above3)//total}%)")
pr(f"Flat -2% a +3%  : {len(flat):2d} ({100*len(flat)//total}%)")
pr(f"Move < -2%      : {len(negative):2d} ({100*len(negative)//total}%)")

pr("\nCasos +5%:")
for c in sorted(above5, key=lambda x: -x['move_pct']):
    lsr = str(c['lsr_trend1h']) if c['lsr_trend1h'] is not None else 'N/A'
    pr(f"  {c['sym']:22s} +{c['move_pct']:.2f}%  par={c['pair']}  lsr1h={lsr}  fr={c['fr']:.6f}  exp1h={c['exp1h']:.1f}")

pr("\nCasos negativos (<-2%):")
for c in sorted(negative, key=lambda x: x['move_pct']):
    lsr = str(c['lsr_trend1h']) if c['lsr_trend1h'] is not None else 'N/A'
    pr(f"  {c['sym']:22s} {c['move_pct']:.2f}%  par={c['pair']}  lsr1h={lsr}  fr={c['fr']:.6f}  exp1h={c['exp1h']:.1f}")

# Analise de discriminadores: winners vs losers
pr("")
pr("=" * 70)
pr("DISCRIMINADORES: WINNERS (+5%) vs LOSERS (<-2%)")
pr("=" * 70)

def avg(lst, key):
    vals = [x[key] for x in lst if x.get(key) is not None]
    return sum(vals)/len(vals) if vals else None

for label2, grupo in [('Winners (>=+5%)', above5), ('Flat (-2%..+3%)', flat), ('Losers (<-2%)', negative)]:
    if not grupo:
        continue
    pr(f"\n{label2} (n={len(grupo)}):")
    pr(f"  exp_btc:1h  media: {avg(grupo, 'exp1h'):.1f}")
    pr(f"  lsr_trend:1h media: {avg(grupo, 'lsr_trend1h'):.2f}" if avg(grupo,'lsr_trend1h') else "  lsr_trend:1h: N/A")
    pr(f"  fr media:   {avg(grupo, 'fr'):.6f}")
    pr(f"  rsi1h media: {avg(grupo, 'rsi1h'):.1f}" if avg(grupo,'rsi1h') else "  rsi1h: N/A")
    pr(f"  oi_trend1h media: {avg(grupo,'oi_trend1h'):.2f}" if avg(grupo,'oi_trend1h') else "  oi_trend1h: N/A")

# =============================================
# E-04 -- MAPEAMENTO DO UNIVERSO CANDIDATO
# =============================================
pr("")
pr("=" * 70)
pr("E-04 -- MAPEAMENTO DO UNIVERSO CANDIDATO PATH B")
pr("=" * 70)
pr("Criterio de recorrencia: ema4h >= +4 AND ema1h >= +2 em multiplos snapshots")

# Criterio mais amplo para E-04: ema4h >= 4 AND ema1h >= 2
snap_labels = [('S1', snaps['S1']), ('S2', snaps['S2']), ('S3', snaps['S3']), ('S4', snaps['S4'])]

symbol_scores = {}  # sym -> contagem de snapshots onde satisfaz criterio
symbol_range_counts = {}  # sym -> contagem de snapshots com range1h >= 3
symbol_reversal = {}  # sym -> contagem de snapshots onde ema4h >= 4 mas nao no proximo

for label, snap in snap_labels:
    data = snap['data']
    for sym, d in data.items():
        ema4h = d.get('ema_trend:4h')
        ema1h = d.get('ema_trend:1h')
        range1h = d.get('range_level:1h')
        if ema4h is not None and ema1h is not None and ema4h >= 4 and ema1h >= 2:
            symbol_scores[sym] = symbol_scores.get(sym, 0) + 1
        if range1h is not None and range1h >= 3 and ema4h is not None and ema4h >= 4:
            symbol_range_counts[sym] = symbol_range_counts.get(sym, 0) + 1

# Deteccao de reversoes rapidas: aparece em Si com criterio mas some em Si+1
snap_list = [snaps['S1'], snaps['S2'], snaps['S3'], snaps['S4']]
for i in range(len(snap_list)-1):
    snap_from = snap_list[i]
    snap_to = snap_list[i+1]
    for sym, d in snap_from['data'].items():
        ema4h = d.get('ema_trend:4h')
        ema1h = d.get('ema_trend:1h')
        if ema4h is not None and ema1h is not None and ema4h >= 4 and ema1h >= 2:
            d_next = snap_to['data'].get(sym, {})
            ema4h_next = d_next.get('ema_trend:4h') or 0
            if ema4h_next < 4:
                symbol_reversal[sym] = symbol_reversal.get(sym, 0) + 1

pr("\n--- Simbolos recorrentes (aparecem em >= 2 snapshots com ema4h>=4, ema1h>=2) ---")
recorrentes = {sym: cnt for sym, cnt in symbol_scores.items() if cnt >= 2}
recorrentes_sorted = sorted(recorrentes.items(), key=lambda x: (-x[1], -symbol_range_counts.get(x[0],0)))
pr(f"Total: {len(recorrentes)} simbolos")
pr("")
pr(f"  {'Simbolo':22s}  Snaps  RangeAlto  Reversoes")
for sym, cnt in recorrentes_sorted[:60]:
    rc = symbol_range_counts.get(sym, 0)
    rv = symbol_reversal.get(sym, 0)
    marker = ' <-- INSTAVEL' if rv >= 2 else (' <-- TENDENCIA SUSTENTADA' if cnt >= 3 else '')
    pr(f"  {sym:22s}  {cnt}/4    {rc}/4       {rv}/3{marker}")

pr("")
pr("--- Simbolos com reversao rapida (aparecem e somem em snapshots consecutivos) ---")
reversao_rapida = {sym: cnt for sym, cnt in symbol_reversal.items() if cnt >= 2 and symbol_scores.get(sym, 0) <= 2}
rv_sorted = sorted(reversao_rapida.items(), key=lambda x: -x[1])
pr(f"Total: {len(rv_sorted)}")
for sym, rv in rv_sorted[:30]:
    sc = symbol_scores.get(sym, 0)
    pr(f"  {sym:22s}  aparece {sc} snaps, reverte {rv}x -> excluir universo Path B")

pr("")
pr("--- Candidatos mais fortes Path B (3-4 snaps sustentados, range alto) ---")
top_candidates = [(sym, cnt) for sym, cnt in recorrentes.items() if cnt >= 3 and symbol_reversal.get(sym, 0) == 0]
top_sorted = sorted(top_candidates, key=lambda x: (-x[1], -symbol_range_counts.get(x[0], 0)))
pr(f"Total: {len(top_sorted)}")
for sym, cnt in top_sorted[:40]:
    rc = symbol_range_counts.get(sym, 0)
    pr(f"  {sym:22s}  {cnt}/4 snaps  range_alto={rc}/4")

# Imprimir tudo
for line in out:
    print(line)
