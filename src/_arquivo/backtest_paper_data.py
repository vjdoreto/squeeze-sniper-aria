"""
Backtesting com dados reais do Paper
Valida se os sinais do paper teriam funcionado em live com os mesmos parâmetros.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_paper_trades() -> List[Dict[str, Any]]:
    """Carrega trades fechados do paper (JSONL)."""
    path = Path("logs/paper_closed.jsonl")
    if not path.exists():
        logger.warning("Arquivo paper_closed.jsonl não encontrado")
        return []
    
    trades = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return trades


def load_snapshots() -> Dict[str, List[Dict]]:
    """Carrega snapshots históricos para backtesting."""
    history_dir = Path("logs/history")
    if not history_dir.exists():
        logger.warning("Diretório logs/history não encontrado")
        return {}
    
    snapshots = {}
    for file_path in history_dir.glob("*.csv"):
        symbol = file_path.stem
        try:
            import csv
            with file_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                snapshots[symbol] = list(reader)
        except Exception as e:
            logger.warning(f"Erro ao ler {file_path}: {e}")
    
    return snapshots


def backtest_trade(
    trade: Dict[str, Any],
    snapshots: Dict[str, List[Dict]],
    slippage_pct: float = 0.01,
) -> Dict[str, Any]:
    """
    Simula o trade com slippage realista.
    
    Args:
        trade: Trade do paper
        snapshots: Snapshots históricos por símbolo
        slippage_pct: Slippage simulado (0.01 = 1%)
    
    Returns:
        Dict com resultados do backtest
    """
    symbol = trade["symbol"]
    entry = trade.get("entry", {})
    exit_data = trade.get("exit", {})
    
    entry_price = entry.get("price")
    exit_price = exit_data.get("price")
    
    if not entry_price or not exit_price:
        return {"error": "missing_prices"}
    
    # Simula slippage na entrada
    entry_price_slipped = entry_price * (1 + slippage_pct / 100)
    
    # Simula slippage na saída
    exit_price_slipped = exit_price * (1 - slippage_pct / 100)
    
    # Recalcula PnL com slippage
    pnl_pct_paper = exit_data.get("pnl_pct", 0)
    pnl_pct_backtest = ((exit_price_slipped - entry_price_slipped) / entry_price_slipped) * 100
    
    # Diferença de PnL
    pnl_diff = pnl_pct_backtest - pnl_pct_paper
    
    return {
        "symbol": symbol,
        "entry_price": entry_price,
        "entry_price_slipped": entry_price_slipped,
        "exit_price": exit_price,
        "exit_price_slipped": exit_price_slipped,
        "pnl_pct_paper": pnl_pct_paper,
        "pnl_pct_backtest": pnl_pct_backtest,
        "pnl_diff_pct": pnl_diff,
        "slippage_pct": slippage_pct,
        "would_have_won": pnl_pct_backtest > 0,
        "paper_won": pnl_pct_paper > 0,
    }


def run_backtest(slippage_pct: float = 0.01):
    """Executa backtest completo dos trades do paper."""
    logger.info("=== Backtesting Paper Data ===")
    logger.info(f"Slippage simulado: {slippage_pct}%")
    
    paper_trades = load_paper_trades()
    logger.info(f"Trades Paper carregados: {len(paper_trades)}")
    
    if not paper_trades:
        logger.warning("Nenhum trade para backtest")
        return
    
    snapshots = load_snapshots()
    logger.info(f"Snapshots carregados: {len(snapshots)} símbolos")
    
    results = []
    for trade in paper_trades:
        result = backtest_trade(trade, snapshots, slippage_pct)
        results.append(result)
    
    # Estatísticas
    total_trades = len(results)
    paper_wins = sum(1 for r in results if r.get("paper_won"))
    backtest_wins = sum(1 for r in results if r.get("would_have_won"))
    
    avg_pnl_paper = sum(r["pnl_pct_paper"] for r in results) / total_trades if total_trades > 0 else 0
    avg_pnl_backtest = sum(r["pnl_pct_backtest"] for r in results) / total_trades if total_trades > 0 else 0
    
    logger.info(f"\n=== Resultados do Backtest ===")
    logger.info(f"Total de trades: {total_trades}")
    logger.info(f"Paper wins: {paper_wins} ({paper_wins/total_trades*100:.1f}%)")
    logger.info(f"Backtest wins: {backtest_wins} ({backtest_wins/total_trades*100:.1f}%)")
    logger.info(f"PnL médio Paper: {avg_pnl_paper:.2f}%")
    logger.info(f"PnL médio Backtest: {avg_pnl_backtest:.2f}%")
    logger.info(f"Impacto do slippage: {avg_pnl_backtest - avg_pnl_paper:.2f}%")
    
    # Detalhe de trades que mudaram de resultado
    flipped = [r for r in results if r.get("paper_won") != r.get("would_have_won")]
    if flipped:
        logger.info(f"\nTrades que mudaram de resultado: {len(flipped)}")
        for r in flipped:
            logger.info(
                f"  {r['symbol']}: Paper={r['pnl_pct_paper']:.2f}% "
                f"→ Backtest={r['pnl_pct_backtest']:.2f}% "
                f"({'GANHOU' if r['would_have_won'] else 'PERDEU'})"
            )
    
    # Salvar resultado
    output_path = Path("logs/backtest_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "slippage_pct": slippage_pct,
        "total_trades": total_trades,
        "paper_wins": paper_wins,
        "backtest_wins": backtest_wins,
        "avg_pnl_paper": avg_pnl_paper,
        "avg_pnl_backtest": avg_pnl_backtest,
        "flipped_trades": len(flipped),
        "results": results,
    }
    
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nResultado salvo em: {output_path}")


if __name__ == "__main__":
    # Testa com diferentes níveis de slippage
    for slippage in [0.01, 0.05, 0.1]:  # 0.01%, 0.05%, 0.1%
        logger.info(f"\n{'='*60}")
        run_backtest(slippage)
