import json
from pathlib import Path
from datetime import datetime

def main():
    paper_path = Path("logs/paper_opportunities.json")
    if not paper_path.exists():
        print(f"Arquivo {paper_path} não encontrado!")
        return
    
    with open(paper_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    closed = data.get("closed", [])
    wins = [t for t in closed if t.get("exit", {}).get("pnl_pct", 0) >= 0]
    losses = [t for t in closed if t.get("exit", {}).get("pnl_pct", 0) < 0]
    
    if closed:
        win_rate = (len(wins) / len(closed)) * 100
    else:
        win_rate = 0.0
    
    print("=" * 80)
    print("ANÁLISE DOS TRADES DE HOJE")
    print("=" * 80)
    print(f"Total de trades fechados: {len(closed)}")
    print(f"Vitórias: {len(wins)}")
    print(f"Derrotas: {len(losses)}")
    print(f"Win rate: {win_rate:.1f}%")
    print()
    
    print("=" * 80)
    print("ANÁLISE DOS DERROTAS:")
    print("=" * 80)
    
    # Analisar cada derrota
    for i, t in enumerate(losses[:20]):  # Mostrar as primeiras 20 derrotas
        symbol = t.get("symbol")
        entry_signal = t.get("entry", {}).get("signal", {})
        exp = entry_signal.get("exp", 0)
        lsr_trend = entry_signal.get("lsr_trend", 0)
        trades_1m = entry_signal.get("trades_1m", 0)
        
        print(f"{i+1}. {symbol}: exp={exp:.4f} | lsr_trend={lsr_trend:.4f} | trades_1m={trades_1m}")
    
    # Contar quantas derrotas têm lsr_trend = 0
    losses_zero_lsr = [t for t in losses if t.get("entry", {}).get("signal", {}).get("lsr_trend", 0) == 0]
    losses_low_exp = [t for t in losses if t.get("entry", {}).get("signal", {}).get("exp", 0) < 2]
    losses_low_trades = [t for t in losses if t.get("entry", {}).get("signal", {}).get("trades_1m", 0) < 15]
    
    print()
    print("=" * 80)
    print("PADRÕES DE DERROTA:")
    print("=" * 80)
    print(f"- lsr_trend = 0: {len(losses_zero_lsr)} derrotas ({(len(losses_zero_lsr)/len(losses)*100):.1f}% das derrotas)")
    print(f"- exp < 2: {len(losses_low_exp)} derrotas ({(len(losses_low_exp)/len(losses)*100):.1f}% das derrotas)")
    print(f"- trades_1m < 15: {len(losses_low_trades)} derrotas ({(len(losses_low_trades)/len(losses)*100):.1f}% das derrotas)")

if __name__ == "__main__":
    main()
