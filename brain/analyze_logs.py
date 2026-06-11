"""
Brain — analyze_logs.py
Lê logs/paper_closed.jsonl e imprime relatório de sessão no terminal.
Uso: python brain/analyze_logs.py [caminho_opcional_para_jsonl]
"""
import json, sys, os
from collections import defaultdict
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

LOG_PATH = sys.argv[1] if len(sys.argv) > 1 else "logs/paper_closed.jsonl"

if not os.path.exists(LOG_PATH):
    print(f"Arquivo não encontrado: {LOG_PATH}")
    sys.exit(1)

trades = []
with open(LOG_PATH, encoding='utf-8') as f:
    for line in f:
        try:
            trades.append(json.loads(line))
        except:
            pass

if not trades:
    print("Nenhum trade encontrado.")
    sys.exit(0)

# Extrai campos com fallback para estrutura aninhada (entry.signal)
def get(t, *keys, default=0):
    for k in keys:
        v = t.get(k)
        if v is not None:
            return v
    sig = t.get('entry', {}).get('signal', {})
    for k in keys:
        v = sig.get(k)
        if v is not None:
            return v
    return default

n = len(trades)
winners = [t for t in trades if get(t, 'pnl_pct', 'pnl') > 0]
losers  = [t for t in trades if get(t, 'pnl_pct', 'pnl') <= 0]
pnl_total  = sum(get(t, 'pnl_usdt', 'pnl') for t in trades)
pnl_w = sum(get(t, 'pnl_usdt', 'pnl') for t in winners)
pnl_l = sum(get(t, 'pnl_usdt', 'pnl') for t in losers)
pf = abs(pnl_w / pnl_l) if pnl_l != 0 else float('inf')

mfe_list = [get(t, 'mfe', 'max_favorable_excursion') for t in trades]
mae_list = [get(t, 'mae', 'max_adverse_excursion') for t in trades]
avg_mfe = sum(mfe_list) / n if n else 0
avg_mae = sum(mae_list) / n if n else 0

# Captura MFE: quanto do MFE foi capturado no PnL
captures = []
for t in winners:
    mfe = get(t, 'mfe', 'max_favorable_excursion')
    pnl = get(t, 'pnl_pct', 'pnl')
    if mfe and mfe > 0:
        captures.append(pnl / mfe)
avg_capture = sum(captures) / len(captures) if captures else 0

print("=" * 60)
print(f"RELATÓRIO DE SESSÃO — {n} trades")
print("=" * 60)
print(f"Win Rate     : {len(winners)}/{n} ({100*len(winners)//n}%)")
print(f"PnL Total    : {pnl_total:+.2f} USDT")
print(f"PnL Winners  : {pnl_w:+.2f} | Losers: {pnl_l:+.2f}")
print(f"Profit Factor: {pf:.2f}")
print(f"Avg MFE      : {avg_mfe:+.2f}%  |  Avg MAE: {avg_mae:+.2f}%")
print(f"Captura MFE  : {100*avg_capture:.1f}%")

# Exit reasons
print()
print("--- BREAKDOWN POR EXIT REASON ---")
by_exit = defaultdict(list)
for t in trades:
    reason = t.get('exit_reason') or t.get('reason') or '?'
    by_exit[reason].append(t)
for reason, grp in sorted(by_exit.items(), key=lambda x: -len(x[1])):
    w = sum(1 for t in grp if get(t,'pnl_pct','pnl') > 0)
    p = sum(get(t,'pnl_usdt','pnl') for t in grp)
    print(f"  {reason:<28} n={len(grp):>3}  WR={100*w//len(grp):>3}%  PnL={p:+.2f}")

# Tabela winners vs losers por campo do signal dict
print()
print("--- WINNERS vs LOSERS — CAMPOS DO SIGNAL ---")
fields = [
    ('trades_1m',      'trades_1m'),
    ('cvd_change_pct', 'cvd_change_pct'),
    ('rsi_5m',         'rsi_5m'),
    ('ema_trend_4h',   'ema_trend_4h'),
    ('volume_quality', 'volume_quality'),
    ('liq_short_1m',   'liq_short_1m', 'liq_short_1m_stable'),
]
print(f"  {'Campo':<22} {'Winners':>10} {'Losers':>10} {'Delta':>10}")
print(f"  {'-'*54}")
for fdef in fields:
    label = fdef[0]
    keys  = fdef[1:]
    def avg_field(group):
        vals = [get(t, *keys) for t in group]
        vals = [v for v in vals if v is not None and isinstance(v, (int, float))]
        return sum(vals)/len(vals) if vals else 0
    w_avg = avg_field(winners)
    l_avg = avg_field(losers)
    delta = w_avg - l_avg
    print(f"  {label:<22} {w_avg:>10.2f} {l_avg:>10.2f} {delta:>+10.2f}")

# Padrões automáticos
print()
print("--- PADRÕES AUTOMÁTICOS ---")
sf_mfe0 = [t for t in trades if t.get('exit_reason') == 'squeeze_failed' and get(t,'mfe','max_favorable_excursion') == 0]
low_cap  = [t for t in winners if captures and get(t,'mfe','max_favorable_excursion') > 0
            and get(t,'pnl_pct','pnl') / get(t,'mfe','max_favorable_excursion') < 0.30]
high_mae = [t for t in losers if abs(get(t,'mae','max_adverse_excursion')) > 8]
liq_casc = [t for t in trades if get(t,'liq_cascade') == True]

print(f"  squeeze_failed MFE=0       : {len(sf_mfe0)} trades")
print(f"  Winners captura < 30%      : {len(low_cap)} trades")
print(f"  Losers MAE > 8%            : {len(high_mae)} trades")
print(f"  Trades com liq_cascade=True: {len(liq_casc)} trades")

# Pior MAE geral
if trades:
    worst = sorted(trades, key=lambda t: get(t,'mae','max_adverse_excursion'))[:3]
    print()
    print("  Top 3 piores MAE:")
    for t in worst:
        sym = t.get('symbol','?')
        mae = get(t,'mae','max_adverse_excursion')
        pnl = get(t,'pnl_usdt','pnl')
        reason = t.get('exit_reason','?')
        print(f"    {sym:<14} MAE={mae:+.2f}%  PnL={pnl:+.2f}  [{reason}]")
