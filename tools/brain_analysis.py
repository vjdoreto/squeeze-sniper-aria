import json
from collections import defaultdict
import datetime

lines = open("logs/paper_closed.jsonl", encoding="utf-8").readlines()
trades = [json.loads(l.strip()) for l in lines if l.strip()]
RESET_TS = 1781306700.0  # 12/06 23:25 UTC

closed = [t for t in trades if t.get("exit") and t["exit"].get("reason")]
post = [t for t in closed if t["entry"]["time"] >= RESET_TS]

def analyze_deep(lst, label):
    if not lst:
        print(label + ": sem trades")
        return
    wins  = [t for t in lst if t["quality"]["win"]]
    loses = [t for t in lst if not t["quality"]["win"]]
    pnl   = sum(t["exit"]["pnl_usdt"] for t in lst)
    gp    = sum(t["exit"]["pnl_usdt"] for t in wins)
    gl    = abs(sum(t["exit"]["pnl_usdt"] for t in loses))
    pf    = gp / gl if gl else 999
    mfes  = [t["quality"]["mfe_pct"] for t in lst]
    maes  = [t["quality"]["mae_pct"] for t in lst]
    avg_mfe = sum(mfes) / len(mfes)
    avg_mae = sum(maes) / len(maes)

    print("=" * 60)
    print(f"{label} ({len(lst)} trades)")
    print("=" * 60)
    print(f"WR: {len(wins)}/{len(lst)} = {100*len(wins)/len(lst):.1f}%")
    print(f"PnL: {pnl:+.2f} USDT | GP: +{gp:.2f} | GL: -{gl:.2f} | PF: {pf:.2f}")
    print(f"MFE medio: {avg_mfe:.2f}% | MAE medio: {avg_mae:.2f}%")

    if wins:
        w_mfe = [t["quality"]["mfe_pct"] for t in wins]
        w_mae = [t["quality"]["mae_pct"] for t in wins]
        print(f"Winners: MFE avg {sum(w_mfe)/len(w_mfe):.2f}% | MAE avg {sum(w_mae)/len(w_mae):.2f}%")
    if loses:
        l_mfe = [t["quality"]["mfe_pct"] for t in loses]
        l_mae = [t["quality"]["mae_pct"] for t in loses]
        print(f"Losers:  MFE avg {sum(l_mfe)/len(l_mfe):.2f}% | MAE avg {sum(l_mae)/len(l_mae):.2f}%")

    print()
    print("Por exit_reason:")
    by_exit = defaultdict(list)
    for t in lst:
        by_exit[t["exit"]["reason"]].append(t)
    for er, ts in sorted(by_exit.items(), key=lambda x: -len(x[1])):
        w = [x for x in ts if x["quality"]["win"]]
        p = sum(x["exit"]["pnl_usdt"] for x in ts)
        mfe_a = sum(x["quality"]["mfe_pct"] for x in ts) / len(ts)
        mae_a = sum(x["quality"]["mae_pct"] for x in ts) / len(ts)
        print(f"  {er}: n={len(ts)} WR={100*len(w)/len(ts):.0f}% PnL={p:+.2f} MFE={mfe_a:.1f}% MAE={mae_a:.1f}%")

    print()
    print("Por hora UTC:")
    by_hour = defaultdict(list)
    for t in lst:
        h = datetime.datetime.utcfromtimestamp(t["entry"]["time"]).hour
        by_hour[h].append(t)
    for h in sorted(by_hour.keys()):
        ts = by_hour[h]
        w = [x for x in ts if x["quality"]["win"]]
        p = sum(x["exit"]["pnl_usdt"] for x in ts)
        print(f"  {h:02d}h UTC: n={len(ts)} WR={100*len(w)/len(ts):.0f}% PnL={p:+.2f}")

    print()
    print("Por ema_trend_4h:")
    ema4h_buckets = defaultdict(list)
    for t in lst:
        sig = t["entry"].get("signal", {})
        v = sig.get("ema_trend_4h")
        if v is None:
            v = "N/A"
        ema4h_buckets[v].append(t)
    for v in sorted(ema4h_buckets.keys(), key=lambda x: (x == "N/A", x)):
        ts = ema4h_buckets[v]
        w = [x for x in ts if x["quality"]["win"]]
        p = sum(x["exit"]["pnl_usdt"] for x in ts)
        print(f"  ema4h={v}: n={len(ts)} WR={100*len(w)/len(ts):.0f}% PnL={p:+.2f}")

    print()
    print("Por liq_cascade:")
    for lc in [True, False]:
        ts = [t for t in lst if t["entry"]["signal"].get("liq_cascade") == lc]
        if not ts:
            continue
        w = [x for x in ts if x["quality"]["win"]]
        p = sum(x["exit"]["pnl_usdt"] for x in ts)
        mfe_a = sum(x["quality"]["mfe_pct"] for x in ts) / len(ts)
        print(f"  liq_cascade={lc}: n={len(ts)} WR={100*len(w)/len(ts):.0f}% PnL={p:+.2f} MFE={mfe_a:.1f}%")

    print()
    print("Por cvd_change_pct (buckets):")
    buckets = {"<0": [], "0-5": [], "5-20": [], "20-50": [], ">50": []}
    for t in lst:
        cvd = t["entry"]["signal"].get("cvd_change_pct", 0) or 0
        if cvd < 0:
            buckets["<0"].append(t)
        elif cvd < 5:
            buckets["0-5"].append(t)
        elif cvd < 20:
            buckets["5-20"].append(t)
        elif cvd < 50:
            buckets["20-50"].append(t)
        else:
            buckets[">50"].append(t)
    for b, ts in buckets.items():
        if not ts:
            continue
        w = [x for x in ts if x["quality"]["win"]]
        p = sum(x["exit"]["pnl_usdt"] for x in ts)
        print(f"  CVD {b}%: n={len(ts)} WR={100*len(w)/len(ts):.0f}% PnL={p:+.2f}")

    print()
    print("TOP 5 winners:")
    for t in sorted(wins, key=lambda x: -x["exit"]["pnl_usdt"])[:5]:
        sig = t["entry"]["signal"]
        sym = t["symbol"]
        pnl_p = t["exit"]["pnl_pct"]
        mfe_p = t["quality"]["mfe_pct"]
        er = t["exit"]["reason"]
        e4 = sig.get("ema_trend_4h")
        liq = sig.get("liq_short_1m")
        casc = sig.get("liq_cascade")
        cvd = sig.get("cvd_change_pct", 0)
        print(f"  {sym} +{pnl_p:.1f}% MFE={mfe_p:.1f}% exit={er} ema4h={e4} liq={liq} casc={casc} cvd={cvd:.1f}%")

    print()
    print("TOP 5 losers:")
    for t in sorted(loses, key=lambda x: x["exit"]["pnl_usdt"])[:5]:
        sig = t["entry"]["signal"]
        sym = t["symbol"]
        pnl_p = t["exit"]["pnl_pct"]
        mfe_p = t["quality"]["mfe_pct"]
        er = t["exit"]["reason"]
        e4 = sig.get("ema_trend_4h")
        liq = sig.get("liq_short_1m")
        casc = sig.get("liq_cascade")
        cvd = sig.get("cvd_change_pct", 0)
        print(f"  {sym} {pnl_p:.1f}% MFE={mfe_p:.1f}% exit={er} ema4h={e4} liq={liq} casc={casc} cvd={cvd:.1f}%")

    print()
    print("squeeze_failed breakdown:")
    sf = [t for t in lst if t["exit"]["reason"] == "squeeze_failed"]
    for t in sf:
        sig = t["entry"]["signal"]
        sym = t["symbol"]
        mfe_p = t["quality"]["mfe_pct"]
        e4 = sig.get("ema_trend_4h")
        liq = sig.get("liq_short_1m")
        casc = sig.get("liq_cascade")
        cvd = sig.get("cvd_change_pct", 0)
        score = sig.get("signal_score") or sig.get("score")
        bypass = sig.get("lsr_bypass_active")
        streak = sig.get("cvd_streak")
        p = t["exit"]["pnl_usdt"]
        print(f"  {sym} MFE={mfe_p:.1f}% PnL={p:+.2f} ema4h={e4} liq={liq} casc={casc} cvd={cvd:.1f}% score={score} bypass={bypass} streak={streak}")

analyze_deep(post, "POS-RESET DNA 12/06")
print()
print("=" * 60)
print("COMPARATIVO PRE vs POS RESET")
print("=" * 60)
pre = [t for t in closed if t["entry"]["time"] < RESET_TS]
for lst, lab in [(pre, "PRE"), (post, "POS")]:
    if not lst: continue
    wins = [t for t in lst if t["quality"]["win"]]
    pnl = sum(t["exit"]["pnl_usdt"] for t in lst)
    gl = abs(sum(t["exit"]["pnl_usdt"] for t in lst if not t["quality"]["win"]))
    gp = sum(t["exit"]["pnl_usdt"] for t in lst if t["quality"]["win"])
    pf = gp/gl if gl else 999
    print(f"  {lab}: n={len(lst)} WR={100*len(wins)/len(lst):.1f}% PnL={pnl:+.2f} PF={pf:.2f}")
