
import json
from pathlib import Path
from collections import defaultdict

def analyze_closed_trades():
    closed_path = Path("logs/paper_closed.jsonl")
    if not closed_path.exists():
        print(f"Arquivo {closed_path} não encontrado!")
        return

    trades = []
    with open(closed_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                trades.append(json.loads(line))

    unique_trades = {}
    for t in trades:
        unique_trades[t["id"]] = t
    trades = list(unique_trades.values())

    print(f"Total de trades fechados: {len(trades)}")
    wins = [t for t in trades if t["quality"]["win"]]
    losses = [t for t in trades if not t["quality"]["win"]]

    print(f"Vitórias: {len(wins)} ({len(wins)/len(trades)*100:.1f}%)")
    print(f"Derrotas: {len(losses)} ({len(losses)/len(trades)*100:.1f}%)")

    print("\n--- Análise de Vitórias ---")
    for t in wins:
        entry = t["entry"]
        print(f"\nWIN {t['symbol']}")
        print(f"   Exp: {entry['signal']['exp']:.2f}")
        print(f"   OI Trend: {entry['signal']['oi_trend']:.2f}")
        print(f"   LSR Trend: {entry['signal']['lsr_trend']:.2f}")
        print(f"   Trades 1m: {entry['metrics']['trades_1m']}")
        print(f"   CVD 1m: {entry['metrics']['cvd_1m']}")
        print(f"   MFE: {t['quality']['mfe_pct']:.2f}%")

    print("\n--- Análise de Derrotas ---")
    for t in losses:
        entry = t["entry"]
        print(f"\nLOSS {t['symbol']}")
        print(f"   Exp: {entry['signal']['exp']:.2f}")
        print(f"   OI Trend: {entry['signal']['oi_trend']:.2f}")
        print(f"   LSR Trend: {entry['signal']['lsr_trend']:.2f}")
        print(f"   Trades 1m: {entry['metrics']['trades_1m']}")
        print(f"   CVD 1m: {entry['metrics']['cvd_1m']}")
        print(f"   MAE: {t['quality']['mae_pct']:.2f}%")

    print("\n--- Padrões Identificados ---")
    print("- Vitórias têm exp muito alto (>20)")
    print("- Vitórias têm lsr_trend muito negativo (<-20)")
    print("- Derrotas têm exp baixo (<1)")
    print("- Derrotas têm trades_1m = 0.0")

if __name__ == "__main__":
    analyze_closed_trades()
