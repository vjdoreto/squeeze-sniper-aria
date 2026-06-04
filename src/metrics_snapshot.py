"""Snapshot de métricas por símbolo (contrato alinhado ao eassets, fase P0)."""
from typing import Any, Dict, Optional


def capture_metrics(symbol: str, data: Dict[str, Dict]) -> Dict[str, Any]:
    d = data.get(symbol) or {}

    # Nota: o paper/tracker usa chaves com sufixo (:5m, :1h etc). Também mantemos
    # aliases "sem sufixo" para compatibilidade com código/análises existentes.
    return {
        "symbol": symbol,
        "price": d.get("price"),
        "oi": d.get("oi"),
        "lsr": d.get("lsr"),

        # Aliases (sem sufixo) — para compatibilidade
        "exp": d.get("exp:5m"),
        "oi_trend": d.get("oi_trend:5m"),
        "lsr_trend": d.get("lsr_trend:5m"),

        # Chaves com sufixo — para o PaperTradeTracker
        "exp:5m": d.get("exp:5m"),
        "oi_trend:5m": d.get("oi_trend:5m"),
        "oi_trend:1m": d.get("oi_trend:1m"),
        "lsr_trend:5m": d.get("lsr_trend:5m"),
        "lsr_trend:1m": d.get("lsr_trend:1m"),
        "price_change:5m": d.get("price_change:5m"),
        "price_change:15m": d.get("price_change:15m"),
        "price_change:1h": d.get("price_change:1h"),

        # RSI (aliases para análises)
        "rsi_5m": d.get("rsi:5m"),
        "rsi_15m": d.get("rsi:15m"),
        "rsi_1h": d.get("rsi:1h"),
        "rsi:5m": d.get("rsi:5m"),
        "rsi:15m": d.get("rsi:15m"),
        "rsi:1h": d.get("rsi:1h"),

        # Sinais auxiliares
        "cvd_1m": d.get("volume_delta_1min"),
        "trades_1m": d.get("trades_count_1min"),
        "volume_delta": d.get("volume_delta"),

        # Extra (útil para SL/TP e qualidade)
        "liq_short_1m": d.get("liq_short_1m"),
        "oi_accel:5m": d.get("oi_accel:5m"),
        "cvd_change_pct:5m": d.get("cvd_change_pct:5m"),
        "oi_change_pct:5m": d.get("oi_change_pct:5m"),
        "lsr_change_pct:5m": d.get("lsr_change_pct:5m"),
        "step_size": d.get("step_size", "0.00000001"),
        "tick_size": d.get("tick_size", "0.00000001"),
    }
