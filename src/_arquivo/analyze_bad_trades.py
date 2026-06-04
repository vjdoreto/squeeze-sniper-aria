# analyze_bad_trades.py — rodar na pasta do bot
import json
from pathlib import Path
from collections import defaultdict

def analyze_trades_from_file(file_path: Path):
    trades = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            trades.append(json.loads(line))
    return trades


if __name__ == "__main__":
    current_log_path = Path("logs/paper_closed.jsonl")
    backup_log_path = Path("backups/LATEST_SESSION/paper_closed.jsonl")

    trades = []

    if current_log_path.exists():
        print(f"Analisando trades de: {current_log_path}")
        trades = analyze_trades_from_file(current_log_path)
    elif backup_log_path.exists():
        print(f"Analisando trades de backup: {backup_log_path}")
        trades = analyze_trades_from_file(backup_log_path)
    else:
        print("Erro: Nenhum arquivo 'paper_closed.jsonl' encontrado em 'logs/' ou 'backups/LATEST_SESSION/'.")
        exit()

    if not trades:
        print("Nenhum trade encontrado para análise.")
        exit()

    wins = [t for t in trades if t["exit"]["pnl_pct"] >= 0]
    losses = [t for t in trades if t["exit"]["pnl_pct"] < 0]

    print(f"Total: {len(trades)} | Wins: {len(wins)} | Losses: {len(losses)}")
    print(f"Win rate: {len(wins)/len(trades)*100:.1f}%")
    print(f"Avg PnL: {sum(t['exit']['pnl_pct'] for t in trades)/len(trades):.3f}%")
    print()

    # Analisar Duração (Sprint 6.46)
    dur_wins = [t.get("live", {}).get("duration_sec", 0) for t in wins]
    dur_losses = [t.get("live", {}).get("duration_sec", 0) for t in losses]
    if dur_wins:
        print(f"Duração média VITÓRIAS: {sum(dur_wins)/len(dur_wins):.1f}s")
    if dur_losses:
        print(f"Duração média DERROTAS: {sum(dur_losses)/len(dur_losses):.1f}s")
    print()

    # Analisar RSI na entrada
    rsi_wins = [t.get("entry", {}).get("metrics", {}).get("rsi_5m", 0) for t in wins]
    rsi_losses = [t.get("entry", {}).get("metrics", {}).get("rsi_5m", 0) for t in losses]
    if rsi_wins:
        print(f"RSI médio nas VITÓRIAS: {sum(rsi_wins)/len(rsi_wins):.1f}")
    if rsi_losses:
        print(f"RSI médio nas DERROTAS: {sum(rsi_losses)/len(rsi_losses):.1f}")
    print()

    # Analisar por motivo de saída
    by_exit = defaultdict(list)
    for t in trades:
        by_exit[t["exit"]["reason"]].append(t["exit"]["pnl_pct"])

    for reason, pnls in by_exit.items():
        print(f"Saída por '{reason}': {len(pnls)} trades, avg {sum(pnls)/len(pnls):.3f}%")
    print()

    # Analisar MFE vs MAE (captura de movimento)
    avg_mfe = sum(t.get("quality", {}).get("mfe_pct", 0) for t in losses) / len(losses) if losses else 0
    avg_mae = sum(t.get("quality", {}).get("mae_pct", 0) for t in losses) / len(losses) if losses else 0
    
    # Trades que poderiam ter sido protegidos
    wasted_opportunities = [t for t in losses if t.get("quality", {}).get("mfe_pct", 0) >= 1.5]
    
    print(f"Derrotas — MFE médio: {avg_mfe:.2f}% | MAE médio: {avg_mae:.2f}%")
    print(f"⚠️ Trades 'Enforcados': {len(wasted_opportunities)} trades subiram >1.5% e terminaram em LOSS.")
    print("(MFE muito baixo nos losses = entrada tardia, pouco upside restante)")