import json
from collections import defaultdict

lines = open("logs/paper_closed.jsonl", encoding="utf-8").readlines()
trades = [json.loads(l.strip()) for l in lines if l.strip()]
RESET_TS = 1781306700.0
closed = [t for t in trades if t.get("exit") and t["exit"].get("reason")]
post = [t for t in closed if t["entry"]["time"] >= RESET_TS]
wins = [t for t in post if t["quality"]["win"]]
loses = [t for t in post if not t["quality"]["win"]]

print("=== ALPHA DECAY ===")
def decay_stats(lst, label):
    snaps_5m, snaps_4h, snaps_24h = [], [], []
    for t in lst:
        pt = t.get("post_trade", {})
        snaps = pt.get("snapshots", {})
        if "5m" in snaps:
            snaps_5m.append(snaps["5m"]["pct"])
        if "4h" in snaps:
            snaps_4h.append(snaps["4h"]["pct"])
        if "24h" in snaps and snaps["24h"].get("pct") is not None:
            snaps_24h.append(snaps["24h"]["pct"])
    print(f"{label} (n={len(lst)}):")
    for snaps, tf in [(snaps_5m, "5m"), (snaps_4h, "4h"), (snaps_24h, "24h")]:
        if snaps:
            avg = sum(snaps) / len(snaps)
            up = sum(1 for v in snaps if v > 0)
            print(f"  {tf} pos-saida: n={len(snaps)} avg={avg:.2f}% positivos={up}/{len(snaps)}")

decay_stats(post, "TODOS pos-reset")
decay_stats(wins, "Winners")
decay_stats(loses, "Losers")

print()
print("=== STOP LOSS DETALHADO ===")
sls = [t for t in post if t["exit"]["reason"] == "stop_loss"]
for t in sls:
    sig = t["entry"]["signal"]
    sym = t["symbol"]
    entry_px = t["entry"]["price"]
    exit_px = t["exit"]["price"]
    targets = t.get("targets", {})
    sl_target = targets.get("sl_price") or targets.get("stop_loss")
    pnl = t["exit"]["pnl_pct"]
    ema4 = sig.get("ema_trend_4h")
    casc = sig.get("liq_cascade")
    cvd = sig.get("cvd_change_pct", 0)
    mae = t["quality"]["mae_pct"]
    print(f"  {sym}: pnl={pnl:.1f}% MAE={mae:.1f}% ema4h={ema4} cascade={casc} cvd={cvd:.1f}%")
    print(f"    entry={entry_px:.8f} exit={exit_px:.8f} sl_target={sl_target}")

print()
print("=== RIFUSDT e TRUMPUSDT ghost analysis (top bloqueados) ===")
ghosts = []
with open("logs/ghost_signals.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            g = json.loads(line)
            if g.get("ts", 0) >= RESET_TS:
                ghosts.append(g)
        except:
            pass

for sym in ["RIFUSDT", "TRUMPUSDT", "TAOUSDT"]:
    these = [g for g in ghosts if g.get("symbol") == sym]
    if not these:
        continue
    rc = defaultdict(int)
    for g in these:
        rc[g.get("reason_code", "?")] += 1
    g = these[0]
    score = g.get("score")
    ema4 = g.get("ema_trend_4h")
    lsr = g.get("lsr_trend", 0)
    liq = g.get("liq_short_1m", 0)
    casc = g.get("liq_cascade")
    cvd = g.get("cvd_change_pct", 0)
    print(f"{sym}: n={len(these)} reason={dict(rc)} score={score} ema4h={ema4} lsr_trend={lsr:.4f} liq={liq:.0f} cascade={casc} cvd={cvd:.1f}%")

print()
print("=== SQUEEZE_FAILED PATTERN ANALYSIS ===")
sf = [t for t in post if t["exit"]["reason"] == "squeeze_failed"]
print(f"squeeze_failed: {len(sf)}/25 trades = {100*len(sf)/25:.0f}% dos trades")

# Padroes nos squeeze_failed
large_caps = ["XRPUSDT", "ADAUSDT", "TRUMPUSDT", "SPXUSDT"]
with_cascade = [t for t in sf if t["entry"]["signal"].get("liq_cascade")]
large = [t for t in sf if t["symbol"] in large_caps]
low_cvd = [t for t in sf if (t["entry"]["signal"].get("cvd_change_pct") or 0) < 5]
high_streak = [t for t in sf if (t["entry"]["signal"].get("cvd_streak") or 0) > 30]

print(f"  Com liq_cascade=True: {len(with_cascade)}/{len(sf)}")
print(f"  Large caps (XRP/ADA/TRUMP/SPX): {len(large)}/{len(sf)}")
print(f"  CVD < 5%: {len(low_cvd)}/{len(sf)}")
print(f"  cvd_streak > 30: {len(high_streak)}/{len(sf)}")

# Classificar squeeze_failed por causa provavel
print()
print("Squeeze_failed classificados:")
for t in sf:
    sig = t["entry"]["signal"]
    sym = t["symbol"]
    ema4 = sig.get("ema_trend_4h")
    casc = sig.get("liq_cascade")
    cvd = sig.get("cvd_change_pct", 0) or 0
    liq = sig.get("liq_short_1m", 0) or 0
    streak = sig.get("cvd_streak", 0) or 0
    score = sig.get("signal_score") or sig.get("score")
    pnl = t["exit"]["pnl_usdt"]

    issues = []
    if ema4 is not None and ema4 <= -2:
        issues.append(f"EMA4H={ema4}")
    if liq < 1000:
        issues.append(f"liq_baixa={liq:.0f}")
    if cvd < 5:
        issues.append(f"CVD_fraco={cvd:.1f}%")
    if sym in ["XRPUSDT", "ADAUSDT"]:
        issues.append("LARGE_CAP")
    if streak < 5:
        issues.append(f"streak={streak}")
    causa = " | ".join(issues) if issues else "?"
    print(f"  {sym} PnL={pnl:+.2f} ema4h={ema4} cascade={casc} cvd={cvd:.1f}% liq={liq:.0f} streak={streak} -> {causa}")
