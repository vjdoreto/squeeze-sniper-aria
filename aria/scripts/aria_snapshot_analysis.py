"""
ARIA — Análise de snapshots eAssets
Uso:
  python aria_snapshot_analysis.py              → analisa eassets_latest.json
  python aria_snapshot_analysis.py --compare    → compara todos os snapshots da pasta (ordena por timestamp)
  python aria_snapshot_analysis.py A.json B.json → compara dois arquivos específicos
"""
import json, sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Apps\#5 SqueezeSniper-V4\aria\eAssets\dados_eassets'
LATEST   = os.path.join(DATA_DIR, 'eassets_latest.json')


# ─── helpers ──────────────────────────────────────────────────────────────────

def load_snapshot(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    rows = {}
    for sym, v in d.get('data', {}).items():
        safe = sym.encode('ascii', 'replace').decode('ascii')
        rows[safe] = {
            'oi_trend_5m':   v.get('oi_trend:5m',   0) or 0,
            'lsr_trend_5m':  v.get('lsr_trend:5m',  0) or 0,
            'exp_btc_5m':    v.get('exp_btc:5m',    0) or 0,
            'exp_btc_15m':   v.get('exp_btc:15m',   0) or 0,
            'exp_btc_1h':    v.get('exp_btc:1h',    0) or 0,
            'ema_trend_4h':  v.get('ema_trend:4h',  0) or 0,
            'ema_trend_1h':  v.get('ema_trend:1h',  0) or 0,
            'rsi_5m':        v.get('rsi:5m',        0) or 0,
            'rsi_1h':        v.get('rsi:1h',        0) or 0,
            'trades_1m':     v.get('trades_minute:5m', 0) or 0,
            'lsr_5m':        v.get('lsr:5m',        0) or 0,
            'range_level_5m': v.get('range_level:5m', 0) or 0,
        }
    return d.get('timestamp', '?'), rows


def gate_combo(r):
    return r['trades_1m'] >= 10 and r['oi_trend_5m'] >= 0.008 and r['lsr_trend_5m'] <= -0.3

def is_tier1(r):
    return r['ema_trend_4h'] >= 4 and r['exp_btc_1h'] > 15 and gate_combo(r)

def is_tier2(r):
    return (r['ema_trend_4h'] >= 2 and r['exp_btc_1h'] > 5
            and r['exp_btc_15m'] > 0 and r['exp_btc_5m'] > 0 and gate_combo(r))

def is_standby(r):
    return r['exp_btc_5m'] < 0 and r['exp_btc_15m'] > 5 and r['exp_btc_1h'] > 10 and r['ema_trend_4h'] >= 0

def delta_str(v_new, v_old):
    d = v_new - v_old
    arrow = '▲' if d > 0 else ('▼' if d < 0 else '─')
    return f"{arrow}{abs(d):+.1f}"


# ─── single snapshot report ───────────────────────────────────────────────────

def report_single(ts, rows):
    n = len(rows)
    vals = list(rows.values())

    ema4h_bull = sum(1 for r in vals if r['ema_trend_4h'] >= 4)
    ema4h_bear = sum(1 for r in vals if r['ema_trend_4h'] <= -4)
    ema4h_neut = sum(1 for r in vals if -3 < r['ema_trend_4h'] < 4)
    expbtc_p1h = sum(1 for r in vals if r['exp_btc_1h'] > 0)
    lsr_neg    = sum(1 for r in vals if r['lsr_trend_5m'] < -0.3)
    oi_pos     = sum(1 for r in vals if r['oi_trend_5m'] > 0.008)
    rsi1h_60   = sum(1 for r in vals if r['rsi_1h'] > 60)
    rsi1h_avg  = sum(r['rsi_1h'] for r in vals) / n

    print(f"\nSnapshot: {ts}  n={n}")
    print()
    print("=== MACRO ===")
    print(f"EMA:4h >= +4 (bull) : {ema4h_bull}/{n} ({100*ema4h_bull//n}%)")
    print(f"EMA:4h <= -4 (bear) : {ema4h_bear}/{n} ({100*ema4h_bear//n}%)")
    print(f"EMA:4h neutro       : {ema4h_neut}/{n} ({100*ema4h_neut//n}%)")
    print(f"EXP_BTC:1h > 0      : {expbtc_p1h}/{n} ({100*expbtc_p1h//n}%)")
    print(f"LSR_trend < -0.3    : {lsr_neg}/{n} ({100*lsr_neg//n}%)")
    print(f"OI_trend > 0.008    : {oi_pos}/{n} ({100*oi_pos//n}%)")
    print(f"RSI:1h > 60         : {rsi1h_60}/{n}")
    print(f"RSI:1h medio        : {rsi1h_avg:.1f}")

    gate      = {s: r for s, r in rows.items() if gate_combo(r)}
    gate_ema  = {s: r for s, r in gate.items()  if r['ema_trend_4h'] >= 0}
    gate_full = {s: r for s, r in gate_ema.items() if r['rsi_5m'] >= 45}

    print()
    print("=== FUNIL DE GATES ===")
    print(f"Gate combo (trades+oi+lsr) : {len(gate)}/{n}")
    print(f"+ ema_trend_4h >= 0        : {len(gate_ema)}/{n}")
    print(f"+ rsi_5m >= 45             : {len(gate_full)}/{n}")

    t1 = {s: r for s, r in rows.items() if is_tier1(r)}
    print(f"\n=== TIER 1 (ema4h>=4 + expbtc1h>15 + gates) n={len(t1)} ===")
    for s, r in sorted(t1.items(), key=lambda x: -x[1]['exp_btc_1h'])[:12]:
        print(f"  {s:16s} e4h={r['ema_trend_4h']:+d} 1h={r['exp_btc_1h']:+7.1f} 15m={r['exp_btc_15m']:+6.1f} 5m={r['exp_btc_5m']:+6.1f} rsi1h={r['rsi_1h']:.0f} t1m={r['trades_1m']:.0f}")

    t2 = {s: r for s, r in rows.items() if is_tier2(r) and s not in t1}
    print(f"\n=== TIER 2 (ema4h>=2 + expbtc 3TFs alinhados + gates) n={len(t2)} ===")
    for s, r in sorted(t2.items(), key=lambda x: -(x[1]['exp_btc_1h'] + x[1]['exp_btc_5m']))[:12]:
        print(f"  {s:16s} e4h={r['ema_trend_4h']:+d} 1h={r['exp_btc_1h']:+6.1f} 15m={r['exp_btc_15m']:+6.1f} 5m={r['exp_btc_5m']:+6.1f} rsi1h={r['rsi_1h']:.0f} t1m={r['trades_1m']:.0f}")

    standby = {s: r for s, r in rows.items() if is_standby(r)}
    print(f"\n=== STANDBY — divergencia temporal (5m fraco, 15m/1h forte, ema4h>=0) n={len(standby)} ===")
    for s, r in sorted(standby.items(), key=lambda x: -x[1]['exp_btc_1h'])[:8]:
        print(f"  {s:16s} e4h={r['ema_trend_4h']:+d} 1h={r['exp_btc_1h']:+6.1f} 15m={r['exp_btc_15m']:+6.1f} 5m={r['exp_btc_5m']:+6.1f} rsi1h={r['rsi_1h']:.0f}")

    blk = {s: r for s, r in gate.items() if r['ema_trend_4h'] <= -4}
    pct = 100 * len(blk) // len(gate) if gate else 0
    print(f"\n=== BLOQUEADOS pelo gate ema_4h_bearish: {len(blk)}/{len(gate)} ({pct}%) do gate combo ===")
    for s, r in sorted(blk.items(), key=lambda x: -x[1]['exp_btc_1h'])[:6]:
        print(f"  {s:16s} e4h={r['ema_trend_4h']:+d} 1h={r['exp_btc_1h']:+6.1f} t1m={r['trades_1m']:.0f} rsi1h={r['rsi_1h']:.0f}")

    return t1, t2, standby


# ─── cross-snapshot comparison ────────────────────────────────────────────────

def report_compare(snapshots):
    """
    snapshots: list of (timestamp_str, rows_dict), sorted oldest → newest
    """
    if len(snapshots) < 2:
        print("Comparação requer 2+ snapshots.")
        return

    ts_old, rows_old = snapshots[0]
    ts_new, rows_new = snapshots[-1]

    # Calcula candidatos em cada snapshot
    t1_old = {s for s, r in rows_old.items() if is_tier1(r)}
    t2_old = {s for s, r in rows_old.items() if is_tier2(r)}
    sb_old = {s for s, r in rows_old.items() if is_standby(r)}

    t1_new = {s: r for s, r in rows_new.items() if is_tier1(r)}
    t2_new = {s: r for s, r in rows_new.items() if is_tier2(r)}
    sb_new = {s: r for s, r in rows_new.items() if is_standby(r)}

    candidates_new = set(t1_new) | set(t2_new) | set(sb_new)
    candidates_old = t1_old | t2_old | sb_old

    print(f"\n{'='*60}")
    print(f"COMPARAÇÃO DE SNAPSHOTS")
    print(f"  ANTES : {ts_old}")
    print(f"  DEPOIS: {ts_new}")
    print(f"{'='*60}")

    # Macro delta
    n_new = len(rows_new)
    n_old = len(rows_old)
    ema_bull_new = sum(1 for r in rows_new.values() if r['ema_trend_4h'] >= 4)
    ema_bull_old = sum(1 for r in rows_old.values() if r['ema_trend_4h'] >= 4)
    exp_p1h_new  = sum(1 for r in rows_new.values() if r['exp_btc_1h'] > 0)
    exp_p1h_old  = sum(1 for r in rows_old.values() if r['exp_btc_1h'] > 0)

    print("\n=== MACRO DELTA ===")
    print(f"  EMA:4h bull (+4)  : {ema_bull_old}/{n_old} → {ema_bull_new}/{n_new}  ({delta_str(ema_bull_new, ema_bull_old)})")
    print(f"  EXP_BTC:1h > 0    : {exp_p1h_old}/{n_old} → {exp_p1h_new}/{n_new}  ({delta_str(exp_p1h_new, exp_p1h_old)})")
    gate_old_n = sum(1 for r in rows_old.values() if gate_combo(r))
    gate_new_n = sum(1 for r in rows_new.values() if gate_combo(r))
    print(f"  Gate combo        : {gate_old_n} → {gate_new_n}  ({delta_str(gate_new_n, gate_old_n)})")

    # Candidatos persistentes (estavam antes E depois)
    persistent = candidates_new & candidates_old
    print(f"\n=== PERSISTENTES (estavam em Tier1/2/Standby nos 2 snapshots) n={len(persistent)} ===")
    for s in sorted(persistent, key=lambda x: -rows_new[x]['exp_btc_1h']):
        r_new = rows_new[s]
        r_old = rows_old.get(s, {})
        tier_tag = 'T1' if s in t1_new else ('T2' if s in t2_new else 'SB')
        d1h  = delta_str(r_new['exp_btc_1h'],  r_old.get('exp_btc_1h', 0))
        d5m  = delta_str(r_new['exp_btc_5m'],  r_old.get('exp_btc_5m', 0))
        dt1m = delta_str(r_new['trades_1m'],    r_old.get('trades_1m', 0))
        print(f"  [{tier_tag}] {s:16s}  1h={r_new['exp_btc_1h']:+7.1f}({d1h})  5m={r_new['exp_btc_5m']:+6.1f}({d5m})  t1m={r_new['trades_1m']:.0f}({dt1m})  e4h={r_new['ema_trend_4h']:+d}")

    # Novos entrants (não estavam antes)
    new_entries = candidates_new - candidates_old
    if new_entries:
        print(f"\n=== NOVOS ENTRANTS (apareceram agora) n={len(new_entries)} ===")
        for s in sorted(new_entries, key=lambda x: -rows_new[x]['exp_btc_1h']):
            r = rows_new[s]
            tier_tag = 'T1' if s in t1_new else ('T2' if s in t2_new else 'SB')
            print(f"  [{tier_tag}] {s:16s}  1h={r['exp_btc_1h']:+7.1f}  15m={r['exp_btc_15m']:+6.1f}  5m={r['exp_btc_5m']:+6.1f}  e4h={r['ema_trend_4h']:+d}  t1m={r['trades_1m']:.0f}")

    # Saídas (estavam antes mas sumiram)
    exits = candidates_old - candidates_new
    if exits:
        print(f"\n=== SAÍRAM DO RADAR n={len(exits)} ===")
        for s in sorted(exits, key=lambda x: -rows_old[x]['exp_btc_1h']):
            r_old = rows_old[s]
            r_new = rows_new.get(s)
            if r_new:
                reason = []
                if not gate_combo(r_new): reason.append('gate_combo')
                if r_new['ema_trend_4h'] < 0: reason.append('ema4h_neg')
                if r_new['exp_btc_1h'] <= 0: reason.append('expbtc_neg')
                print(f"  {s:16s}  antes: 1h={r_old['exp_btc_1h']:+7.1f}  agora: 1h={r_new['exp_btc_1h']:+7.1f}  motivo: {','.join(reason) or '?'}")
            else:
                print(f"  {s:16s}  antes: 1h={r_old['exp_btc_1h']:+7.1f}  (saiu do universo?)")

    # Standby que viraram Tier 1/2 — os mais interessantes
    upgraded = (set(sb_old) & (set(t1_new) | set(t2_new)))
    if upgraded:
        print(f"\n=== ⭐ STANDBY → TIER (1m alinhando — entrada potencial) n={len(upgraded)} ===")
        for s in upgraded:
            r_new = rows_new[s]
            r_old = rows_old.get(s, {})
            print(f"  {s:16s}  antes 5m={r_old.get('exp_btc_5m',0):+6.1f}  agora 5m={r_new['exp_btc_5m']:+6.1f}  1h={r_new['exp_btc_1h']:+7.1f}  e4h={r_new['ema_trend_4h']:+d}")


# ─── main ─────────────────────────────────────────────────────────────────────

def discover_snapshots():
    """Retorna lista de (timestamp, path) de todos os snapshots, ordenado por timestamp."""
    pattern = os.path.join(DATA_DIR, 'eassets-panel-*.json')
    files = glob.glob(pattern)
    # inclui latest
    if os.path.exists(LATEST):
        files.append(LATEST)
    result = []
    seen_ts = set()
    for f in files:
        try:
            d = json.load(open(f, encoding='utf-8'))
            ts = d.get('timestamp', '')
            n  = len(d.get('data', {}))
            if n < 100:   # ignora snapshots parciais
                continue
            if ts in seen_ts:
                continue
            seen_ts.add(ts)
            result.append((ts, f))
        except Exception:
            pass
    result.sort(key=lambda x: x[0])
    return result


if __name__ == '__main__':
    args = sys.argv[1:]

    if '--compare' in args or len(args) >= 2:
        # modo comparação
        if len(args) >= 2 and '--compare' not in args:
            # dois arquivos explícitos
            files = [(None, a) for a in args[:2]]
        else:
            files = discover_snapshots()

        if len(files) < 2:
            print(f"Apenas {len(files)} snapshot(s) encontrado(s). Adicione mais JSONs na pasta para comparar.")
            sys.exit(0)

        print(f"\n{len(files)} snapshots encontrados:")
        snapshots_loaded = []
        for ts, path in files:
            ts_real, rows = load_snapshot(path)
            print(f"  {ts_real}  n={len(rows)}  {os.path.basename(path)}")
            snapshots_loaded.append((ts_real, rows))

        # Análise individual do mais recente
        print("\n" + "="*60)
        print("ANÁLISE DO SNAPSHOT MAIS RECENTE")
        report_single(*snapshots_loaded[-1])

        # Comparação
        report_compare(snapshots_loaded)

    else:
        # modo single (padrão)
        path = args[0] if args else LATEST
        ts, rows = load_snapshot(path)
        report_single(ts, rows)
