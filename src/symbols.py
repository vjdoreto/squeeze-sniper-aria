"""Filtro de símbolos Binance USD-M — alinhado ao universo do painel eassets (~527)."""
from typing import Dict, List, Tuple


def list_usdt_perpetual_symbols(exchange_info: Dict) -> Tuple[List[str], Dict[str, int]]:
    """
    Retorna símbolos PERPETUAL USDT com status TRADING.
    Ignora contratos com entrega (quarterly) que inflam a contagem (~582 → ~527).
    """
    stats = {
        "total": 0,
        "usdt": 0,
        "trading": 0,
        "perpetual": 0,
    }
    out: List[str] = []
    for s in exchange_info.get("symbols", []):
        stats["total"] += 1
        if s.get("quoteAsset") != "USDT":
            continue
        stats["usdt"] += 1
        if s.get("status") != "TRADING":
            continue
        stats["trading"] += 1
        if s.get("contractType") != "PERPETUAL":
            continue
        stats["perpetual"] += 1
        out.append(s["symbol"])
    return sorted(out), stats
