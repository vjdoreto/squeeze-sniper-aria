
import json
from pathlib import Path
from collections import defaultdict

# Paths
LOGS_DIR = Path(__file__).parent.parent / "logs"
PAPER_CLOSED = LOGS_DIR / "paper_closed.jsonl"
SIGNALS = LOGS_DIR / "signals.jsonl"
REFUSALS = LOGS_DIR / "signal_refusals.jsonl"
GHOST_SIGNALS = LOGS_DIR / "ghost_signals.jsonl"

def load_jsonl(path):
    data = []
    if not path.exists():
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except Exception as e:
                    print(f"Error parsing line in {path.name}: {e}")
    return data

def analyze_trades():
    print("=" * 80)
    print("ANÁLISE DETALHADA DOS TRADES")
    print("=" * 80)

    trades = load_jsonl(PAPER_CLOSED)
    print(f"\nTotal de trades fechados: {len(trades)}")

    wins = []
    losses = []
    all_trade_info = []
    symbol_stats = defaultdict(lambda: {"count": 0, "win": 0, "loss": 0, "total_pnl": 0.0})

    for i, trade in enumerate(trades, 1):
        symbol = trade["symbol"]
        pnl = trade["entry"]["realized_pnl_usdt"]
        signal = trade["entry"]["signal"]
        score = signal["score"]
        cvd_1m = signal["cvd_1m"]
        cvd_change = signal["cvd_change_pct"]
        rsi_5m = signal["rsi_5m"]
        trades_1m = signal["trades_1m"]
        exp_btc_norm_1h = signal.get("exp_btc_norm_1h", "N/A")
        relax_label = signal.get("relax_label", "N/A")

        trade_info = {
            "index": i,
            "symbol": symbol,
            "pnl": pnl,
            "score": score,
            "cvd_1m": cvd_1m,
            "cvd_change_pct": cvd_change,
            "rsi_5m": rsi_5m,
            "trades_1m": trades_1m,
            "exp_btc_norm_1h": exp_btc_norm_1h,
            "relax_label": relax_label
        }
        all_trade_info.append(trade_info)

        symbol_stats[symbol]["count"] += 1
        symbol_stats[symbol]["total_pnl"] += pnl

        if pnl > 0:
            wins.append(trade_info)
            symbol_stats[symbol]["win"] += 1
        else:
            losses.append(trade_info)
            symbol_stats[symbol]["loss"] += 1

    # Print summary
    print(f"\nWIN RATE: {len(wins)}/{len(trades)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"Total PNL: {sum(t['pnl'] for t in all_trade_info):.2f} USDT")

    print("\n" + "=" * 80)
    print("TRADES VENCEDORES")
    print("=" * 80)
    for w in wins:
        print(f"\n{w['index']}. {w['symbol']}: +{w['pnl']:.2f} USDT")
        print(f"   Score: {w['score']} | CVD 1m: {w['cvd_1m']} | CVD %: {w['cvd_change_pct']:.1f}")
        print(f"   RSI 5m: {w['rsi_5m']:.1f} | Trades 1m: {w['trades_1m']} | Exp BTC 1h: {w['exp_btc_norm_1h']}")
        print(f"   Relax Label: {w['relax_label']}")

    print("\n" + "=" * 80)
    print("ESTATÍSTICAS POR SÍMBOLO")
    print("=" * 80)
    for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]["total_pnl"], reverse=True):
        print(f"\n{symbol}:")
        print(f"   Total: {stats['count']} | Wins: {stats['win']} | Losses: {stats['loss']}")
        print(f"   PNL Total: {stats['total_pnl']:.2f} USDT")

    # Analyze refusals
    print("\n" + "=" * 80)
    print("ANÁLISE DE RECUSAS DE SINAIS")
    print("=" * 80)
    refusals = load_jsonl(REFUSALS)
    refusal_reasons = defaultdict(int)
    for ref in refusals:
        reason = ref.get("reason", "unknown")
        refusal_reasons[reason] += 1

    print(f"\nTotal de recusas: {len(refusals)}")
    print("\nPrincipais motivos:")
    for reason, count in sorted(refusal_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"   {reason}: {count}")

if __name__ == "__main__":
    analyze_trades()
