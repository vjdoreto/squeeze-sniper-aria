"""
Utilitários compartilhados para cálculo de sizing (Paper e Live)
Garante paridade na lógica de dimensionamento de posições.
"""
import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def calculate_position_size(
    available_capital: float,
    risk_pct: float,
    leverage: int,
    price: float,
    committed_margin: float = 0.0,
    min_margin_usdt: float = 0.5,
    max_notional_usdt: Optional[float] = None,
    step_size: str = "0.001",
) -> Dict[str, Any]:
    """
    Calcula tamanho da posição (quantidade, notional, margem) de forma unificada.
    
    Args:
        available_capital: Capital disponível (Equity - Margens Abertas)
        risk_pct: Risco por trade (ex: 0.05 para 5%)
        leverage: Alavancagem (ex: 10)
        price: Preço atual do ativo
        committed_margin: Margem já comprometida em posições abertas
        min_margin_usdt: Margem mínima para evitar quantidades lixo
        max_notional_usdt: Limite máximo de notional (opcional)
        step_size: Step size para arredondamento de quantidade
    
    Returns:
        Dict com: quantity, notional_usdt, usdt_margin, effective_capital
    """
    # Capital efetivo disponível
    effective_capital = max(0, available_capital - committed_margin)
    
    # Margem alvo
    usdt_margin_target = effective_capital * risk_pct
    
    # Validação de margem mínima
    if usdt_margin_target < min_margin_usdt:
        logger.info(
            "Margem alvo muito baixa (%.2f USDT). Tentando margem mínima (%.2f USDT)",
            usdt_margin_target, min_margin_usdt
        )
        usdt_margin_target = min_margin_usdt
        notional_target = usdt_margin_target * leverage
        if notional_target / price < 0.00001:
            return {
                "quantity": 0.0, "notional_usdt": 0.0, "usdt_margin": 0.0,
                "effective_capital": effective_capital, "error": "margin_too_baixa",
            }
    
    # Notional alvo
    notional_target = usdt_margin_target * leverage
    
    # Cap de notional (se fornecido)
    if max_notional_usdt and notional_target > max_notional_usdt:
        notional_target = max_notional_usdt
        logger.info(
            "Notional cap aplicado: %.2f USDT (original: %.2f)",
            max_notional_usdt,
            notional_target,
        )
    
    # Quantidade bruta
    raw_qty = notional_target / price if price > 0 else 0
    
    # Arredondamento para step size
    step = float(step_size)
    precision = len(step_size.split('.')[-1].rstrip('0')) if '.' in step_size else 0
    quantity = round(math.floor(raw_qty / step) * step, precision)
    
    # Recalcular notional e margem com quantidade arredondada
    actual_notional = quantity * price
    actual_margin = actual_notional / leverage
    
    return {
        "quantity": quantity,
        "notional_usdt": actual_notional,
        "usdt_margin": actual_margin,
        "effective_capital": effective_capital,
        "raw_notional_target": notional_target,
    }


def calculate_dynamic_risk_with_hft(base_risk_pct: float, trades_1m: int, min_hft_threshold: int = 15) -> float:
    """
    Aplica decaimento linear/peneira dinâmica no tamanho do risco (Kelly)
    baseado na atividade de trades HFT por minuto para evitar falsos squeezes.
    
    CRITICAL FIX: Threshold reduzido de 50 para 15 trades/min
    Análise dos logs mostrou que 85% dos sinais tinham 2-13 trades/min e passavam sem penalidade,
    resultando em entradas fracas com score 100 mas performance terrível (win rate 9.52%).
    """
    if trades_1m <= 0:
        return 0.0

    if trades_1m < min_hft_threshold:
        penalty_factor = trades_1m / min_hft_threshold
        return round(base_risk_pct * penalty_factor, 4)

    return base_risk_pct


def calculate_kelly_risk(
    closed_trades: list,
    base_risk_pct: float = 0.05,
    min_trades: int = 10,
    score: float = 0.0,
    is_high_quality: bool = False,
) -> float:
    """
    Calcula risco dinâmico via Kelly Criterion (Quarter-Kelly).
    SPRINT 12.145: Kelly Adaptativo (DNA eassets) - Aumenta risco para sinais A+
    
    Args:
        closed_trades: Lista de trades fechados com campo 'pnl_pct' no exit
        base_risk_pct: Risco base (fallback)
        min_trades: Mínimo de trades para começar a ajustar
        score: Score do sinal para ajuste de agressividade
        is_high_quality: Flag de sinal institucional (liq_cascade, exp_btc)
    
    Returns:
        Risco percentual (0.01 a 0.10)
    """
    # Cálculo base do Quarter-Kelly
    if len(closed_trades) < min_trades:
        kelly_base = base_risk_pct
    else:
        wins = [t.get("exit", {}).get("pnl_pct", 0) for t in closed_trades if (t.get("exit") or {}).get("pnl_pct", 0) > 0]
        losses = [abs(t.get("exit", {}).get("pnl_pct", 0)) for t in closed_trades if (t.get("exit") or {}).get("pnl_pct", 0) < 0]
        
        if not wins or not losses:
            kelly_base = base_risk_pct
        else:
            win_rate = len(wins) / len(closed_trades)
            avg_win = sum(wins) / len(wins)
            avg_loss = sum(losses) / len(losses)
            
            b = avg_win / avg_loss
            p = win_rate
            kelly = (b * p - (1 - p)) / b
            kelly_base = max(0.01, (kelly / 4.0))

    # SPRINT 12.146: Multiplicador Adaptativo por Qualidade (Análise Honesta)
    multiplier = 1.0
    if score >= 95 or is_high_quality:
        multiplier = 1.5  # 50% mais agressivo em sinais Elite
    elif score >= 90:
        multiplier = 1.2  # 20% mais agressivo em sinais Fortes

    # Risco final com cap de 10% (DNA Sniper: nunca apostar a banca toda)
    return max(0.01, min(0.10, kelly_base * multiplier))
