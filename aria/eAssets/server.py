"""
server.py — eAssets Dashboard Backend v2.0
Doreto Squeeze Sniper · Forge · 09/06/2026

Substitui enrich_server.py (Flask) + monitorar_eassets.py (processo separado).
Um único processo FastAPI + asyncio que faz tudo:

  • Monitora Downloads + dados_eassets para novo JSON do eAssets (a cada 2s)
  • Busca dados externos: Yahoo Finance, CoinGecko, FGI, Binance klines
  • Calcula CRM, GRM e BTC Reset nos módulos Python proprietários
  • Serve scores prontos via /api/indicators
  • Mantém compatibilidade total com os endpoints que o HTML já usa

Endpoints:
  GET  /health                → status do servidor
  GET  /api/latest-enriched   → JSON eAssets + signals SS + scores CRM/GRM/BTC Reset
  GET  /api/check-update      → mtime do JSON atual (para o HTML detectar atualizações)
  POST /api/enrich-json       → enriquece JSON enviado com dados CVD do SS
  GET  /api/indicators        → CRM, GRM, BTC Reset calculados pelo Python (novo)

Ciclos de atualização:
  Macro (Yahoo + CoinGecko + FGI) → a cada 3 min
  BTC klines + RSI multi-TF       → a cada 60s
  File monitor (Downloads)        → a cada 2s
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import aiohttp
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── Import dos indicadores proprietários ──────────────────────────────────────
# Adiciona aria/ ao path para que scripts/ seja um package importável
_ARIA_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_ARIA_DIR))

from scripts.crm import calculate_crm, fetch_crm_data
from scripts.grm import calculate_grm, fetch_grm_data
from scripts.btc_reset import calculate_btc_reset
from scripts.models import BTCResetInput, RiskLevel, ResetState

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.parent.parent   # SqueezeSniper-V4/
EASSETS_DIR    = Path(__file__).parent                 # aria/eAssets/
DADOS_DIR      = EASSETS_DIR / "dados_eassets"
JSON_LATEST    = DADOS_DIR / "eassets_latest.json"
SIGNALS_LOG    = BASE_DIR / "logs" / "signals.jsonl"
DOWNLOADS_PATH = Path.home() / "Downloads"

DADOS_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("eAssets.server")

# ── Estado compartilhado (atualizado pelas tasks asyncio) ─────────────────────
state = {
    # Dados brutos externos
    "macro_raw": {},        # Yahoo: VIX, DXY, SP500, Nasdaq, Gold
    "coingecko": {},        # CoinGecko: USDT.D, ETH.D
    "fgi": {},              # Alternative.me: Fear & Greed
    "btc_change_24h": None, # Binance 24h BTC change
    # Scores calculados
    "crm": None,            # CRMOutput
    "grm": None,            # GRMOutput
    "btc_reset": None,      # BTCResetOutput
    # Metadados
    "last_macro_update": 0.0,
    "last_rsi_update": 0.0,
    "last_file_mtime": 0.0,
}

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="eAssets Dashboard Server", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# TASKS DE BACKGROUND
# ═══════════════════════════════════════════════════════════════════════════════

async def _task_macro():
    """
    Busca dados macro a cada 3 minutos e calcula CRM + GRM.
    Fontes: Yahoo Finance (GRM) + CoinGecko (CRM parcial) + Alternative.me (FGI).
    Sem proxy — requisições feitas server-side, sem restrição CORS.
    """
    while True:
        try:
            async with aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as session:
                # ── Yahoo Finance: VIX, DXY, S&P500, Nasdaq, Gold ──────────
                yahoo_symbols = {
                    "vix":    "%5EVIX",
                    "sp500":  "%5EGSPC",
                    "nasdaq": "%5EIXIC",
                    "dxy":    "DX-Y.NYB",
                    "gold":   "GC%3DF",
                }
                macro_raw = {}
                for key, sym in yahoo_symbols.items():
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
                    try:
                        async with session.get(url) as r:
                            if r.status == 200:
                                d = await r.json(content_type=None)
                                meta = d["chart"]["result"][0]["meta"]
                                price = meta["regularMarketPrice"]
                                prev  = meta.get("previousClose") or meta.get("chartPreviousClose")
                                pct   = ((price - prev) / prev * 100) if prev else None
                                macro_raw[key] = {"price": price, "change_pct": pct}
                    except Exception as e:
                        logger.debug(f"Yahoo {key}: {e}")

                state["macro_raw"] = macro_raw

                # ── CoinGecko: USDT.D, ETH.D ────────────────────────────────
                try:
                    async with session.get("https://api.coingecko.com/api/v3/global") as r:
                        if r.status == 200:
                            d = await r.json()
                            pct = d["data"]["market_cap_percentage"]
                            state["coingecko"] = {
                                "usdt_d": pct.get("usdt"),
                                "eth_d":  pct.get("eth"),
                                "btc_d":  pct.get("btc"),
                            }
                except Exception as e:
                    logger.debug(f"CoinGecko: {e}")

                # ── Alternative.me: Fear & Greed ─────────────────────────────
                try:
                    async with session.get("https://api.alternative.me/fng/?limit=1") as r:
                        if r.status == 200:
                            d = await r.json()
                            state["fgi"] = {
                                "value": int(d["data"][0]["value"]),
                                "label": d["data"][0]["value_classification"],
                            }
                except Exception as e:
                    logger.debug(f"FGI: {e}")

                # ── Binance: BTC 24h ─────────────────────────────────────────
                try:
                    async with session.get(
                        "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
                    ) as r:
                        if r.status == 200:
                            d = await r.json()
                            state["btc_change_24h"] = float(d["priceChangePercent"])
                except Exception as e:
                    logger.debug(f"Binance BTC 24h: {e}")

            # ── Calcula CRM ──────────────────────────────────────────────────
            crm_input = await fetch_crm_data(
                btc_change_24h=state.get("btc_change_24h"),
                funding_rate_avg=_avg_funding_from_signals(),
            )
            state["crm"] = calculate_crm(crm_input)

            # ── Calcula GRM ──────────────────────────────────────────────────
            mr = state["macro_raw"]
            from scripts.models import GRMInput
            grm_input = GRMInput(
                vix           = mr.get("vix",    {}).get("price"),
                dxy           = mr.get("dxy",    {}).get("price"),
                sp500_change  = mr.get("sp500",  {}).get("change_pct"),
                nasdaq_change = mr.get("nasdaq", {}).get("change_pct"),
                gold_change   = mr.get("gold",   {}).get("change_pct"),
            )
            state["grm"] = calculate_grm(grm_input)

            state["last_macro_update"] = time.time()
            logger.info(
                f"Macro atualizado — CRM={state['crm'].score:.1f} [{state['crm'].level.value}] "
                f"GRM={state['grm'].score:.1f} [{state['grm'].level.value}]"
            )

        except Exception as e:
            logger.warning(f"_task_macro erro: {e}")

        await asyncio.sleep(180)  # 3 minutos


async def _task_btc_rsi():
    """
    Busca klines BTC em 7 TFs a cada 60s e calcula BTC Reset Monitor.
    Usa a Binance API pública (sem autenticação).
    """
    TF_MAP = {
        "5m":  50,
        "15m": 50,
        "30m": 50,
        "1h":  50,
        "4h":  50,
        "12h": 30,
        "1d":  20,
    }

    while True:
        try:
            rsi_by_tf      = {}
            rsi_history_by = {}

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8)
            ) as session:
                for tf, limit in TF_MAP.items():
                    url = (
                        f"https://api.binance.com/api/v3/klines"
                        f"?symbol=BTCUSDT&interval={tf}&limit={limit}"
                    )
                    try:
                        async with session.get(url) as r:
                            if r.status == 200:
                                data   = await r.json()
                                closes = [float(k[4]) for k in data]

                                from scripts.btc_reset import calculate_rsi, calculate_rsi_history
                                rsi_current    = calculate_rsi(closes)
                                rsi_hist       = calculate_rsi_history(closes, lookback=5)
                                rsi_by_tf[tf]  = rsi_current
                                rsi_history_by[tf] = rsi_hist
                    except Exception as e:
                        logger.debug(f"BTC klines {tf}: {e}")

            if rsi_by_tf:
                btc_reset_input = BTCResetInput(
                    rsi_by_tf         = rsi_by_tf,
                    rsi_history_by_tf = rsi_history_by,
                    liq_usd_1h        = 0.0,   # sem acesso ao SS por ora
                    rsi_threshold     = 30.0,
                    liq_threshold     = 10_000_000,
                )
                state["btc_reset"] = calculate_btc_reset(btc_reset_input)
                state["last_rsi_update"] = time.time()
                logger.info(
                    f"BTC Reset — score={state['btc_reset'].score:.1f} "
                    f"[{state['btc_reset'].state.value}] "
                    f"TFs resetados: {state['btc_reset'].reset_count}"
                )

        except Exception as e:
            logger.warning(f"_task_btc_rsi erro: {e}")

        await asyncio.sleep(60)


async def _task_file_monitor():
    """
    Monitora Downloads + dados_eassets para novo JSON do eAssets.
    Quando detecta arquivo mais recente, copia para eassets_latest.json.
    Substitui monitorar_eassets.py (processo separado).
    """
    last_processed: Optional[Path] = None

    while True:
        try:
            candidates = []

            # Downloads
            dl = max(
                DOWNLOADS_PATH.glob("eassets-panel-*.json"),
                key=os.path.getmtime,
                default=None,
            )
            if dl:
                candidates.append(dl)

            # Pasta local (usuário pode jogar direto)
            local = max(
                (f for f in DADOS_DIR.glob("eassets-panel-*.json")),
                key=os.path.getmtime,
                default=None,
            )
            if local:
                candidates.append(local)

            if candidates:
                newest = max(candidates, key=os.path.getmtime)
                if newest != last_processed:
                    # Aguarda fim do download (tamanho estável)
                    size_before = newest.stat().st_size
                    await asyncio.sleep(0.5)
                    if newest.exists() and newest.stat().st_size == size_before:
                        _copy_json(newest)
                        last_processed = newest

        except Exception as e:
            logger.debug(f"file monitor: {e}")

        await asyncio.sleep(2)


def _copy_json(src: Path) -> None:
    target  = JSON_LATEST
    history = DADOS_DIR / "historico"
    history.mkdir(exist_ok=True)
    shutil.copy2(src, target)
    shutil.copy2(src, history / src.name)
    logger.info(f"Novo JSON detectado: {src.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _avg_funding_from_signals() -> Optional[float]:
    """Calcula funding rate médio dos símbolos no signals.jsonl do SS."""
    if not SIGNALS_LOG.exists():
        return None
    rates = []
    try:
        with open(SIGNALS_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    fr = d.get("fr") or d.get("funding_rate")
                    if fr is not None:
                        rates.append(float(fr))
                except Exception:
                    pass
    except Exception:
        pass
    return sum(rates) / len(rates) if rates else None


def _load_signals() -> dict:
    signals = {}
    if not SIGNALS_LOG.exists():
        return signals
    try:
        with open(SIGNALS_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    sym = d.get("symbol")
                    if sym:
                        signals[sym] = d
                except Exception:
                    pass
    except Exception:
        pass
    return signals


def _indicators_payload() -> dict:
    """Serializa CRM, GRM, BTC Reset para JSON."""
    def _crm_dict():
        c = state["crm"]
        if not c:
            return None
        return {
            "score": c.score,
            "level": c.level.value,
            "summary": c.summary,
            "components": c.components,
            "missing": c.missing,
        }

    def _grm_dict():
        g = state["grm"]
        if not g:
            return None
        return {
            "score": g.score,
            "level": g.level.value,
            "summary": g.summary,
            "components": g.components,
            "missing": g.missing,
        }

    def _reset_dict():
        r = state["btc_reset"]
        if not r:
            return None
        return {
            "score": r.score,
            "state": r.state.value,
            "summary": r.summary,
            "reset_count": r.reset_count,
            "v_detected": r.v_detected,
            "v_tfs": r.v_tfs,
            "liq_multiplier": r.liq_multiplier,
            "tf_statuses": [
                {
                    "tf": s.tf,
                    "rsi": round(s.rsi, 1),
                    "is_reset": s.is_reset,
                    "is_watch": s.is_watch,
                    "is_v": s.is_v,
                    "weight": s.weight,
                }
                for s in r.tf_statuses
            ],
        }

    return {
        "crm": _crm_dict(),
        "grm": _grm_dict(),
        "btc_reset": _reset_dict(),
        "last_macro_update": state["last_macro_update"],
        "last_rsi_update": state["last_rsi_update"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/macro")
async def get_macro():
    """
    Retorna todos os dados externos já buscados pelo servidor em memória.
    O HTML usa este endpoint para popular a seção macro sem precisar
    de proxy (allorigins.win) ou fetch direto de APIs externas do browser.

    Formato compatível com o que fetchMacro() espera:
      yahoo.{dxy,sp500,nasdaq,vix,gold} → {price, change_pct}
      btc  → {price, change_pct}
      coingecko → {btc_d, eth_d, usdt_d}
      fgi  → {value, label}
    """
    mr = state["macro_raw"]
    cg = state.get("coingecko", {})
    return JSONResponse({
        "yahoo": {
            "dxy":    mr.get("dxy"),
            "sp500":  mr.get("sp500"),
            "nasdaq": mr.get("nasdaq"),
            "vix":    mr.get("vix"),
            "gold":   mr.get("gold"),
        },
        "btc": {
            "price":      None,           # browser já busca do Binance diretamente
            "change_pct": state.get("btc_change_24h"),
        },
        "coingecko": {
            "btc_d":  cg.get("btc_d"),
            "eth_d":  cg.get("eth_d"),
            "usdt_d": cg.get("usdt_d"),
        },
        "fgi": state.get("fgi", {}),
        "last_update": state["last_macro_update"],
    })


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "crm_ready": state["crm"] is not None,
        "grm_ready": state["grm"] is not None,
        "btc_reset_ready": state["btc_reset"] is not None,
        "json_ready": JSON_LATEST.exists(),
    }


@app.get("/api/indicators")
async def get_indicators():
    """Scores CRM, GRM e BTC Reset calculados pelos módulos Python."""
    return JSONResponse(_indicators_payload())


@app.get("/api/latest-enriched")
async def get_enriched():
    """
    Retorna o JSON eAssets mais recente enriquecido com:
      - dados do signals.jsonl do SS (ss_score, ss_trades_1m, etc.)
      - scores CRM, GRM, BTC Reset calculados pelo Python
    Compatível com o endpoint original — o HTML continua funcionando.
    """
    if not JSON_LATEST.exists():
        return JSONResponse({"error": "Nenhum JSON detectado ainda"}, status_code=404)

    try:
        with open(JSON_LATEST, encoding="utf-8") as f:
            eassets_data = json.load(f)

        signals = _load_signals()

        # Enriquecimento SS
        main_data = eassets_data.get("data", {})
        for symbol, info in main_data.items():
            if symbol in signals:
                ss = signals[symbol]
                info["ss_score"]     = ss.get("score", 0)
                info["ss_cvd_1m"]    = ss.get("cvd_1m", 0)
                info["ss_trades_1m"] = ss.get("trades_1m", 0)
                info["ss_status"]    = "GATILHO ATIVO"

        # Macro bruto (compatibilidade com HTML existente)
        mr = state["macro_raw"]
        eassets_data["macro_tradfi"] = {
            name: {"price": v.get("price"), "change": v.get("change_pct", 0)}
            for name, v in mr.items()
        }
        eassets_data["sentiment"] = state["fgi"]

        # Scores Python — campo novo, o HTML ignora campos desconhecidos
        eassets_data["indicators"] = _indicators_payload()

        # Salva consolidado para auditoria
        consolidated = JSON_LATEST.parent / "eassets_consolidado_com_sniper.json"
        with open(consolidated, "w", encoding="utf-8") as f:
            json.dump(eassets_data, f, indent=2)

        return JSONResponse(eassets_data)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/check-update")
async def check_update():
    if not JSON_LATEST.exists():
        return JSONResponse({"mtime": 0})
    return JSONResponse({"mtime": os.path.getmtime(JSON_LATEST)})


@app.post("/api/enrich-json")
async def enrich_json(request: Request):
    """
    Enriquece JSON enviado via POST com dados CVD do SS.
    Compatível com auto_enrich_cvd.js existente.
    """
    try:
        data = await request.json()
        signals = _load_signals()

        enriched_count = 0
        main_data = data.get("data", {})
        for symbol, info in main_data.items():
            if symbol in signals:
                ss = signals[symbol]
                info["ss_score"]     = ss.get("score", 0)
                info["ss_cvd_1m"]    = ss.get("cvd_1m", 0)
                info["ss_trades_1m"] = ss.get("trades_1m", 0)
                info["ss_status"]    = "GATILHO ATIVO"
                enriched_count += 1

        data["enriched_symbols"] = enriched_count
        return JSONResponse(data)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(_task_macro())
    asyncio.create_task(_task_btc_rsi())
    asyncio.create_task(_task_file_monitor())
    logger.info("eAssets Server v2.0 iniciado — CRM + GRM + BTC Reset ativos")


if __name__ == "__main__":
    print("🔥 eAssets Dashboard Server v2.0")
    print("📡 http://127.0.0.1:5001")
    print("📊 /api/indicators — CRM + GRM + BTC Reset (Python)")
    print("🔗 /api/latest-enriched — eAssets + SS + scores")
    uvicorn.run("server:app", host="127.0.0.1", port=5001, reload=False)
