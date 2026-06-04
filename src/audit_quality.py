import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional, Tuple

PAPER_CLOSED_JSONL = Path("logs/paper_closed.jsonl")
REFUSALS_JSONL = Path("logs/signal_refusals.jsonl")

OUT_JSON = Path("logs/audit_quality_report.json")
OUT_TEXT = Path("logs/audit_quality_report.txt")


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _bucket(value: Optional[float], buckets: List[Tuple[Optional[float], Optional[float]]]) -> str:
    """
    buckets: list of (low_inclusive, high_exclusive) with None meaning -inf/+inf.
    """
    if value is None:
        return "none"

    for low, high in buckets:
        # -inf .. high
        if low is None and high is not None:
            high_f = float(high)
            if value < high_f:
                return f"<{high_f}"
        # low .. +inf
        elif low is not None and high is None:
            low_f = float(low)
            if value >= low_f:
                return f">={low_f}"
        # low .. high
        elif low is not None and high is not None:
            low_f = float(low)
            high_f = float(high)
            if value >= low_f and value < high_f:
                return f"[{low_f},{high_f})"

    return "other"


def analyze_paper(closed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(closed_trades)
    if total == 0:
        return {"total_trades": 0}

    # overall
    def pnl_pct_or_none(t: Dict[str, Any]) -> Optional[float]:
        return _safe_float((t.get("exit") or {}).get("pnl_pct"))

    wins: List[Dict[str, Any]] = [
        t for t in closed_trades
        if (p := pnl_pct_or_none(t)) is not None and p >= 0
    ]
    losses: List[Dict[str, Any]] = [t for t in closed_trades if t not in wins]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total * 100.0

    def avg(field_path: List[str]) -> float:
        s = 0.0
        n = 0
        for t in closed_trades:
            cur: Any = t
            for k in field_path:
                if not isinstance(cur, dict):
                    cur = None
                    break
                cur = cur.get(k)
            v = _safe_float(cur)
            if v is not None:
                s += v
                n += 1
        return s / n if n else 0.0

    avg_pnl = avg(["exit", "pnl_pct"])
    avg_mfe = avg(["quality", "mfe_pct"])
    avg_mae = avg(["quality", "mae_pct"])

    # per-symbol aggregation
    per_symbol: Dict[str, Dict[str, Any]] = {}
    for t in closed_trades:
        sym = str(t.get("symbol") or "UNKNOWN")
        per_symbol.setdefault(sym, {
            "total": 0,
            "wins": 0,
            "pnl_sum": 0.0,
            "mfe_sum": 0.0,
            "mae_sum": 0.0,
            "exp_sum": 0.0,
            "oi_trend_sum": 0.0,
            "lsr_trend_sum": 0.0,
            "exp_samples": 0,
            "oi_trend_samples": 0,
            "lsr_trend_samples": 0,
            "trades_1m_samples": 0,
            "trades_1m_sum": 0.0,
            "favorable_early": 0,
        })
        rec = per_symbol[sym]
        rec["total"] += 1
        pnl = _safe_float((t.get("exit") or {}).get("pnl_pct"))
        if pnl is not None:
            rec["pnl_sum"] += pnl
        mfe = _safe_float((t.get("quality") or {}).get("mfe_pct"))
        if mfe is not None:
            rec["mfe_sum"] += mfe
        mae = _safe_float((t.get("quality") or {}).get("mae_pct"))
        if mae is not None:
            rec["mae_sum"] += mae

        if pnl is not None and pnl >= 0:
            rec["wins"] += 1

        exp = _safe_float((t.get("entry") or {}).get("signal", {}).get("exp"))
        oi_trend = _safe_float((t.get("entry") or {}).get("signal", {}).get("oi_trend"))
        lsr_trend = _safe_float((t.get("entry") or {}).get("signal", {}).get("lsr_trend"))
        if exp is not None:
            rec["exp_sum"] += exp
            rec["exp_samples"] += 1
        if oi_trend is not None:
            rec["oi_trend_sum"] += oi_trend
            rec["oi_trend_samples"] += 1
        if lsr_trend is not None:
            rec["lsr_trend_sum"] += lsr_trend
            rec["lsr_trend_samples"] += 1

        trades_1m = (t.get("entry") or {}).get("metrics", {}).get("trades_1m", None)
        trades_1m_f = _safe_float(trades_1m)
        if trades_1m_f is not None:
            rec["trades_1m_sum"] += trades_1m_f
            rec["trades_1m_samples"] += 1

        if bool((t.get("quality") or {}).get("favorable_early")):
            rec["favorable_early"] += 1

    for sym, rec in per_symbol.items():
        total_sym = rec["total"]
        rec["win_rate"] = rec["wins"] / total_sym * 100.0 if total_sym else 0.0
        rec["avg_pnl"] = rec["pnl_sum"] / total_sym if total_sym else 0.0
        rec["avg_mfe"] = rec["mfe_sum"] / total_sym if total_sym else 0.0
        rec["avg_mae"] = rec["mae_sum"] / total_sym if total_sym else 0.0
        rec["avg_exp"] = rec["exp_sum"] / rec["exp_samples"] if rec["exp_samples"] else 0.0
        rec["avg_oi_trend"] = rec["oi_trend_sum"] / rec["oi_trend_samples"] if rec["oi_trend_samples"] else 0.0
        rec["avg_lsr_trend"] = rec["lsr_trend_sum"] / rec["lsr_trend_samples"] if rec["lsr_trend_samples"] else 0.0
        rec["avg_trades_1m"] = rec["trades_1m_sum"] / rec["trades_1m_samples"] if rec["trades_1m_samples"] else 0.0
        rec["early_rate"] = rec["favorable_early"] / total_sym * 100.0 if total_sym else 0.0

    # buckets for quick insight
    exp_buckets = [
        (None, 0.1),
        (0.1, 0.2),
        (0.2, 0.5),
        (0.5, 1.0),
        (1.0, None),
    ]
    lsrchg_buckets = [
        (None, -10),
        (-10, -5),
        (-5, -2),
        (-2, -0.5),
        (-0.5, None),
    ]
    tr1m_buckets = [
        (None, 5),
        (5, 20),
        (20, 60),
        (60, None),
    ]

    bucket_stats: Dict[str, Any] = {
        "exp": {},
        "lsr_change_pct": {},
        "trades_1m": {},
    }

    def init_bucket_map(buckets):
        d = {}
        for low, high in buckets:
            label = _bucket(None, [(low, high)])
            d[label] = {"n": 0, "wins": 0}
        return d

    bucket_stats["exp"] = init_bucket_map(exp_buckets)
    bucket_stats["lsr_change_pct"] = init_bucket_map(lsrchg_buckets)
    bucket_stats["trades_1m"] = init_bucket_map(tr1m_buckets)

    for t in closed_trades:
        sym = str(t.get("symbol") or "UNKNOWN")
        pnl = _safe_float((t.get("exit") or {}).get("pnl_pct"))
        is_win = pnl is not None and pnl >= 0

        exp = _safe_float((t.get("entry") or {}).get("signal", {}).get("exp"))
        lsr_chg = _safe_float((t.get("entry") or {}).get("signal", {}).get("lsr_change_pct"))
        tr1m = _safe_float((t.get("entry") or {}).get("metrics", {}).get("trades_1m"))

        b_exp = _bucket(exp, exp_buckets)
        b_lsr = _bucket(lsr_chg, lsrchg_buckets)
        b_tr1m = _bucket(tr1m, tr1m_buckets)

        for key, b, do_win in [
            ("exp", b_exp, is_win),
            ("lsr_change_pct", b_lsr, is_win),
            ("trades_1m", b_tr1m, is_win),
        ]:
            if b not in bucket_stats[key]:
                bucket_stats[key][b] = {"n": 0, "wins": 0}
            bucket_stats[key][b]["n"] += 1
            if do_win:
                bucket_stats[key][b]["wins"] += 1

    # compute win rates per bucket
    for key in list(bucket_stats.keys()):
        for b, rec in bucket_stats[key].items():
            n = rec["n"]
            rec["win_rate"] = rec["wins"] / n * 100.0 if n else 0.0

    return {
        "total_trades": total,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "avg_pnl_pct": avg_pnl,
        "avg_mfe_pct": avg_mfe,
        "avg_mae_pct": avg_mae,
        "per_symbol": per_symbol,
        "bucket_stats": bucket_stats,
    }


def analyze_refusals(refusals: List[Dict[str, Any]]) -> Dict[str, Any]:
    # each line from SqueezeIgnition._maybe_log_refusal includes ts, symbol, reason_code and extra.
    total = len(refusals)
    counts = Counter()
    per_symbol = defaultdict(lambda: Counter())
    per_reason = defaultdict(lambda: Counter())
    last_ts = None

    for r in refusals:
        sym = str(r.get("symbol") or "UNKNOWN")
        reason = str(r.get("reason_code") or "unknown")
        counts[reason] += 1
        per_symbol[sym][reason] += 1
        per_reason[reason][sym] += 1
        ts = _safe_float(r.get("ts"))
        if ts is not None:
            if last_ts is None or ts > last_ts:
                last_ts = ts

    top_reasons = counts.most_common(20)
    top_by_symbol = sorted(per_symbol.items(), key=lambda kv: sum(kv[1].values()), reverse=True)[:20]

    # Additionally compute whether refusal reasons mention key gates (heuristic)
    gate_groups = {
        "score": ("score_lt", "score", "score_lt_25"),
        "spread": ("spread", "bid_ask_spread", "spread_too_high"),
        "utc_time": ("utc_time_gate",),
        "vol_adaptive": ("vol_adaptive",),
        "lsr": ("lsr_trend", "lsr_", "lsr_change"),
        "oi": ("oi_change", "oi_lt", "oi_accel"),
        "rsi": ("rsi",),
        "funding": ("funding",),
        "cooldown": ("cooldown",),
        "final_gate": ("final_gate",),
    }

    gate_hist = Counter()
    for reason, c in counts.items():
        for group, keys in gate_groups.items():
            for k in keys:
                if k in reason:
                    gate_hist[group] += c
                    break

    return {
        "total_refusals": total,
        "last_ts": last_ts,
        "top_reasons": top_reasons,
        "top_reasons_by_symbol": [
            {"symbol": sym, "total": sum(c.values()), "top_reasons": c.most_common(8)}
            for sym, c in top_by_symbol
        ],
        "gate_histogram": gate_hist.most_common(20),
    }


def correlate(refusals_summary: Dict[str, Any], paper_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick correlation:
    For each symbol with both data:
      - compare win_rate (paper) and refusal total (ghost)
      - highlight symbols with high refusals but low wins, and vice-versa.
    """
    per_symbol_ref = refusals_summary.get("top_reasons_by_symbol", [])
    refusal_totals: Dict[str, int] = {x["symbol"]: int(x["total"]) for x in per_symbol_ref if "symbol" in x}

    per_symbol_paper = paper_summary.get("per_symbol", {})
    points = []
    for sym, rec in per_symbol_paper.items():
        if sym in refusal_totals:
            points.append({
                "symbol": sym,
                "refusal_total": refusal_totals[sym],
                "win_rate": rec.get("win_rate", 0.0),
                "paper_total": rec.get("total", 0),
                "avg_pnl": rec.get("avg_pnl", 0.0),
            })

    # sort and find interesting groups
    points_sorted_by_ref = sorted(points, key=lambda p: p["refusal_total"], reverse=True)
    high_ref_low_win = sorted(points, key=lambda p: (p["refusal_total"], -p["win_rate"]), reverse=True)[:15]
    low_ref_high_win = sorted(points, key=lambda p: (p["refusal_total"], -p["win_rate"]))[:15]

    return {
        "correlation_points_count": len(points),
        "top_symbols_by_refusals": points_sorted_by_ref[:20],
        "high_refusals_low_win_suspects": high_ref_low_win,
        "low_refusals_high_win_samples": low_ref_high_win,
    }


def main() -> None:
    closed = _read_jsonl(PAPER_CLOSED_JSONL)
    refusals = _read_jsonl(REFUSALS_JSONL)

    paper_summary = analyze_paper(closed)
    refusals_summary = analyze_refusals(refusals)

    report = {
        "paper": paper_summary,
        "ghost_refusals": refusals_summary,
        "correlation": correlate(refusals_summary, paper_summary),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # human readable subset
    lines: List[str] = []
    lines.append("=== AUDIT QUALITY REPORT ===")
    lines.append(f"Paper trades closed: {paper_summary.get('total_trades',0)} | win_rate={paper_summary.get('win_rate',0):.2f}%")
    lines.append(f"Avg PnL%={paper_summary.get('avg_pnl_pct',0):.3f} | Avg MFE%={paper_summary.get('avg_mfe_pct',0):.3f} | Avg MAE%={paper_summary.get('avg_mae_pct',0):.3f}")
    lines.append("")
    lines.append("Top refusal reasons (Ghost audit / refusals):")
    for reason, c in refusals_summary.get("top_reasons", []):
        lines.append(f"- {reason}: {c}")
    lines.append("")
    lines.append("Top symbols by win rate (paper, min 3 trades):")
    per_symbol = paper_summary.get("per_symbol", {})
    top = []
    for sym, rec in per_symbol.items():
        if rec.get("total", 0) >= 3:
            top.append((rec.get("win_rate",0.0), rec.get("total",0), sym, rec.get("avg_pnl",0.0)))
    top.sort(reverse=True)
    for wr, n, sym, ap in top[:20]:
        lines.append(f"- {sym}: win_rate={wr:.1f}% n={n} avg_pnl={ap:.3f}%")
    lines.append("")
    lines.append("Top symbols by MAE magnitude (paper, min 3 trades, worst drawdown):")
    worst = []
    for sym, rec in per_symbol.items():
        if rec.get("total", 0) >= 3:
            mae = rec.get("avg_mae", 0.0)
            worst.append((mae, rec.get("total", 0), sym, rec.get("win_rate",0.0)))
    # mae is negative typically, so "worst" = most negative (min)
    worst.sort(key=lambda x: x[0])
    for mae, n, sym, wr in worst[:20]:
        lines.append(f"- {sym}: avg_mae={mae:.3f}% n={n} win_rate={wr:.1f}%")

    OUT_TEXT.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()
