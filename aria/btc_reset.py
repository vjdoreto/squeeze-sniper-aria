"""
btc_reset.py — BTC Reset Monitor
Doreto Squeeze Sniper — Indicadores Proprietários v1.0

Indicador proprietário Doreto. Conceito pouco explorado no mercado.

Mede o nível de desalavancagem do BTC em múltiplos timeframes
simultaneamente. O mercado cripto, por ser altamente alavancado,
precisa de um processo de "limpeza" antes de novos movimentos
sustentados.

Teoria da Tempestade e Bonança:
    FASE 1 — TEMPESTADE
        BTC RSI despenca para < threshold em múltiplos TFs
        Liquidações em massa confirmam a intensidade
        Alavancagem sendo destruída — manada vende com medo

    FASE 2 — RESET CONFIRMADO
        RSI < threshold em N timeframes simultaneamente
        Mercado desalavancado = slate limpo

    FASE 3 — BONANÇA
        Ativos com EXP_BTC positivo durante a queda lideram
        Reversão mais rápida e mais potente

Pesos por TF (TFs longos valem mais):
    5m  →  8   15m → 12   30m → 15
    1h  → 20    4h → 25   12h → 30   1D → 35

Multiplicador de liquidações:
    < 50% threshold  → 0.70 (sem confirmação)
    50–100%          → 0.85 (parcial)
    100–200%         → 1.00 (confirmado)
    200–500%         → 1.15 (forte)
    > 500%           → 1.30 (histórico)

Detecção de padrão V (Reset Relâmpago):
    RSI tocou < threshold E voltou acima de 50 nos últimos N candles.
    Bônus de +15 no score. Estado "V RELÂMPAGO" se V em 2+ TFs.

Integração com o SS:
    OPÇÃO A (preferida) — RSIs do MetricStore:
        rsi_by_tf = {
            '5m':  metric_store.get('BTCUSDT', 'rsi:5m'),
            '15m': metric_store.get('BTCUSDT', 'rsi:15m'),
            '1h':  metric_store.get('BTCUSDT', 'rsi:1h'),
            '4h':  metric_store.get('BTCUSDT', 'rsi:4h'),
        }

    OPÇÃO B — Closes brutos (RSI calculado internamente):
        closes_by_tf = {
            '5m':  kline_cache['BTCUSDT']['5m'],   # lista de closes
            '1h':  kline_cache['BTCUSDT']['1h'],
        }

    liq_usd_1h → somar liq_short_1m dos últimos 60 ciclos do MetricStore
"""

import logging
import math
from typing import Optional
from .models import BTCResetInput, BTCResetOutput, TFResetStatus, ResetState

logger = logging.getLogger(__name__)

# ─── Configuração dos timeframes ──────────────────────────────────────────────

TF_CONFIG = [
    {"id": "5m",  "weight": 8,  "min_candles_reset": 2, "v_lookback": 5},
    {"id": "15m", "weight": 12, "min_candles_reset": 2, "v_lookback": 5},
    {"id": "30m", "weight": 15, "min_candles_reset": 1, "v_lookback": 4},
    {"id": "1h",  "weight": 20, "min_candles_reset": 1, "v_lookback": 3},
    {"id": "4h",  "weight": 25, "min_candles_reset": 1, "v_lookback": 3},
    {"id": "12h", "weight": 30, "min_candles_reset": 1, "v_lookback": 2},
    {"id": "1d",  "weight": 35, "min_candles_reset": 1, "v_lookback": 2},
]

TOTAL_WEIGHT = sum(tf["weight"] for tf in TF_CONFIG)  # 145


# ─── RSI Calculator ───────────────────────────────────────────────────────────

def calculate_rsi(closes: list, period: int = 14) -> float:
    """
    Calcula RSI Wilder a partir de uma lista de closes.
    Requer pelo menos period + 1 valores.
    Retorna 50.0 se dados insuficientes.
    """
    if len(closes) < period + 1:
        return 50.0

    gains  = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    # Wilder smoothing — usar apenas os últimos N períodos
    relevant_gains  = gains[-period:]
    relevant_losses = losses[-period:]

    avg_gain = sum(relevant_gains) / period
    avg_loss = sum(relevant_losses) / period

    if avg_loss == 0:
        return 100.0

    rs  = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def calculate_rsi_history(closes: list, period: int = 14, lookback: int = 5) -> list:
    """
    Retorna os últimos `lookback` valores de RSI para detecção de padrão V.
    """
    if len(closes) < period + lookback + 1:
        return [calculate_rsi(closes, period)]

    result = []
    for i in range(lookback, 0, -1):
        subset = closes[:-i] if i > 0 else closes
        result.append(calculate_rsi(subset, period))
    result.append(calculate_rsi(closes, period))
    return result


# ─── Detecção de padrão V ────────────────────────────────────────────────────

def detect_v_pattern(
    rsi_history: list,
    threshold: float,
    recovery_level: float = 50.0,
) -> bool:
    """
    Detecta padrão V: RSI tocou abaixo do threshold E
    já recuperou acima de recovery_level no histórico recente.

    Diferença entre V espúrio e V real:
        V no 5m por 1-2 candles = spike, não reset
        V no 1h+ = reset real e rápido

    Args:
        rsi_history: lista com valores RSI recentes [mais_antigo, ..., atual]
        threshold:   nível de reset (ex: 30.0)
        recovery_level: nível de recuperação (ex: 50.0)

    Returns:
        True se padrão V detectado
    """
    if len(rsi_history) < 2:
        return False

    # RSI atual acima do recovery_level
    current_rsi = rsi_history[-1]
    if current_rsi < recovery_level:
        return False

    # Algum ponto anterior tocou abaixo do threshold
    historical = rsi_history[:-1]
    return any(r < threshold for r in historical)


# ─── Multiplicador de liquidações ────────────────────────────────────────────

def _liq_multiplier(liq_usd: float, threshold: float) -> float:
    """
    Retorna o multiplicador baseado na intensidade das liquidações
    em relação ao threshold configurado.
    """
    if threshold <= 0:
        return 1.0

    ratio = liq_usd / threshold
    if ratio < 0.5:   return 0.70
    if ratio < 1.0:   return 0.85
    if ratio < 2.0:   return 1.00
    if ratio < 5.0:   return 1.15
    return 1.30


# ─── Calculadora principal ────────────────────────────────────────────────────

def calculate_btc_reset(data: BTCResetInput) -> BTCResetOutput:
    """
    Calcula o BTC Reset Monitor.

    Aceita RSIs prontos (rsi_by_tf) OU closes brutos (closes_by_tf).
    Se ambos fornecidos, rsi_by_tf tem prioridade.

    Args:
        data: BTCResetInput com RSIs ou closes por TF.

    Returns:
        BTCResetOutput com score, estado e status por TF.

    Exemplo de uso no SS (com MetricStore):
        from indicators.btc_reset import calculate_btc_reset
        from indicators.models import BTCResetInput

        rsi_tf = {}
        for tf in ['5m', '15m', '1h', '4h']:
            val = metric_store.get('BTCUSDT', f'rsi:{tf}')
            if val is not None:
                rsi_tf[tf] = val

        liq_1h = sum(
            metric_store.get('BTCUSDT', 'liq_short_1m') or 0
            for _ in range(60)   # aproximação — somar janela de 1h
        )

        result = calculate_btc_reset(BTCResetInput(
            rsi_by_tf=rsi_tf,
            liq_usd_1h=liq_1h,
            liq_threshold=preferences.get('reset_liq_threshold', 10_000_000),
            rsi_threshold=preferences.get('reset_rsi_threshold', 30.0),
        ))

        if result.state in (ResetState.STRONG, ResetState.EXTREME):
            logger.warning(f"BTC RESET DETECTADO: {result.summary}")
    """
    tf_statuses  = []
    reset_weight = 0.0
    total_weight = 0.0
    reset_count  = 0
    v_detected   = False
    v_tfs        = []

    for tf_cfg in TF_CONFIG:
        tf_id   = tf_cfg["id"]
        weight  = tf_cfg["weight"]
        lookback = tf_cfg["v_lookback"]

        # ── Obter RSI atual ───────────────────────────────────────
        rsi_current: Optional[float] = None
        rsi_history: list = []

        if tf_id in data.rsi_by_tf and data.rsi_by_tf[tf_id] is not None:
            # Opção A: RSI pronto do MetricStore
            rsi_current = float(data.rsi_by_tf[tf_id])

            # Histórico para detecção V
            if tf_id in data.rsi_history_by_tf:
                rsi_history = list(data.rsi_history_by_tf[tf_id])
            else:
                rsi_history = [rsi_current]  # sem histórico = sem V

        elif tf_id in data.closes_by_tf and data.closes_by_tf[tf_id]:
            # Opção B: calcular RSI dos closes
            closes = list(data.closes_by_tf[tf_id])
            rsi_current = calculate_rsi(closes)
            rsi_history = calculate_rsi_history(closes, lookback=lookback)

        else:
            # TF não disponível — pular
            logger.debug(f"BTC Reset: TF {tf_id} não disponível, pulando")
            continue

        total_weight += weight

        # ── Estado do TF ──────────────────────────────────────────
        is_reset = rsi_current < data.rsi_threshold
        is_watch = (not is_reset) and (rsi_current < data.rsi_threshold + 10)

        # Detecção de padrão V
        is_v = detect_v_pattern(rsi_history, data.rsi_threshold)

        # Contribuição ao score
        if is_v:
            reset_weight += weight * 0.7   # V conta parcialmente
            v_detected = True
            v_tfs.append(tf_id)
        elif is_reset:
            reset_weight += weight
            reset_count  += 1

        tf_statuses.append(TFResetStatus(
            tf=tf_id,
            rsi=rsi_current,
            is_reset=is_reset,
            is_watch=is_watch,
            is_v=is_v,
            weight=weight,
        ))

    # ── Score base ────────────────────────────────────────────────
    if total_weight == 0:
        raw_score = 0.0
    else:
        raw_score = (reset_weight / total_weight) * 100.0

    # ── Bônus V Relâmpago ─────────────────────────────────────────
    if v_detected:
        raw_score = min(100.0, raw_score + 15.0)

    # ── Multiplicador de liquidações ──────────────────────────────
    liq_mult = _liq_multiplier(data.liq_usd_1h, data.liq_threshold)
    final_score = max(0.0, min(100.0, raw_score * liq_mult))

    # ── Estado global ─────────────────────────────────────────────
    state = _classify_state(final_score, v_detected, reset_count, v_tfs)

    # ── Summary ───────────────────────────────────────────────────
    reset_tfs_str = [s.tf for s in tf_statuses if s.is_reset]
    liq_m = data.liq_usd_1h / 1_000_000
    summary = (
        f"BTC RESET {final_score:.1f}/100 [{state.value}] — "
        f"{reset_count} TFs resetados {reset_tfs_str} "
        f"liq=${liq_m:.1f}M mult={liq_mult:.2f}"
    )
    if v_tfs:
        summary += f" | V detectado em: {v_tfs}"

    logger.debug(f"BTCReset: score={final_score:.1f} state={state.value} "
                 f"reset_count={reset_count} v_tfs={v_tfs} liq_mult={liq_mult:.2f}")

    return BTCResetOutput(
        score=round(final_score, 1),
        state=state,
        tf_statuses=tf_statuses,
        reset_count=reset_count,
        v_detected=v_detected,
        v_tfs=v_tfs,
        liq_multiplier=liq_mult,
        liq_usd_1h=data.liq_usd_1h,
        summary=summary,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _classify_state(
    score: float,
    v_detected: bool,
    reset_count: int,
    v_tfs: list,
) -> ResetState:
    """
    Classifica o estado global do RESET.
    V Relâmpago tem prioridade se V em 2+ TFs.
    """
    if v_detected and (reset_count >= 2 or len(v_tfs) >= 2):
        return ResetState.V_LIGHTNING
    if score >= 75:
        return ResetState.EXTREME
    if score >= 50:
        return ResetState.STRONG
    if score >= 25:
        return ResetState.PARTIAL
    return ResetState.NEUTRAL


def get_post_reset_candidates(
    reset_output: BTCResetOutput,
    symbol_data: dict,
    exp_btc_threshold: float = -5.0,
    min_oi_trend: float = 0.0,
) -> list:
    """
    Após RESET FORTE ou EXTREMO, identifica os candidatos
    que resistiram melhor à queda e lideram a bonança.

    Filtros:
        exp_btc:1h > exp_btc_threshold   (resistiu vs BTC)
        oi_trend:5m > min_oi_trend        (OI voltando)
        lsr_trend:5m < 0                  (shorts fechando)

    Args:
        reset_output:      resultado do calculate_btc_reset()
        symbol_data:       dict {symbol: metrics} do MetricStore
        exp_btc_threshold: mínimo EXP_BTC para considerar resistente
        min_oi_trend:      mínimo OI trend para considerar ativo

    Returns:
        Lista de símbolos ordenados por força relativa.

    Exemplo:
        if result.state in (ResetState.STRONG, ResetState.EXTREME):
            candidates = get_post_reset_candidates(result, metric_store.snapshot())
            logger.info(f"Candidatos pós-reset: {candidates[:5]}")
    """
    if reset_output.state not in (
        ResetState.STRONG, ResetState.EXTREME, ResetState.V_LIGHTNING
    ):
        return []

    candidates = []
    for symbol, metrics in symbol_data.items():
        exp_btc = metrics.get("exp_btc:1h") or metrics.get("exp_btc:5m") or -999
        oi_trend = metrics.get("oi_trend:5m") or 0.0
        lsr_trend = metrics.get("lsr_trend:5m") or 0.0

        if exp_btc < exp_btc_threshold:
            continue
        if oi_trend < min_oi_trend:
            continue
        if lsr_trend >= 0:
            continue  # LSR deve estar caindo

        # Score de força relativa pós-reset
        strength = (
            exp_btc * 1.5 +        # quanto mais forte vs BTC, melhor
            oi_trend * 10.0 +      # OI voltando positivo
            abs(lsr_trend) * 5.0   # shorts fechando agressivamente
        )
        candidates.append((symbol, round(strength, 2), exp_btc, oi_trend, lsr_trend))

    candidates.sort(key=lambda x: -x[1])
    return [
        {
            "symbol": c[0],
            "strength_score": c[1],
            "exp_btc_1h": c[2],
            "oi_trend_5m": c[3],
            "lsr_trend_5m": c[4],
        }
        for c in candidates
    ]
