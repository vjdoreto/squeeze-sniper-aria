"""
grm.py — Global Risk Meter (GRM)
Doreto Squeeze Sniper — Indicadores Proprietários v1.0

Indicador proprietário Doreto.
Mede o apetite de risco dos mercados financeiros globais.
Quando o GRM sobe, o capital migra para ativos seguros —
afetando indiretamente o cripto.

A correlação entre macro global e volatilidade cripto tem
crescido consistentemente desde 2022.

Componentes e pesos:
    VIX             35% — índice do medo S&P500 (mais importante)
    DXY             25% — força do dólar vs cesta de moedas
    S&P 500 var     20% — apetite de risco americano
    Gold var        12% — fuga para segurança (lógica especial)
    Nasdaq var       8% — tech = barômetro risk-on/off

Lógica especial Gold + DXY:
    Quando Gold sobe E DXY sobe E bolsas caem simultaneamente
    = fuga dupla para segurança = bônus adicional no score.

Integração com o SS:
    Todos os dados são externos (Yahoo Finance).
    Usar fetch_grm_data() para buscar automaticamente.
    Sugestão: atualizar a cada 5 minutos via task asyncio separada.
"""

import logging
from typing import Optional
from .models import GRMInput, GRMOutput, RiskLevel

logger = logging.getLogger(__name__)

# ─── Pesos dos componentes ────────────────────────────────────────────────────

WEIGHTS = {
    "vix":          0.35,
    "dxy":          0.25,
    "sp500_change": 0.20,
    "gold_change":  0.12,
    "nasdaq_change": 0.08,
}

# ─── Funções de scoring por componente ───────────────────────────────────────

def _score_vix(val: float) -> float:
    """
    VIX = volatilidade implícita do S&P500.
    Quanto maior o VIX, maior o medo do mercado global.

    Escala histórica de referência:
        < 13  → euforia / complacência
        13–17 → calmo normal
        17–22 → atenção
        22–28 → nervoso
        28–35 → medo / desalavancagem parcial
        > 35  → pânico / desalavancagem global
    """
    if val < 13:   return 0.0
    if val < 15:   return 10.0
    if val < 17:   return 18.0
    if val < 20:   return 30.0
    if val < 22:   return 42.0
    if val < 25:   return 55.0
    if val < 28:   return 67.0
    if val < 32:   return 78.0
    if val < 38:   return 88.0
    return 97.0


def _score_dxy(val: float) -> float:
    """
    DXY alto = dólar forte = fuga de ativos de risco.
    Historicamente, DXY > 104 é zona de pressão para cripto.

    Escala:
        < 98   → dólar fraco, favorável ao risco
        98–101 → neutro
        101–103 → atenção
        103–106 → pressão
        > 106  → dólar muito forte = adverso
    """
    if val < 98:   return 5.0
    if val < 100:  return 15.0
    if val < 102:  return 30.0
    if val < 104:  return 48.0
    if val < 106:  return 65.0
    if val < 108:  return 80.0
    return 93.0


def _score_sp500_change(pct: float) -> float:
    """
    S&P500 caindo = apetite de risco diminuindo.
    Quedas fortes precedem ou acompanham saídas de cripto.
    """
    if pct > 1.5:   return 0.0
    if pct > 0.5:   return 12.0
    if pct > 0.0:   return 22.0
    if pct > -0.5:  return 35.0
    if pct > -1.0:  return 48.0
    if pct > -1.5:  return 62.0
    if pct > -2.5:  return 76.0
    return 90.0


def _score_gold_change(gold_pct: float, sp500_pct: Optional[float] = None) -> float:
    """
    Gold sobe quando há fuga para segurança.
    Lógica especial: Gold subindo + bolsas caindo = dupla confirmação de risco.

    Se sp500_pct for fornecido, aplica o bônus de correlação.
    """
    # Score base do gold
    if gold_pct > 1.5:   base = 70.0
    elif gold_pct > 0.8: base = 55.0
    elif gold_pct > 0.3: base = 40.0
    elif gold_pct > -0.3: base = 25.0
    elif gold_pct > -0.8: base = 15.0
    else:                 base = 5.0

    # Bônus de correlação: gold subindo E bolsas caindo = fuga dupla
    if sp500_pct is not None and gold_pct > 0.3 and sp500_pct < -0.5:
        bonus = min(25.0, abs(sp500_pct) * 8)
        base = min(100.0, base + bonus)
        logger.debug(f"GRM Gold: fuga dupla detectada (gold={gold_pct:+.2f}% sp500={sp500_pct:+.2f}%) bônus={bonus:.1f}")

    return base


def _score_nasdaq_change(pct: float) -> float:
    """
    Nasdaq lidera ciclos risk-on/off.
    Tech caindo = saída de risco = pressão em cripto.
    """
    if pct > 1.5:   return 0.0
    if pct > 0.5:   return 12.0
    if pct > 0.0:   return 22.0
    if pct > -0.5:  return 35.0
    if pct > -1.5:  return 55.0
    if pct > -2.5:  return 72.0
    return 88.0


# ─── Classificação por score ──────────────────────────────────────────────────

def _classify(score: float) -> RiskLevel:
    if score <= 30: return RiskLevel.LOW
    if score <= 55: return RiskLevel.MODERATE
    if score <= 75: return RiskLevel.HIGH
    return RiskLevel.CRITICAL


# ─── Calculadora principal ────────────────────────────────────────────────────

def calculate_grm(data: GRMInput) -> GRMOutput:
    """
    Calcula o GRM (Global Risk Meter) a partir dos dados fornecidos.

    Campos ausentes são ignorados com normalização proporcional.

    Args:
        data: GRMInput com os valores dos componentes macro.

    Returns:
        GRMOutput com score 0–100, nível e detalhes.

    Exemplo de uso no SS:
        from indicators.grm import calculate_grm, fetch_grm_data
        from indicators.models import GRMInput

        # Opção A — busca automática
        grm_data = await fetch_grm_data()
        result = calculate_grm(grm_data)

        # Opção B — valores externos já disponíveis
        result = calculate_grm(GRMInput(vix=22.4, dxy=104.2, sp500_change=-1.2))

        logger.info(f"GRM: {result.score:.1f} [{result.level.value}]")
    """
    components       = {}
    missing          = []
    weighted_sum     = 0.0
    available_weight = 0.0

    # ── VIX ───────────────────────────────────────────────────────
    if data.vix is not None:
        s = _score_vix(data.vix)
        components["vix"] = {
            "value": data.vix,
            "score": s,
            "weight": WEIGHTS["vix"],
            "label": f"VIX {data.vix:.1f}",
        }
        weighted_sum     += s * WEIGHTS["vix"]
        available_weight += WEIGHTS["vix"]
    else:
        missing.append("vix")

    # ── DXY ───────────────────────────────────────────────────────
    if data.dxy is not None:
        s = _score_dxy(data.dxy)
        components["dxy"] = {
            "value": data.dxy,
            "score": s,
            "weight": WEIGHTS["dxy"],
            "label": f"DXY {data.dxy:.2f}",
        }
        weighted_sum     += s * WEIGHTS["dxy"]
        available_weight += WEIGHTS["dxy"]
    else:
        missing.append("dxy")

    # ── S&P 500 ───────────────────────────────────────────────────
    if data.sp500_change is not None:
        s = _score_sp500_change(data.sp500_change)
        components["sp500_change"] = {
            "value": data.sp500_change,
            "score": s,
            "weight": WEIGHTS["sp500_change"],
            "label": f"S&P500 {data.sp500_change:+.2f}%",
        }
        weighted_sum     += s * WEIGHTS["sp500_change"]
        available_weight += WEIGHTS["sp500_change"]
    else:
        missing.append("sp500_change")

    # ── Gold ──────────────────────────────────────────────────────
    if data.gold_change is not None:
        s = _score_gold_change(data.gold_change, data.sp500_change)
        components["gold_change"] = {
            "value": data.gold_change,
            "score": s,
            "weight": WEIGHTS["gold_change"],
            "label": f"Gold {data.gold_change:+.2f}%",
            "note": "bônus correlação se sp500 negativo" if data.sp500_change and data.sp500_change < -0.5 else "",
        }
        weighted_sum     += s * WEIGHTS["gold_change"]
        available_weight += WEIGHTS["gold_change"]
    else:
        missing.append("gold_change")

    # ── Nasdaq ────────────────────────────────────────────────────
    if data.nasdaq_change is not None:
        s = _score_nasdaq_change(data.nasdaq_change)
        components["nasdaq_change"] = {
            "value": data.nasdaq_change,
            "score": s,
            "weight": WEIGHTS["nasdaq_change"],
            "label": f"Nasdaq {data.nasdaq_change:+.2f}%",
        }
        weighted_sum     += s * WEIGHTS["nasdaq_change"]
        available_weight += WEIGHTS["nasdaq_change"]
    else:
        missing.append("nasdaq_change")

    # ── Score final ───────────────────────────────────────────────
    if available_weight == 0:
        score = 50.0
        logger.warning("GRM: nenhum dado disponível, retornando score neutro 50")
    else:
        score = weighted_sum / available_weight

    score = max(0.0, min(100.0, score))
    level = _classify(score)

    missing_str = f" [faltando: {', '.join(missing)}]" if missing else ""
    summary = (
        f"GRM {score:.1f}/100 [{level.value}]{missing_str} — "
        + _build_summary(components, score)
    )

    logger.debug(f"GRM calculado: score={score:.1f} level={level.value} "
                 f"disponível={available_weight:.2f} missing={missing}")

    return GRMOutput(
        score=round(score, 1),
        level=level,
        components=components,
        missing=missing,
        summary=summary,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_summary(components: dict, score: float) -> str:
    drivers = []
    for k, v in components.items():
        if v["score"] >= 65:
            drivers.append(f"{v['label']} ↑risco")
        elif v["score"] <= 15:
            drivers.append(f"{v['label']} ↓risco")
    if drivers:
        return "Drivers: " + " | ".join(drivers[:3])
    if score > 55: return "ambiente macro adverso"
    if score < 30: return "ambiente macro favorável"
    return "ambiente macro neutro"


# ─── Fetcher automático ───────────────────────────────────────────────────────

async def fetch_grm_data() -> GRMInput:
    """
    Busca automaticamente os dados macro necessários para o GRM.

    Fonte: Yahoo Finance v8 API (sem autenticação)
    Symbols:
        ^VIX    → VIX
        DX-Y.NYB → DXY
        ^GSPC   → S&P 500
        ^IXIC   → Nasdaq
        GC=F    → Gold Futures

    Integração no SS:
        Criar task asyncio periódica (a cada 5min):

        async def _update_grm_task(self):
            while True:
                grm_data = await fetch_grm_data()
                self.grm_result = calculate_grm(grm_data)
                await asyncio.sleep(300)

    Retorna GRMInput com os dados disponíveis.
    Campos que falharem na requisição retornam None.
    """
    import aiohttp

    symbols = {
        "vix":    "%5EVIX",
        "sp500":  "%5EGSPC",
        "nasdaq": "%5EIXIC",
        "dxy":    "DX-Y.NYB",
        "gold":   "GC%3DF",
    }

    prices  = {}
    prevs   = {}

    async with aiohttp.ClientSession() as session:
        for key, sym in symbols.items():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
            try:
                async with session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as r:
                    if r.status == 200:
                        d = await r.json()
                        meta = d["chart"]["result"][0]["meta"]
                        prices[key] = meta["regularMarketPrice"]
                        prevs[key]  = meta.get("previousClose") or meta.get("chartPreviousClose")
            except Exception as e:
                logger.warning(f"GRM fetch {key} ({sym}) falhou: {e}")

    def _pct_change(key: str) -> Optional[float]:
        p = prices.get(key)
        v = prevs.get(key)
        if p and v and v != 0:
            return ((p - v) / v) * 100
        return None

    return GRMInput(
        vix=prices.get("vix"),
        dxy=prices.get("dxy"),
        sp500_change=_pct_change("sp500"),
        nasdaq_change=_pct_change("nasdaq"),
        gold_change=_pct_change("gold"),
    )
