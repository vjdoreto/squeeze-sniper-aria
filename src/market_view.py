"""Shared ranking/status logic for terminal and web dashboards."""
from typing import Any, Dict, List, Tuple


def squeeze_status(exp: float, oi_trend: float, lsr_trend: float) -> str:
    if exp > 0.5 and oi_trend > 0.1 and lsr_trend < -0.05:
        return "squeeze"
    if exp > 0 and oi_trend > 0:
        return "potential"
    return "watch"


def calculate_fit_score(d: Dict) -> int:
    """Calcula a nota de qualidade institucional (0-100) do alinhamento para Squeeze.
    Usa métricas de % de crescimento (delta percentual) ao invés de valores absolutos,
    para comparar ativos de tamanhos diferentes (BTC vs altcoin) de forma justa.
    """
    score = 0

    # 1. CVD % crescimento — Até 25 pts (SPRINT 6.5: Reequilíbrio para captura de ignição)
    cvd_chg = d.get("cvd_change_pct:5m")
    if cvd_chg is not None:
        if cvd_chg > 100:
            score += 25
        elif cvd_chg > 50:
            score += 20
        elif cvd_chg > 20:
            score += 15
        elif cvd_chg > 10:
            score += 10
        elif cvd_chg > 0:
            score += 5
        elif cvd_chg < -20:
            score -= 10

    # 2. OI % crescimento (5m) — Até 20 pts
    oi_chg = d.get("oi_change_pct:5m")
    if oi_chg is not None:
        if oi_chg > 1.5:
            score += 20
        elif oi_chg > 0.8:
            score += 15
        elif oi_chg > 0.2:
            score += 10
        elif oi_chg > 0:
            score += 5
        elif oi_chg < -0.5:
            score -= 8

    # 3. LSR % queda (5m) — Até 15 pts (pânico de shorts)
    lsr_chg = d.get("lsr_change_pct:5m")
    if lsr_chg is not None:
        if lsr_chg < -3:
            score += 15
        elif lsr_chg < -1:
            score += 10
        elif lsr_chg > 3:
            score -= 5  # LSR subindo = mais shorts = contra

    # 4. Força do Preço EXP (Momentum) — Até 15 pts (SPRINT 6.9: Boost Momentum)
    exp = d.get("exp:5m", 0) or 0
    if exp > 0.06:
        score += 15
    elif exp > 0.03:
        score += 10
    elif exp > 0.01:
        score += 5

    # 6. OI Aceleração (DNA Sniper) — Até 10 pts
    oi_accel = d.get("oi_accel:5m")
    if oi_accel is not None:
        if oi_accel > 0.05:
            score += 10
        elif oi_accel > 0.02:
            score += 6
        elif oi_accel > 0:
            score += 3
        elif oi_accel < -0.05:
            score -= 5

    # 5. Descolamento do BTC (Relative Strength) — Até 30 pts (Prioridade P0)
    exp_btc = d.get("exp_btc:5m")
    if exp_btc is not None:
        if exp_btc > 0.025:  # SPRINT 6.13: Mais sensível ao descolamento real (DNA eassets)
            score += 30
        elif exp_btc > 0.012:
            score += 20
        elif exp_btc > 0.005:
            score += 10
        elif exp_btc < -0.015:
            score -= 15
        elif exp_btc < -0.005:
            score -= 8

    # 5.2 Alinhamento de Médias (EMA Trend) — Até 10 pts
    ema_tr = d.get("ema_trend:5m")
    if ema_tr is not None:
        if ema_tr >= 5: score += 10
        elif ema_tr >= 3: score += 5
        elif ema_tr <= -5: score -= 15 # Anti-faca caindo

    # 5.2.1 EMA Trend 1h — Bônus +5 pts (R-ARIA-03 · 10/06/2026)
    # Discrimina pullback em tendência maior (4h/1h fortes, 5m fraco) de bear pleno
    ema_tr_1h = d.get("ema_trend:1h")
    if ema_tr_1h is not None and ema_tr_1h >= 2:
        score += 5

    # 5.3 Acumulação (Range Level) — Até 10 pts
    rng = d.get("range_level:5m")
    if rng is not None:
        if rng >= 4: score += 10
        elif rng >= 2: score += 5

    # 5.1 RSI como Combustível (DNA) — Até 10 pts
    rsi = d.get("rsi:5m")
    if rsi is not None:
        if rsi > 65:
            score += 10
        elif rsi > 55:
            score += 5
        elif rsi < 45:
            score -= 10

    # 7. Liquidações de short — Até 15 pts extras (SPRINT 6.9: Usa versão estável)
    # fix(T-1): thresholds calibrados para small/mid caps — era $10k/$50k/$100k (large cap only)
    liq_short = d.get("liq_short_1m_stable", 0) or 0
    if liq_short > 20000:   # $20k em shorts liquidados em 1m
        score += 15
    elif liq_short > 5000:  # $5k
        score += 10
    elif liq_short > 1000:  # $1k
        score += 5

    # 7.1. Bônus de Cascata (DNA Squeeze) — +20 pts
    if d.get("liq_cascade"):
        score += 20

    # 8. HFT Burst — Até 10 pts (SPRINT 6.9: Usa versão estável)
    trades_10s = d.get("last_trades_10s", 0) or 0
    trades_1m = d.get("trades_count_1min_stable", 0) or 0
    avg_trades_10s = trades_1m / 6.0
    if trades_10s > 30 and trades_10s > (avg_trades_10s * 2.0):
        score += 10
    elif trades_10s > 15 and trades_10s > (avg_trades_10s * 1.3):
        score += 5

    # 9. Order Book Imbalance — Até 10 pts (Sprint 3D)
    ob_imb = d.get("ob_imbalance", 1.0) or 1.0
    if ob_imb > 2.0:
        score += 10
    elif ob_imb > 1.5:
        score += 5
    elif ob_imb < 0.5:
        score -= 5  # Pressão vendedora imediata segurando o preço

    # SPRINT 7.3: Penalidade por entrada tardia (preço já moveu muito)
    pc_5m_val = d.get("price_change:5m") or 0
    if pc_5m_val > 2.0:
        score -= 20  # Preço já subiu 2%+ em 5m = catching the tail
    elif pc_5m_val > 1.5:
        score -= 10  # Preço subiu 1.5%+ = movimento avançado

    # Bônus por entrada precoce (exp moderado mas OI forte = ignição começando)
    if (d.get("exp:5m") or 0) < 0.03 and (d.get("oi_change_pct:5m") or 0) > 0.5:
        score += 5  # OI subindo mas preço ainda não moveu = IDEAL DNA

    # SPRINT 7.5: Funding Rate bônus/penalidade (DNA Sniper)
    fr = d.get("funding_rate", 0) or 0
    if fr < -0.0001:
        score += 5   # Funding negativo = shorts pagando longs = combustível extra
    elif fr > 0.0003:
        score -= 10  # Funding muito positivo = longs pagando shorts = risco de dump

    return max(0, min(100, score))


def build_rows(
    market_data: Dict[str, Dict],
    min_exp: float = 0.5,
    min_oi_trend: float = 0.1,
    max_lsr_trend: float = -0.05,
    limit: int = 100,
    sort_by: str = "score",
) -> List[Dict[str, Any]]:
    ranked: List[Tuple[float, float, float, str, Dict[str, Any]]] = []
    for symbol, d in market_data.items():
        # Removemos o filtro de preço zero para que o Top 50 apareça
        # imediatamente após o boot, mesmo durante o aquecimento (warmup).

        # SPRINT 6.27: Reaproveita o score já calculado no BotState para performance
        score = d.get("score")
        if score is None:
            score = calculate_fit_score(d)
            
        cvd_chg = d.get("cvd_change_pct:5m")
        if cvd_chg is None:
            cvd_chg = -999.0
        oi_trend = d.get("oi_trend:5m")
        if oi_trend is None:
            oi_trend = -999.0
        # Ordenação: primeiro score (decrescente), depois CVD % chg (decrescente)
        ranked.append((score, cvd_chg, oi_trend, symbol, d))

    # Ordenação flexível (Sprint 4)
    if sort_by == "cvd":
        ranked.sort(
            key=lambda x: (x[1], x[0], float(x[2]) if x[2] != -999.0 else -1e9),
            reverse=True,
        )
    elif sort_by == "oi":
        ranked.sort(
            key=lambda x: (float(x[2]) if x[2] != -999.0 else -1e9, x[0], x[1]),
            reverse=True,
        )
    else:
        # Default: Score Institucional
        ranked.sort(
            key=lambda x: (x[0], x[1], float(x[2]) if x[2] != -999.0 else -1e9),
            reverse=True,
        )

    rows: List[Dict[str, Any]] = []

    for score, cvd_chg_val, oi_trend, symbol, d in ranked[:limit]:
        exp = d.get("exp:5m")  # pode ser None
        lsr_trend = d.get("lsr_trend:5m")  # pode ser None
        warming = oi_trend == -999.0
        display_oi_trend = None if warming else oi_trend

        # Fallback apenas para cálculo do status (não para exibição)
        exp_num = float(exp) if exp is not None else 0.0
        lsr_trend_num = float(lsr_trend) if lsr_trend is not None else 0.0
        oi_trend_num = float(display_oi_trend) if display_oi_trend is not None else 0.0

        price = d.get("price") or 0
        oi_coin = d.get("oi", 0) or 0
        oi_notional = None if price <= 0 else (oi_coin * price)
        # OI em milhões com 2 casas
        oi_m = oi_notional / 1e6 if oi_notional is not None else None

        rows.append(
            {
                "symbol": symbol,
                "price": d["price"],
                "pc_24h": d.get("price_change_24h", 0.0), # SPRINT 6.28
                "vol_24h_m": (d.get("volume_24h", 0) or 0) / 1e6,
                "oi": d.get("oi", 0),

                # === Contrato do web_dashboard.py (escalares planos, sem dict aninhado) ===
                "exp": exp,  # float | None (5m)
                "exp_btc": d.get("exp_btc:5m"),  # float | None
                "oi_trend": display_oi_trend,  # float | None (5m)
                "lsr_trend": lsr_trend,  # float | None (5m)

                "rsi_5m": d.get("rsi:5m"),
                "rsi_15m": d.get("rsi:15m"),
                "rsi_1h": d.get("rsi:1h"),

                "ema_trend": d.get("ema_trend:5m"),
                "range_level": d.get("range_level:5m"),

                # === Métricas e histórico (flat) ===
                # SPRINT 6.46: Coação para lista nova (thread-safe serialization)
                "cvd_hist": list(d.get("cvd_hist") or []),
                "oi_hist": list(d.get("oi_hist") or []),
                "oi_accel": d.get("oi_accel:5m"),
                "oi_notional": oi_notional,  # OI em USDT notional (OI*preço)
                "oi_notional_m": oi_m,  # OI em milhões
                "cvd_1m": d.get("volume_delta_1min_stable", 0),
                "liq_short_1m": d.get("liq_short_1m_stable", 0),
                "ob_imbalance": d.get("ob_imbalance", 1.0),
                "funding_rate": d.get("funding_rate", 0),
                "trades_10s": d.get("last_trades_10s", 0),
                "trades_1m": d.get("trades_count_1min_stable", 0),
                "trades_level": d.get("trades_level", 0),  # 0-4 spike vs baseline histórica
                "trades_minute_5m": d.get("trades_minute:5m", 0.0),  # trades/min nos últimos 5m (derivado)
                "cvd_change_pct": d.get("cvd_change_pct:5m") or 0.0,  # % crescimento CVD 5m
                "oi_change_pct": d.get("oi_change_pct:5m") or 0.0,  # % crescimento OI 5m
                "lsr_change_pct": d.get("lsr_change_pct:5m") or 0.0,  # % mudança LSR 5m
                "volume_1h": d.get("volume_1h", 0.0),
                "bid_ask_spread": d.get("bid_ask_spread", 0.0),
                "trades_second": d.get("trades_second", 0.0),
                "pc_5m": d.get("price_change:5m"),
                "pc_15m": d.get("price_change:15m"),
                "pc_1h": d.get("price_change:1h"),

                "lsr": d.get("lsr"),  # não force 0 quando for None (evita 0.00 fantasma)
                "lsr_is_proxy": d.get("lsr_is_proxy", False),
                
                # Timeframes extras
                "exp_1m": d.get("exp:1m"),
                "exp_1h": d.get("exp:1h"),
                "oi_trend_1m": d.get("oi_trend:1m"),
                "oi_trend_1h": d.get("oi_trend:1h"),
                "lsr_trend_1m": d.get("lsr_trend:1m"),
                "lsr_trend_1h": d.get("lsr_trend:1h"),
                "ema_trend_15m": d.get("ema_trend:15m"),
                "ema_trend_1h": d.get("ema_trend:1h"),
                "range_level_15m": d.get("range_level:15m"),
                "range_level_1h": d.get("range_level:1h"),
                "liq_cascade": d.get("liq_cascade", False),

                "score": score,
                "status": "warming"
                if warming
                else squeeze_status(exp_num, oi_trend_num, lsr_trend_num),
            }
        )
    return rows
