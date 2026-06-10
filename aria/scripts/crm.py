"""
crm.py — Crypto Risk Meter (CRM)
Doreto Squeeze Sniper — Indicadores Proprietários v1.0

Indicador proprietário Doreto.
Mede o nível de risco do ambiente cripto em tempo real.
Score 0–100 calculado a partir dos fluxos de capital e
sentimento do mercado de futuros.

Quanto mais alto o score, mais adverso o ambiente para entradas long.

ATENÇÃO — Lógica do FGI invertida intencionalmente:
    O operador opera CONTRA a manada. Medo extremo (FGI < 20)
    significa mercado desalavancado = oportunidade, não risco.
    Ganância extrema (FGI > 80) = mercado alavancado = risco real.

Componentes e pesos:
    USDT.D          35% — fuga para stable = medo
    Fear & Greed    25% — sentimento invertido
    BTC 24h         20% — tendência macro cripto
    Funding Rate    12% — viés do mercado de futuros
    ETH.D            8% — saúde das altcoins

Integração com o SS:
    - usdt_dominance  → buscar via CoinGecko ou CMC (chave disponível)
    - fear_greed      → buscar via api.alternative.me/fng
    - btc_change_24h  → já disponível no MetricStore (price_change:1D do BTCUSDT)
    - funding_rate    → já disponível no MetricStore (fr por símbolo)
    - eth_dominance   → buscar via CoinGecko junto com USDT.D
"""

import logging
from typing import Optional
from .models import CRMInput, CRMOutput, RiskLevel

logger = logging.getLogger(__name__)

# ─── Pesos dos componentes ────────────────────────────────────────────────────

WEIGHTS = {
    "usdt_dominance":   0.35,
    "fear_greed":       0.25,
    "btc_change_24h":   0.20,
    "funding_rate":     0.12,
    "eth_dominance":    0.08,
}

# ─── Funções de scoring por componente ───────────────────────────────────────

def _score_usdt_dominance(val: float) -> float:
    """
    USDT.D alto = capital fugindo para stable = risco cripto alto.
    Escala: < 5% neutro/bom → > 9% crítico
    Retorna contribuição ao score de risco (0–100).
    """
    if val < 4.5:  return 0.0
    if val < 5.0:  return 10.0
    if val < 6.0:  return 20.0
    if val < 7.0:  return 40.0
    if val < 8.0:  return 60.0
    if val < 9.0:  return 78.0
    return 95.0


def _score_fear_greed(val: int) -> float:
    """
    LÓGICA INVERTIDA — operador opera contra a manada.
    Medo extremo (FGI baixo) = oportunidade = score de risco BAIXO.
    Ganância extrema (FGI alto) = mercado alavancado = score de risco ALTO.

    Escala:
        0–20  Medo Extremo   → score 10  (oportunidade)
        21–40 Medo           → score 25  (zona positiva)
        41–60 Neutro         → score 50  (neutro)
        61–80 Ganância       → score 70  (atenção)
        81–100 Ganância Ext. → score 90  (risco real)
    """
    if val <= 20:  return 10.0
    if val <= 40:  return 25.0
    if val <= 60:  return 50.0
    if val <= 80:  return 70.0
    return 90.0


def _score_btc_change(pct: float) -> float:
    """
    BTC caindo = ambiente cripto adverso = risco alto.
    Retorna contribuição ao score de risco.
    """
    if pct > 3.0:   return 0.0
    if pct > 1.0:   return 10.0
    if pct > 0.0:   return 20.0
    if pct > -1.0:  return 35.0
    if pct > -2.0:  return 50.0
    if pct > -4.0:  return 68.0
    if pct > -6.0:  return 82.0
    return 95.0


def _score_funding_rate(rate: float) -> float:
    """
    Funding negativo = bears dominando = risco de queda.
    Funding muito positivo = longs excessivos = risco de flush.
    Zona ideal: funding levemente positivo (0.01%–0.03%).

    rate em decimal, ex: 0.0003 = 0.03%
    """
    pct = rate * 100  # converter para %
    if -0.01 < pct < 0.03:   return 20.0   # zona saudável
    if 0.03 <= pct < 0.06:   return 40.0   # longs acumulando
    if pct >= 0.06:           return 70.0   # longs excessivos
    if -0.03 < pct <= -0.01: return 55.0   # bears leves
    return 80.0                             # bears dominando / funding muito negativo


def _score_eth_dominance(val: float) -> float:
    """
    ETH.D baixo = alts sem sustentação = ambiente fraco.
    ETH.D muito alto = capital concentrado = alts sofrendo.
    Zona saudável: 12%–18%.
    """
    if 12.0 <= val <= 18.0: return 20.0
    if val < 10.0:          return 65.0   # ETH fraco = alts sem base
    if val < 12.0:          return 45.0
    if val < 22.0:          return 35.0
    return 55.0                           # ETH dominando demais = rotação saindo das alts


# ─── Classificação por score ──────────────────────────────────────────────────

def _classify(score: float) -> RiskLevel:
    if score <= 30: return RiskLevel.LOW
    if score <= 55: return RiskLevel.MODERATE
    if score <= 75: return RiskLevel.HIGH
    return RiskLevel.CRITICAL


# ─── Calculadora principal ────────────────────────────────────────────────────

def calculate_crm(data: CRMInput) -> CRMOutput:
    """
    Calcula o CRM (Crypto Risk Meter) a partir dos dados fornecidos.

    Campos ausentes (None) são ignorados — o score é normalizado
    pelo peso total disponível, garantindo resultado válido mesmo
    com dados parciais.

    Args:
        data: CRMInput com os valores dos componentes.

    Returns:
        CRMOutput com score 0–100, nível de risco e detalhes.

    Exemplo de uso no SS:
        from indicators.crm import calculate_crm
        from indicators.models import CRMInput

        crm_input = CRMInput(
            usdt_dominance=8.7,
            fear_greed_index=12,
            btc_change_24h=-4.27,
            funding_rate_avg=0.00005,
            eth_dominance=8.8,
        )
        result = calculate_crm(crm_input)
        logger.info(f"CRM: {result.score:.1f} [{result.level.value}] — {result.summary}")
    """
    components = {}
    missing    = []
    weighted_sum   = 0.0
    available_weight = 0.0

    # ── USDT Dominance ────────────────────────────────────────────
    if data.usdt_dominance is not None:
        s = _score_usdt_dominance(data.usdt_dominance)
        components["usdt_dominance"] = {
            "value": data.usdt_dominance,
            "score": s,
            "weight": WEIGHTS["usdt_dominance"],
            "label": f"USDT.D {data.usdt_dominance:.1f}%",
        }
        weighted_sum     += s * WEIGHTS["usdt_dominance"]
        available_weight += WEIGHTS["usdt_dominance"]
    else:
        missing.append("usdt_dominance")

    # ── Fear & Greed ──────────────────────────────────────────────
    if data.fear_greed_index is not None:
        s = _score_fear_greed(data.fear_greed_index)
        fgi_label = _fgi_label(data.fear_greed_index)
        components["fear_greed"] = {
            "value": data.fear_greed_index,
            "score": s,
            "weight": WEIGHTS["fear_greed"],
            "label": f"FGI {data.fear_greed_index} — {fgi_label}",
            "note": "lógica invertida: medo = oportunidade",
        }
        weighted_sum     += s * WEIGHTS["fear_greed"]
        available_weight += WEIGHTS["fear_greed"]
    else:
        missing.append("fear_greed_index")

    # ── BTC 24h ───────────────────────────────────────────────────
    if data.btc_change_24h is not None:
        s = _score_btc_change(data.btc_change_24h)
        components["btc_change_24h"] = {
            "value": data.btc_change_24h,
            "score": s,
            "weight": WEIGHTS["btc_change_24h"],
            "label": f"BTC 24h {data.btc_change_24h:+.2f}%",
        }
        weighted_sum     += s * WEIGHTS["btc_change_24h"]
        available_weight += WEIGHTS["btc_change_24h"]
    else:
        missing.append("btc_change_24h")

    # ── Funding Rate ──────────────────────────────────────────────
    if data.funding_rate_avg is not None:
        s = _score_funding_rate(data.funding_rate_avg)
        components["funding_rate"] = {
            "value": data.funding_rate_avg,
            "score": s,
            "weight": WEIGHTS["funding_rate"],
            "label": f"Funding {data.funding_rate_avg * 100:.4f}%",
        }
        weighted_sum     += s * WEIGHTS["funding_rate"]
        available_weight += WEIGHTS["funding_rate"]
    else:
        missing.append("funding_rate_avg")

    # ── ETH Dominance ─────────────────────────────────────────────
    if data.eth_dominance is not None:
        s = _score_eth_dominance(data.eth_dominance)
        components["eth_dominance"] = {
            "value": data.eth_dominance,
            "score": s,
            "weight": WEIGHTS["eth_dominance"],
            "label": f"ETH.D {data.eth_dominance:.1f}%",
        }
        weighted_sum     += s * WEIGHTS["eth_dominance"]
        available_weight += WEIGHTS["eth_dominance"]
    else:
        missing.append("eth_dominance")

    # ── Score final normalizado ───────────────────────────────────
    if available_weight == 0:
        score = 50.0  # sem dados = score neutro
        logger.warning("CRM: nenhum dado disponível, retornando score neutro 50")
    else:
        score = weighted_sum / available_weight

    score = max(0.0, min(100.0, score))
    level = _classify(score)

    # ── Summary ───────────────────────────────────────────────────
    missing_str = f" [faltando: {', '.join(missing)}]" if missing else ""
    summary = (
        f"CRM {score:.1f}/100 [{level.value}]{missing_str} — "
        + _build_summary(components, score)
    )

    logger.debug(f"CRM calculado: score={score:.1f} level={level.value} "
                 f"disponível={available_weight:.2f} missing={missing}")

    return CRMOutput(
        score=round(score, 1),
        level=level,
        components=components,
        missing=missing,
        summary=summary,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fgi_label(val: int) -> str:
    if val <= 20: return "Medo Extremo"
    if val <= 40: return "Medo"
    if val <= 60: return "Neutro"
    if val <= 80: return "Ganância"
    return "Ganância Extrema"


def _build_summary(components: dict, score: float) -> str:
    drivers = []
    for k, v in components.items():
        if v["score"] >= 70:
            drivers.append(f"{v['label']} ↑risco")
        elif v["score"] <= 20:
            drivers.append(f"{v['label']} ↓risco")
    if drivers:
        return "Drivers: " + " | ".join(drivers[:3])
    if score > 55:
        return "ambiente cripto adverso"
    if score < 30:
        return "ambiente cripto favorável"
    return "ambiente neutro"


# ─── Fetcher opcional ─────────────────────────────────────────────────────────

async def fetch_crm_data(
    btc_change_24h: Optional[float] = None,
    funding_rate_avg: Optional[float] = None,
) -> CRMInput:
    """
    Busca automaticamente os dados externos necessários para o CRM.
    btc_change_24h e funding_rate_avg podem ser passados diretamente
    do MetricStore do SS para evitar requisições redundantes.

    Fontes:
        USDT.D / ETH.D → CoinGecko /api/v3/global
        Fear & Greed   → api.alternative.me/fng/?limit=1

    Uso no SS:
        btc_chg = metric_store.get("BTCUSDT", "price_change:1D") or 0
        fr_avg  = mean([metric_store.get(s, "fr") for s in active_symbols])
        crm_data = await fetch_crm_data(btc_change_24h=btc_chg, funding_rate_avg=fr_avg)
        result = calculate_crm(crm_data)
    """
    import aiohttp

    usdt_d = eth_d = fgi = None

    async with aiohttp.ClientSession() as session:
        # CoinGecko — dominâncias
        try:
            async with session.get(
                "https://api.coingecko.com/api/v3/global",
                timeout=aiohttp.ClientTimeout(total=8),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    pct = d["data"]["market_cap_percentage"]
                    usdt_d = pct.get("usdt", None)
                    eth_d  = pct.get("eth", None)
        except Exception as e:
            logger.warning(f"CRM fetch CoinGecko falhou: {e}")

        # Alternative.me — Fear & Greed
        try:
            async with session.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=aiohttp.ClientTimeout(total=8),
            ) as r:
                if r.status == 200:
                    d = await r.json()
                    fgi = int(d["data"][0]["value"])
        except Exception as e:
            logger.warning(f"CRM fetch FGI falhou: {e}")

    return CRMInput(
        usdt_dominance=usdt_d,
        fear_greed_index=fgi,
        btc_change_24h=btc_change_24h,
        funding_rate_avg=funding_rate_avg,
        eth_dominance=eth_d,
    )
