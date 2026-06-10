"""
ARIA — analyze_eassets.py
Lê o JSON mais recente de aria/eAssets/dados_eassets/ e cruza com trades do dia.
Uso: python aria/scripts/analyze_eassets.py [caminho_json_opcional]
"""
import json, sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = "aria/eAssets/dados_eassets"
LOG_PATH = "logs/paper_closed.jsonl"

# Encontra snapshot mais recente por timestamp interno
def find_latest_snapshot():
    files = glob.glob(os.path.join(DATA_DIR, "eassets*.json"))
    best_ts, best_path = "", ""
    for f in files:
        try:
            d = json.load(open(f, encoding='utf-8'))
            ts = d.get('timestamp', '')
            n  = len(d.get('data', {}))
            if n >= 100 and ts > best_ts:
                best_ts, best_path = ts, f
        except:
            pass
    return best_path, best_ts

snap_path = sys.argv[1] if len(sys.argv) > 1 else None
if not snap_path:
    snap_path, snap_ts = find_latest_snapshot()
    if not snap_path:
        print(f"Nenhum snapshot encontrado em {DATA_DIR}")
        sys.exit(1)
else:
    snap_ts = '?'

d = json.load(open(snap_path, encoding='utf-8'))
snap_ts = d.get('timestamp', snap_ts)
ea_data = d.get('data', {})

# Normaliza chaves unicode
ea = {}
for sym, v in ea_data.items():
    ea[sym.encode('ascii','replace').decode('ascii')] = v

# Carrega trades do dia
trades = []
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, encoding='utf-8') as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except:
                pass

traded_syms = {t.get('symbol') for t in trades}

print("=" * 60)
print(f"ARIA — eAssets × SS · snapshot {snap_ts}")
print(f"Universo: {len(ea)} símbolos | Trades hoje: {len(trades)}")
print("=" * 60)

# Cruzamento: para cada trade, extrai campos do eAssets
if trades:
    print()
    print("--- TRADES DO DIA × eAssets ---")
    print(f"  {'Símbolo':<16} {'PnL':>7} {'Exit':<20} {'e4h':>4} {'EXP1h':>7} {'RSI1h':>6} {'OI_tr':>7}  Divergência")
    print(f"  {'-'*95}")
    for t in sorted(trades, key=lambda x: x.get('pnl_usdt', x.get('pnl', 0))):
        sym    = t.get('symbol', '?')
        pnl    = t.get('pnl_usdt', t.get('pnl', 0))
        reason = t.get('exit_reason', '?')
        ea_sym = ea.get(sym, {})
        e4h    = ea_sym.get('ema_trend:4h', '?')
        exp1h  = ea_sym.get('exp_btc:1h',  '?')
        rsi1h  = ea_sym.get('rsi:1h',       '?')
        oi_tr  = ea_sym.get('oi_trend:5m',  '?')
        # Divergências óbvias
        divs = []
        bot_e4h = t.get('ema_trend_4h', t.get('entry', {}).get('signal', {}).get('ema_trend_4h'))
        if bot_e4h is not None and e4h != '?' and abs(float(e4h) - float(bot_e4h)) >= 4:
            divs.append(f"e4h bot={bot_e4h} ea={e4h}")
        e4h_str  = f"{e4h:+d}"  if isinstance(e4h, (int,float)) else str(e4h)
        exp_str  = f"{exp1h:+.1f}" if isinstance(exp1h, (int,float)) else str(exp1h)
        rsi_str  = f"{rsi1h:.0f}"  if isinstance(rsi1h, (int,float)) else str(rsi1h)
        oi_str   = f"{oi_tr:.4f}"  if isinstance(oi_tr, (int,float)) else str(oi_tr)
        div_str  = " | ".join(divs) if divs else ""
        print(f"  {sym:<16} {pnl:>+7.2f} {reason:<20} {e4h_str:>4} {exp_str:>7} {rsi_str:>6} {oi_str:>7}  {div_str}")

# Tier 1: top 10 por EXP_BTC:1h com EMA:4h >= 0 que NÃO entraram
print()
print("--- TIER 1 — TOP OPORTUNIDADES QUE NÃO ENTRARAM (EXP1h>15, EMA4h>=0) ---")
candidates = []
for sym, v in ea.items():
    e4h   = v.get('ema_trend:4h', 0) or 0
    exp1h = v.get('exp_btc:1h',   0) or 0
    exp5  = v.get('exp_btc:5m',   0) or 0
    rsi1h = v.get('rsi:1h',       0) or 0
    t1m   = v.get('trades_minute:5m', 0) or 0
    oi    = v.get('oi_trend:5m',  0) or 0
    lsr   = v.get('lsr_trend:5m', 0) or 0
    if e4h >= 0 and exp1h > 15 and sym not in traded_syms:
        candidates.append((sym, e4h, exp1h, exp5, rsi1h, t1m, oi, lsr))

candidates.sort(key=lambda x: -x[2])
print(f"  {'Símbolo':<16} {'e4h':>4} {'EXP1h':>7} {'EXP5m':>7} {'RSI1h':>6} {'t1m':>7} {'OI_tr':>8} {'LSR_tr':>8}")
for sym, e4h, exp1h, exp5, rsi1h, t1m, oi, lsr in candidates[:10]:
    gate_str = "PASS" if (t1m >= 10 and oi >= 0.008 and lsr <= -0.3) else "gate_blk"
    print(f"  {sym:<16} {e4h:>+4} {exp1h:>+7.1f} {exp5:>+7.1f} {rsi1h:>6.0f} {t1m:>7.0f} {oi:>8.4f} {lsr:>8.4f}  [{gate_str}]")

# Standby: 5m fraco mas 1h forte
print()
print("--- STANDBY — divergência temporal (5m<0, 15m>5, 1h>10, EMA4h>=0) ---")
standby = [(sym, v) for sym, v in ea.items()
           if (v.get('exp_btc:5m') or 0) < 0
           and (v.get('exp_btc:15m') or 0) > 5
           and (v.get('exp_btc:1h') or 0) > 10
           and (v.get('ema_trend:4h') or 0) >= 0
           and sym not in traded_syms]
standby.sort(key=lambda x: -(x[1].get('exp_btc:1h') or 0))
for sym, v in standby[:5]:
    print(f"  {sym:<16} e4h={v.get('ema_trend:4h',0):+d}  1h={v.get('exp_btc:1h',0):+.1f}  15m={v.get('exp_btc:15m',0):+.1f}  5m={v.get('exp_btc:5m',0):+.1f}")
