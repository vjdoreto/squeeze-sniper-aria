import asyncio
import contextlib
import json
import logging
import signal
import sys
import time
import os
import socket
import aiohttp
from logging.handlers import RotatingFileHandler
from typing import Optional, Any, Dict, List, TYPE_CHECKING, cast, Tuple

from binance import AsyncClient
from rich.live import Live

from pathlib import Path
from datetime import datetime, timedelta, timezone

from config import (
    load_config,
    load_preferences,
    resolve_preferences_path,
    get_mode_node,
    get_mode_signal,
    get_mode_execution,
    ModeName,
    BotConfig,
)
from src.market_view import build_rows, calculate_fit_score
from src.bot_state import BotState
from src.data_engine import DataEngine
from src.persistence import SignalJournal
from src.paper_tracker import PaperConfig, PaperTradeTracker
from src.risk_manager import DrawdownManager, SymbolThrottler, CORR_GROUPS
from src.live_tracker import LiveConfig, LiveTracker
from src.signal_engine import SqueezeIgnition
from src.sniper import Sniper
from src.symbols import list_usdt_perpetual_symbols
from src.ui import Dashboard
from src.web_dashboard import run_dashboard_thread
from src.paper_analyzer import PaperAnalyzer
from src.telegram_alert import TelegramAlert
from src.backup_session import create_backup

def setup_logging():
    """Configura logs e encoding global para evitar erros de Unicode no Windows."""
    # SPRINT 12.38: Força encoding UTF-8 nos streams ANTES de iniciar o logger
    try:
        stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
        if callable(stdout_reconfigure):
            stdout_reconfigure(encoding="utf-8")

        stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
        if callable(stderr_reconfigure):
            stderr_reconfigure(encoding="utf-8")
    except Exception:
        pass

    os.makedirs("logs", exist_ok=True)

    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    # SPRINT 12.37: basicConfig não aceita 'encoding' sem 'filename' (Erro Pylance)
    # O encoding do console é garantido pelo reconfigure acima.
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    
    # SPRINT 11: Nível INFO por padrão para reduzir uso de CPU/Disco. 
    # DEBUG apenas se houver problema específico.
    logging.getLogger("Main").setLevel(logging.INFO)
    logging.getLogger("DataEngine").setLevel(logging.INFO)
    logging.getLogger("MetricStore").setLevel(logging.INFO)
    logging.getLogger("WebDashboard").setLevel(logging.INFO)
    logging.getLogger("SignalEngine").setLevel(logging.INFO)
    
    # Log de erro em arquivo para facilitar debug de "Offline"
    file_handler = RotatingFileHandler("logs/error.log", maxBytes=1024*1024, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter(log_fmt))
    logging.getLogger().addHandler(file_handler)

setup_logging()
logger = logging.getLogger("Main")

# SPRINT 12.107: Silencia o ruído 'WinError 10054' do asyncio no Windows.
# Ocorre quando o health check fecha a conexão antes do loop proactor processar.
class AsyncioWinErrorFilter(logging.Filter):
    def filter(self, record):
        return "WinError 10054" not in record.getMessage()

logging.getLogger("asyncio").addFilter(AsyncioWinErrorFilter())

# ---- Dashboard startup diagnostics (main-side) ----
_MAIN_DASH_DIAG_PATH = Path("logs/dashboard_startup_diagnostics.log")
def _main_dash_diag(msg: str) -> None:
    try:
        _MAIN_DASH_DIAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _MAIN_DASH_DIAG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
    except Exception:
        pass

# ---- Single-instance guard (evita rodar 2 bots ao mesmo tempo e tomar ban) ----
_INSTANCE_LOCK_PATH = Path("logs/instance_lock_main.pid")


def _pid_is_alive(pid: int) -> bool:
    try:
        # Windows: sinal 0 costuma funcionar pra validar existência
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _acquire_instance_lock() -> tuple[bool, Optional[int]]:
    try:
        _INSTANCE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        # O_EXCL garante que só 1 processo cria o arquivo
        fd = os.open(str(_INSTANCE_LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True, None
    except FileExistsError:
        try:
            existing = _INSTANCE_LOCK_PATH.read_text(encoding="utf-8").strip()
            pid = int(existing) if existing else None
            if pid is not None and _pid_is_alive(pid):
                return False, pid
        except Exception:
            pass
        # lock stale: tenta sobrescrever
        try:
            _INSTANCE_LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        return _acquire_instance_lock()
    except Exception:
        return True, None


def _release_instance_lock() -> None:
    try:
        _INSTANCE_LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

# Menos ruído ao fechar WebSocket da Binance com Ctrl+C
logging.getLogger("binance.ws.reconnecting_websocket").setLevel(logging.CRITICAL)
logging.getLogger("websockets.client").setLevel(logging.INFO)
logging.getLogger("DataEngine").setLevel(logging.INFO)

def _save_prefs(prefs: dict):
    """Escrita atômica no preferences.json para evitar corrupção no Windows."""
    from config import DEFAULT_PREFERENCES_PATH
    try:
        tmp_path = DEFAULT_PREFERENCES_PATH.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=4, ensure_ascii=False)
        tmp_path.replace(DEFAULT_PREFERENCES_PATH)
    except Exception as e:
        logger.error("❌ Falha ao salvar preferências: %s", e)


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _btc_exp_strength_sort_key(x: Dict[str, Any]) -> float:
    """
    Safe conversion for sorting exp_btc:5m.
    Handles int, float, str, or None values returning a float.
    """
    try:
        val = x.get("exp_btc:5m")
    except Exception:
        return -999.0

    if isinstance(val, int):
        return float(val)
    if isinstance(val, float):
        return val
    if isinstance(val, str):
        try:
            return float(val)
        except Exception:
            return -999.0

    return -999.0


async def _execute_signal(
    sniper: Sniper,
    engine: DataEngine,
    symbol: str,
    signal: dict,
    inflight: set,
    state: Optional[BotState] = None,
) -> None:
    # Debug: confirmar se o pipeline está chamando sniper.execute_long
    try:
        debug_path = Path("logs/pipeline_debug.jsonl")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "ts": time.time(),
                    "event": "execute_signal_called",
                    "symbol": symbol,
                    "sniper_trading_mode": getattr(sniper, "trading_mode", None),
                    "state_trading_mode": getattr(getattr(sniper, "paper_tracker", None), "trading_mode", None),
                    "signal_price": signal.get("price"),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    except Exception:
        pass

    # SPRINT 11.34: Armazena o preço ideal do sinal para auditoria de slippage no dashboard LIVE
    if state is not None and sniper.trading_mode == "live":
        # Usamos getattr/setattr para evitar erros Pylance se o atributo não estiver na classe BotState
        if not hasattr(state, "_live_expected_prices"):
            setattr(state, "_live_expected_prices", {})
        getattr(state, "_live_expected_prices")[symbol] = signal["price"]

    try:
        await sniper.execute_long(
            symbol,
            signal["price"],
            signal=signal,
            market_data=engine.data,
        )
    finally:
        inflight.discard(symbol)


async def paper_analysis_loop(
    analyzer: PaperAnalyzer,
    signals: SqueezeIgnition,
    sniper: Sniper,
    tracker: PaperTradeTracker,
    telegram: Optional[TelegramAlert],
    state: BotState,
    interval_minutes: int = 15,
) -> None:
    """Loop de análise do Paper. Também dispara relatório Telegram horário (a cada 60min) — Roadmap 3.4."""
    interval_seconds = interval_minutes * 60
    logger.info(f"📊 Analisador de paper iniciado (intervalo: {interval_minutes}min)")

    # Roadmap 3.4: hourly report a cada 60min (Paper-only)
    last_hourly_sent_at = time.time()

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            result = analyzer.run_analysis()
            if result:
                # SPRINT 6.2 / Melhoria 8: Persistência das mudanças em preferences_local.json
                prefs_path = resolve_preferences_path()
                current_prefs = load_preferences(prefs_path)

                changed = False

                # 1. Aplica Blacklist
                if result.parameter_changes.get("blacklist"):
                    new_entries = result.parameter_changes["blacklist"]
                    signals.blacklist.update(new_entries)
                    
                    existing_bl = set(current_prefs.get("blacklist", []))
                    existing_bl.update(new_entries)
                    current_prefs["blacklist"] = sorted(list(existing_bl))
                    changed = True
                    logger.info("🛡️ Blacklist atualizada e persistida: %s", current_prefs["blacklist"])
                
                # 2. Aplica parâmetros de sinal — escreve em <mode>.signal (nunca na raiz)
                _mode = current_prefs.get("trading_mode", "paper")
                if "signal" in result.parameter_changes:
                    sig_changes = result.parameter_changes["signal"]
                    sig_node = current_prefs.setdefault(_mode, {}).setdefault("signal", {})
                    for attr, val in sig_changes.items():
                        if hasattr(signals, attr):
                            setattr(signals, attr, val)
                            sig_node[attr] = val
                            changed = True
                            logger.info("⚙️ Parâmetro %s otimizado para %s via Auto-Calibração", attr, val)

                # 3. Aplica parâmetros de execução — escreve em <mode>.execution (nunca na raiz)
                if "execution" in result.parameter_changes:
                    exec_changes = result.parameter_changes["execution"]
                    exec_node = current_prefs.setdefault(_mode, {}).setdefault("execution", {})
                    for attr, val in exec_changes.items():
                        if hasattr(sniper, attr):
                            setattr(sniper, attr, val)
                            exec_node[attr] = val
                            changed = True
                            logger.info("⚙️ Sniper %s otimizado para %s via Auto-Calibração", attr, val)

                if changed:
                    _save_prefs(current_prefs)
                    logger.info("💾 Preferências auto-calibradas salvas.")

        except Exception as e:
            logger.exception("Erro no analisador de paper: %s", e)


async def trading_loop(
    engine: DataEngine,
    signals: SqueezeIgnition,
    sniper: Sniper,
    state: BotState,
    journal: SignalJournal,
    inflight: set,
    telegram: Optional[TelegramAlert] = None,
    risk_manager: Optional[DrawdownManager] = None,
) -> None:
    # SPRINT 12.170: Rastro local para evitar chamadas redundantes ao RiskManager
    last_processed_closed_count = 0

    symbol_throttler = SymbolThrottler(window_seconds=3600) # 1h de cooldown

    try:
        # SPRINT 6.24: Warmup Gate (Governança de Dados)
        # Impede trades nos primeiros 5 min para garantir que as tendências (slopes) estejam maduras.
        warmup_period = 300 # 5 minutos
        warmup_announced = False # SPRINT 6.32: Confirmação visual de prontidão
        market_view = {} # SPRINT 6.35: Previne UnboundLocalError se o try falhar



        while True:
            warmup_remaining = _safe_float(state.get_warmup_remaining(), default=0.0)

            # DNA Sniper P1: Loop otimizado com cache de scores (Performance crítica)
            try:
                now = time.time()
                market_view = {}
                stats = {"with_price": 0, "with_oi": 0, "with_trend": 0}
                all_scores = []

                engine_syms = list(engine.symbols)

                # DNA Sniper P1: Único loop otimizado (sem cópias desnecessárias)
                for idx, sym in enumerate(engine_syms):
                    d = engine.data.get(sym)
                    if not d:
                        continue
                    
                    # SPRINT 12.95: Consome cache centralizado no BotState
                    score_val = state.get_fit_score(sym, d)

                    d["score"] = score_val  # Persiste no motor
                    market_view[sym] = d  # Referência direta (sem copy)
                    
                    all_scores.append(score_val)
                    
                    # Stats inline (sem cópias)
                    if (d.get("price") or 0) > 0:
                        stats["with_price"] += 1
                    if (d.get("oi") or 0) > 0:
                        stats["with_oi"] += 1
                    if d.get("oi_trend:5m") is not None:
                        stats["with_trend"] += 1

                    # SPRINT 11.1: Alívio de CPU
                    if idx % 50 == 0:
                        await asyncio.sleep(0)

                # Atualiza Squeezometer (média top 10)
                all_scores.sort(reverse=True)
                state.market_squeeze_level = sum(all_scores[:10]) / 10 if all_scores else 0
                # F-04: rastreia pico horário para o relatório horário não capturar valor zerado
                if state.market_squeeze_level > state.squeeze_peak_1h:
                    state.squeeze_peak_1h = state.market_squeeze_level
                state.bind_market(engine.data, len(engine.symbols))

                rows = build_rows(market_view, min_exp=-0.01, min_oi_trend=-0.01, max_lsr_trend=10.0, limit=100)

                # SPRINT 11.29: Identificação de ativos mais fortes que o BTC
                strong_assets: List[str] = []
                sorted_by_strength = sorted(
                    [{"symbol": s, **d} for s, d in market_view.items() if d and s not in ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]],
                    key=_btc_exp_strength_sort_key,
                    reverse=True,
                )
                for d in sorted_by_strength[:5]:
                    if isinstance(d, dict):
                        val = d.get("exp_btc:5m")
                        if val is not None and float(val or 0.0) > 0:
                            strong_assets.append(f"{d.get('symbol', 'UNK')} ({(float(val or 0.0)):.2f})")

                macro_state: Dict[str, Any] = {}
                for sym in ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]:
                    md = market_view.get(sym)
                    if md:
                        macro_state[sym] = {
                            "price": md.get("price", 0),
                            "pc_1h": md.get("price_change:1h"),
                            "rsi_5m": md.get("rsi:5m"),
                            "exp": md.get("exp:5m"),
                        }
                macro_state["strong_than_btc"] = strong_assets

                # SPRINT 12.81: Restaura Sinais Bloqueados (Geral e Última Hora) para o Cockpit do Dashboard
                ref_stats = signals.get_refusal_stats()
                stats.update(ref_stats)
                
                state.set_dashboard_data(rows, macro_state, stats)
            except Exception as e:
                logger.error("[DASHBOARD] Erro ao atualizar dados: %s", e)


            # Sprint 5.4: Alerta de Pânico no Telegram
            # Roadmap P0: notificações Telegram no PAPER devem ser só em eventos reais
            # (trade open/close) + relatório horário. Então, panic fica somente no LIVE.
            # SPRINT 12.125: Alerta de pânico ativado para ambos os modos (visibilidade institucional)
            if telegram and state.market_squeeze_level > 80:
                # Evita spam: só envia se não enviou nos últimos 5 minutos
                now = time.time()
                last_panic = _safe_float(getattr(state, "_last_panic_ts", 0.0), 0.0)
                if now - last_panic > 300:  # 5 minutos de cooldown
                    asyncio.create_task(telegram.panic_warning(state.market_squeeze_level))
                    setattr(state, "_last_panic_ts", now)
            if state.market_paused:
                # Se o Squeezometer estiver abaixo de 20 por mais de 10 min, entra em hibernação
                await asyncio.sleep(30)
                continue

            # SPRINT 11.32: Conexão Guard (Req 1 Doreto)
            if not engine.is_healthy():
                logger.warning("📡 [SEGURANÇA] Dados estagnados. Gatilho bloqueado até normalização da internet.")
                await asyncio.sleep(2)
                continue

            # SPRINT 12.155: Integração do DrawdownManager (Governança Semana 3-4)
            if risk_manager:
                # Sincroniza manager com o estado atual do tracker ativo
                tracker = sniper.live_tracker if state.trading_mode == "live" else sniper.paper_tracker
                if tracker:
                    # Type narrowing para evitar AttributeAccessIssue (Pylance/Pyright)
                    if state.trading_mode == "live" and hasattr(tracker, "get_stats"):
                        st = tracker.get_stats()
                    elif hasattr(tracker, "_stats"):
                        st = tracker._stats()
                    else:
                        st = {}

                    current_closed = st.get("closed_count", 0)
                    
                    # Só atualiza o contador de vitórias/derrotas se um novo trade foi fechado
                    if current_closed > last_processed_closed_count:
                        # Acessa histórico de forma segura
                        history = getattr(tracker, "_closed", [])
                        last_trade = history[-1] if history else {}
                        is_win = (last_trade.get("exit") or {}).get("pnl_pct", 0) > 0
                        risk_manager.update(tracker.current_capital, tracker.peak_capital, is_win)
                        last_processed_closed_count = current_closed
                        
                        # SPRINT 12.156: Atualiza o multiplicador no sniper
                        sniper.risk_multiplier = risk_manager.risk_multiplier

                    if not risk_manager.can_trade():
                        await asyncio.sleep(30)
                        continue

            # SPRINT 5.8: Priorização de processamento.
            # Moedas em cascata ou com scores altos são analisadas primeiro para reduzir latência de disparo.
            sorted_symbols = sorted(
                engine.symbols, 
                key=lambda s: (
                    engine.data.get(s, {}).get("liq_cascade", False), 
                    engine.data.get(s, {}).get("score", 0)
                ), 
                reverse=True
            )
            for symbol in sorted_symbols:
                if not warmup_announced and warmup_remaining <= 0.0:
                    logger.info("🎯 SNIPER STATUS: Warmup de 300s concluído. Gatilho LIBERADO.")
                    warmup_announced = True

                if symbol not in engine.data:
                    continue
                d = engine.data[symbol]
                if not d.get("price"):
                    continue
                
                try:
                    # SPRINT 6.33: A PENEIRA (Dynamic Sieve)
                    # SPRINT 12.70: Peneira dinâmica baseada no Squeezometer global.
                    # Se o mercado está em pânico (>80), baixamos a régua da peneira para 55
                    # para não perder ignições rápidas em ativos que estão acordando.
                    squeeze_level = state.market_squeeze_level
                    if squeeze_level > 80:
                        sieve_threshold = 55   # Agressivo: captura ignições precoces
                    elif squeeze_level > 60:
                        sieve_threshold = 65   # Moderado
                    else:
                        sieve_threshold = 75   # Conservador: só elite

                    d_score = d.get("score", 0)
                    if d_score < sieve_threshold and not d.get("liq_cascade", False) and symbol not in inflight:
                        # Só vira ghost se score for alto — sinais com score baixo não são candidatos úteis
                        if d_score >= 70:
                            state.add_ghost_signal({
                                "symbol": symbol, "score": d_score,
                                "reason": "score_below_sieve", "price": d.get("price")
                            })
                        continue

                    hit: Optional[dict] = signals.analyze(
                        symbol,
                        engine.data,
                        score=d.get("score"),
                        market_squeeze_level=state.market_squeeze_level,
                        trading_mode=state.trading_mode,
                        state=state,
                    )
                    if not hit:
                        # Sprint 5.6: Captura sinais fantasma (Score > 40 que não dispararam)
                        score = d.get("score", 0)
                        # SPRINT 12.72: Log de Diagnóstico em Pânico
                        # Se o Squeezometer está alto (>80) e um ativo com Score > 80 falhou no gate final, logamos o motivo.
                        # SPRINT 12.100: Rate limiting para logs de DIAGNÓSTICO PANIC
                        # Cada símbolo loga no máximo 1 vez a cada 60 segundos
                        if not hasattr(state, "_panic_log_ts"):
                            setattr(state, "_panic_log_ts", {})

                        panic_log_ts = getattr(state, "_panic_log_ts")
                        now = time.time()
                        last_log = panic_log_ts.get(symbol, 0)

                        if state.market_squeeze_level > 80 and score >= 80 and (now - last_log) > 60:
                            ghost_info = signals.get_ghost_info(symbol)
                            if ghost_info:
                                logger.info(
                                    "🔍 [DIAGNÓSTICO PANIC] %s (Score %d) bloqueado por: %s",
                                    symbol, score, ghost_info["reason_code"]
                                )
                                panic_log_ts[symbol] = now

                        if score > 20:
                            ghost_info = signals.get_ghost_info(symbol)
                            if ghost_info:
                                state.add_ghost_signal({
                                    "symbol": symbol,
                                    "score": score,
                                    "reason": ghost_info["reason_code"],
                                    "price": d.get("price")
                                })
                        continue
                except Exception as e:
                    logger.error("❌ Erro ao analisar %s: %s", symbol, e)
                    continue
                
                # Type Narrowing para o linter (hit não é mais None)
                assert hit is not None

                # SPRINT 12.132: Throttle por Símbolo (Anti-Revenge Trading)
                # Bloqueia se já operou esta moeda na última 1 hora
                if not symbol_throttler.can_trade(symbol):
                    logger.debug(f"🛡️ [THROTTLE] {symbol} em período de cooldown (1h).")
                    continue

                # Verifica se o período de Warmup já passou
                if warmup_remaining > 0.0:
                    logger.info(
                        "⏳ WARMUP: Sinal detectado em %s, mas Sniper aguardando maturação dos dados (%.0fs restantes).",
                        symbol,
                        warmup_remaining,
                    )
                    continue

                # DNA Sniper: Usa o modo dinâmico do state para consistência em runtime
                current_mode = state.trading_mode
                journal.log_signal(hit, trading_mode=current_mode)
                state.add_signal(hit, paper=(current_mode == "paper"))
                
                # DNA Sniper: Registra o trade no throttler para ativar o cooldown de 1h
                symbol_throttler.record_trade(symbol)

                # Sprint 5.4: Disparo do sinal para o celular
                # SPRINT 11: Spam filter ativo. Notificamos apenas execuções reais no paper_tracker/sniper.
                # if telegram: asyncio.create_task(telegram.signal(hit, state.trading_mode))

                # Debug imediato: hit detectado e task será agendada
                try:
                    debug_path = Path("logs/pipeline_debug.jsonl")
                    debug_path.parent.mkdir(parents=True, exist_ok=True)
                    hit_lsr_trend_val = hit.get("lsr_trend")
                    hit_lsr_trend_neg = (
                        hit_lsr_trend_val is not None
                        and _safe_float(hit_lsr_trend_val, default=0.0) < 0
                    )

                    debug_path.open("a", encoding="utf-8").write(
                        json.dumps(
                            {
                                "ts": time.time(),
                                "event": "signal_hit",
                                "symbol": symbol,
                                "state_trading_mode": state.trading_mode,
                                "hit_price": hit.get("price"),
                                "hit_lsr_trend": hit_lsr_trend_val,
                                "hit_lsr_trend_neg": hit_lsr_trend_neg,
                                "hit_trades_1m": hit.get("trades_1m"),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                except Exception as e:
                    try:
                        err_path = Path("logs/pipeline_debug_error.jsonl")
                        err_path.parent.mkdir(parents=True, exist_ok=True)
                        err_path.open("a", encoding="utf-8").write(
                            json.dumps(
                                {
                                    "ts": time.time(),
                                    "event": "signal_hit_debug_error",
                                    "symbol": symbol,
                                    "state_trading_mode": state.trading_mode,
                                    "exception": str(e),
                                    "hit_lsr_trend": hit.get("lsr_trend"),
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    except Exception:
                        pass
                
                # SPRINT 12.132: Throttle por Símbolo (Análise Honesta)
                # DNA Sniper: Verificação atômica de duplicidade antes de qualquer processamento
                if symbol in inflight:
                    continue

                # Verifica se já está aberto no tracker ativo
                is_open = False
                if state.trading_mode == "paper" and sniper.paper_tracker:
                    if sniper.paper_tracker.has_open(symbol):
                        is_open = True
                elif state.trading_mode == "live" and sniper.live_tracker:
                    if any(p["symbol"] == symbol for p in state._live_positions):
                        is_open = True
                
                if is_open:
                    continue

                # Impede abrir um segundo trade no mesmo símbolo se já houver um inflight ou aberto
                if state.trading_mode == "live":
                    if any(p["symbol"] == symbol for p in state._live_positions):
                        continue
                    
                    # SPRINT 12.205: Strict Sector Correlation Guard (DNA Pilar 2)
                    # Bloqueia se já houver posição aberta no mesmo setor (L1, Meme, DeFi)
                    current_sector = next((g for g, syms in CORR_GROUPS.items() if symbol in syms), None)
                    if current_sector:
                        open_symbols = [p["symbol"] for p in state._live_positions]
                        if any(s in CORR_GROUPS[current_sector] for s in open_symbols):
                            logger.warning(f"🛡️ [CORRELATION] {symbol} bloqueado. Setor {current_sector} já possui posições abertas.")
                            continue
                
                if state.trading_mode == "paper" and sniper.paper_tracker:
                    if sniper.paper_tracker.has_open(symbol):
                        continue
                    
                    # Paridade total Paper/Live no Correlation Guard
                    current_sector = next((g for g, syms in CORR_GROUPS.items() if symbol in syms), None)
                    if current_sector:
                        open_symbols = list(sniper.paper_tracker._open.keys())
                        if any(s in CORR_GROUPS[current_sector] for s in open_symbols):
                            continue

                if symbol in inflight:
                    continue
                inflight.add(symbol)
                asyncio.create_task(
                    _execute_signal(sniper, engine, symbol, hit, inflight, state)
                )

            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                return
    except asyncio.CancelledError:
        return


async def paper_monitor_loop(
    tracker: PaperTradeTracker,
    engine: DataEngine,
    interval: float,
) -> None:
    # Hot-reload do limite global de posições do Paper (max_open_positions)
    # para evitar precisar de hard reset do processo durante testes.
    prefs_path = resolve_preferences_path()
    last_max_open_positions: Optional[int] = None

    while True:
        try:
            prefs = load_preferences(prefs_path)
            paper_cfg = prefs.get("paper") or {}
            new_max_open_positions = int(
                paper_cfg.get("max_open_positions", tracker.config.max_open_positions)
            )

            if last_max_open_positions != new_max_open_positions:
                if tracker.config.max_open_positions != new_max_open_positions:
                    prev = tracker.config.max_open_positions
                    tracker.config.max_open_positions = new_max_open_positions

                    # Persistir em paper_debug.jsonl (para podermos inspecionar se o hot-reload rodou)
                    try:
                        if hasattr(tracker, "_append_debug") and callable(getattr(tracker, "_append_debug")):
                            tracker._append_debug(
                                {
                                    "ts": time.time(),
                                    "event": "paper_config_hot_reload",
                                    "prev_max_open_positions": prev,
                                    "new_max_open_positions": new_max_open_positions,
                                    "prefs_file": prefs_path.name,
                                }
                            )
                    except Exception:
                        pass

                    logger.info(
                        "♻️ PaperConfig hot-reload: max_open_positions=%s (via %s)",
                        new_max_open_positions,
                        prefs_path.name,
                    )
                last_max_open_positions = new_max_open_positions
        except Exception as e:
            logger.warning("⚠️ Falha ao hot-reload paper.max_open_positions: %s", e)

        tracker.tick(engine.data)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            return


async def paper_hourly_report_loop(
    tracker: PaperTradeTracker,
    telegram: TelegramAlert,
    state: BotState,
    interval_seconds: int = 3600,
) -> None:
    """Relatório horário (Paper-only) — Roadmap 11 (3.4)."""
    logger.info("🕒 Relatório horário do Paper iniciado (intervalo: %ss).", interval_seconds)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            if state.trading_mode != "paper":
                continue
            snap = tracker.snapshot()
            # F-04: usa pico da última hora em vez do valor instantâneo (evita capturar reset)
            snap["market_squeeze_level"] = state.squeeze_peak_1h
            state.squeeze_peak_1h = 0.0  # reset após enviar
            # Trades fechados na última hora para o relatório horário
            cutoff = time.time() - interval_seconds
            snap["trades_1h"] = [
                t for t in tracker._closed
                if (t.get("exit") or {}).get("time", 0) >= cutoff
            ]
            await telegram.send_hourly_report(snap)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("⚠️ Falha no hourly report: %s", e)


async def paper_daily_report_loop(
    tracker: PaperTradeTracker,
    telegram: TelegramAlert,
    state: BotState,
    interval_seconds: int = 86400,
) -> None:
    """Relatório diário (Paper-only) — envia às 20:50 UTC-3."""
    logger.info("📅 Relatório diário do Paper iniciado (intervalo: %ss).", interval_seconds)
    while True:
        try:
            # Calcula tempo até 20:50 UTC-3
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=-3)))
            target = now.replace(hour=20, minute=50, second=0, microsecond=0)
            if now >= target:
                target = target + timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            
            logger.info("📅 Próximo relatório diário em %.1f horas (às 20:50)", wait_seconds / 3600)
            await asyncio.sleep(wait_seconds)
            
            if state.trading_mode != "paper":
                continue

            snap = tracker.snapshot()
            await telegram.send_daily_report(snap)
            logger.info("📅 Relatório diário enviado com sucesso")
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("⚠️ Falha no daily report: %s", e)


async def live_hourly_report_loop(
    tracker: LiveTracker,
    telegram: TelegramAlert,
    state: BotState,
    interval_seconds: int = 3600,
) -> None:
    """Relatório horário (LIVE-only) — usa dados do LiveTracker + estado do BotState."""
    logger.info("🕒 Relatório horário do LIVE iniciado (intervalo: %ss).", interval_seconds)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            if state.trading_mode != "live":
                continue

            snap = tracker.get_snapshot()
            # F-04: usa pico da última hora em vez do valor instantâneo (evita capturar reset)
            snap["market_squeeze_level"] = state.squeeze_peak_1h
            state.squeeze_peak_1h = 0.0  # reset após enviar
            snap["uptime_sec"] = int(time.time() - state.boot_started_at)

            await telegram.send_hourly_report(snap)
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("⚠️ Falha no LIVE hourly report: %s", e)


async def live_daily_report_loop(
    tracker: LiveTracker,
    telegram: TelegramAlert,
    state: BotState,
    interval_seconds: int = 86400,
) -> None:
    """Relatório diário (LIVE-only) — envia às 20:50 UTC-3 usando LiveTracker."""
    logger.info("📅 Relatório diário do LIVE iniciado (intervalo: %ss).", interval_seconds)
    while True:
        try:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=-3)))
            target = now.replace(hour=20, minute=50, second=0, microsecond=0)
            if now >= target:
                target = target + timedelta(days=1)
            wait_seconds = (target - now).total_seconds()

            logger.info("📅 Próximo relatório diário LIVE em %.1f horas (às 20:50)", wait_seconds / 3600)
            await asyncio.sleep(wait_seconds)

            if state.trading_mode != "live":
                continue

            snap = tracker.get_snapshot()
            snap["market_squeeze_level"] = state.market_squeeze_level
            snap["uptime_sec"] = int(time.time() - state.boot_started_at)

            await telegram.send_daily_report(snap)
            logger.info("📅 Relatório diário LIVE enviado com sucesso")
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("⚠️ Falha no LIVE daily report: %s", e)


from binance import BinanceSocketManager
async def live_monitor_loop(
    state: BotState,
    client: AsyncClient,
    sniper: Sniper,
    engine: DataEngine,
    telegram: Optional[TelegramAlert] = None,
    interval_seconds: int = 10,
) -> None:
    """
    Painel LIVE read-only (4.2).
    Agora usa FUTURES user-data stream (listenKey via BinanceSocketManager) para evitar REST (-1003).
    """

    logger.info("📡 live_monitor_loop iniciado via user-data stream (intervalo=%ss).", interval_seconds)

    bsm = BinanceSocketManager(client)

    # Cache para atualizar posição “atualizada” sem depender de markPrice no payload.
    # SPRINT 12.50: Inicializa cache com o estado atual do bot para evitar perda de dados no reconect
    last_positions: Dict[str, Dict[str, Any]] = {
        p["symbol"]: p for p in (state._live_positions or [])
    }

    while True:
        try:
            # FIX: Só conectar à Binance se estiver em modo LIVE
            if state.trading_mode != "live":
                await asyncio.sleep(interval_seconds)
                continue

            # Debug persistente: tentativa de conectar
            try:
                dbg = Path("logs/runtime_main_debug.jsonl")
                dbg.parent.mkdir(parents=True, exist_ok=True)
                dbg.open("a", encoding="utf-8").write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "event": "live_user_stream_connect_attempt",
                            "trading_mode": getattr(state, "trading_mode", None),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            except Exception:
                pass

            # SPRINT 11.7: Respeitar o banimento do DataEngine para não estender o tempo na Binance
            if engine._rest_ban_active():
                logger.debug("live_monitor_loop: REST ban ativo, aguardando...")
                await asyncio.sleep(interval_seconds)
                continue

            # SPRINT 11: Obter saldo inicial via REST antes de abrir o stream
            current_balance_snapshot: Dict[str, Any] = state._live_balance
            try:
                acc = await client.futures_account()
                current_balance_snapshot = {
                    "totalWalletBalance": float(acc.get("totalWalletBalance", 0)),
                    "totalMarginBalance": float(acc.get("totalMarginBalance", 0)),
                    "availableBalance": float(acc.get("availableBalance", 0)),
                }
                state.update_live_data(
                    positions=state._live_positions,
                    balance=current_balance_snapshot,
                    api_status={"ok": True, "error": None, "ts": time.time()}
                )
            except Exception as eb:
                logger.debug("Fetch balance inicial falhou: %s", eb)
            
            # SPRINT 11.26: Garante que o estado seja atualizado antes de entrar no loop do socket
            if current_balance_snapshot:
                state.update_live_data(
                    positions=state._live_positions,
                    balance=current_balance_snapshot,
                    api_status={"ok": True, "error": None, "ts": time.time()}
                )

            _socket_cm = bsm.futures_user_socket()
            async with cast(Any, _socket_cm) as stream:
                logger.info("✅ LIVE user-data websocket conectada.")

                # Debug persistente: conectado
                try:
                    dbg = Path("logs/runtime_main_debug.jsonl")
                    dbg.parent.mkdir(parents=True, exist_ok=True)
                    dbg.open("a", encoding="utf-8").write(
                        json.dumps(
                            {
                                "ts": time.time(),
                                "event": "live_user_stream_connected",
                                "trading_mode": getattr(state, "trading_mode", None),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                except Exception:
                    pass

                state.update_live_data(
                    positions=[],
                    balance=current_balance_snapshot, # Use the last known balance
                    api_status={"ok": True, "error": None, "ts": time.time()},
                )

                # FIX BUG 1: Refresh periódico de saldo — stream só emite ACCOUNT_UPDATE em fills,
                # não em oscilações de PnL flutuante. REST a cada 30s mantém saldo e availableBalance atuais.
                _last_rest_bal_refresh: float = time.time()
                _rest_bal_refresh_interval: float = 30.0

                while True:
                    # Timeout garante que PnL e saldo atualizem mesmo sem eventos no stream
                    try:
                        msg = await asyncio.wait_for(stream.recv(), timeout=_rest_bal_refresh_interval)
                    except asyncio.TimeoutError:
                        msg = None
                    except asyncio.CancelledError:
                        return

                    api_status = {"ok": True, "error": None, "ts": time.time()}
                    now_ws = time.time()

                    # Refresh periódico de saldo via REST (captura PnL flutuante + availableBalance real)
                    if (now_ws - _last_rest_bal_refresh) >= _rest_bal_refresh_interval:
                        try:
                            acc = await client.futures_account()
                            current_balance_snapshot = {
                                "totalWalletBalance": float(acc.get("totalWalletBalance", 0)),
                                "totalMarginBalance": float(acc.get("totalMarginBalance", 0)),
                                "availableBalance": float(acc.get("availableBalance", 0)),
                            }
                            _last_rest_bal_refresh = now_ws
                            if sniper.compound_enabled and current_balance_snapshot:
                                sniper.usdt_amount = current_balance_snapshot.get("totalMarginBalance", sniper.usdt_amount)
                            logger.debug("[LIVE] Saldo REST atualizado: %.2f USDT", current_balance_snapshot.get("totalMarginBalance", 0))
                        except Exception as eb:
                            logger.debug("Refresh periódico de saldo falhou: %s", eb)

                    if not msg:
                        # Timeout ou mensagem vazia: sincroniza PnL das posições em cache e atualiza dashboard
                        for sym, pos_data in last_positions.items():
                            curr_p = engine.data.get(sym, {}).get("price")
                            if curr_p and pos_data.get("entry_price"):
                                p_entry = float(pos_data["entry_price"])
                                pos_data["current_price"] = round(curr_p, 8)
                                pos_data["pnl_pct"] = round(((curr_p / p_entry) - 1) * 100 * sniper.leverage, 4)
                        # FIX: Sempre atualiza saldo mesmo sem eventos
                        state.update_live_data(
                            positions=list(last_positions.values()),
                            balance=current_balance_snapshot,
                            api_status=api_status,
                        )
                        continue

                    event = msg.get("e")

                    # SPRINT 12.11: Ignorar ordens manuais e persistir apenas Sniper
                    if event == "ORDER_TRADE_UPDATE":
                        o = msg.get("o", {})
                        client_id = str(o.get("c", ""))
                        if not client_id.startswith("sniper_"):
                            # Ordem manual: atualiza PnL e avisa no Telegram
                            if o.get("x") == "TRADE" and o.get("X") == "FILLED" and telegram:
                                side = "LONG" if float(o.get("pa", 0)) > 0 else "CLOSE/SHORT"
                                asyncio.create_task(telegram._send(f"👤 <b>Ordem Manual Detectada:</b> {o.get('s')} {side} @ {o.get('ap')}"))
                            for sym, pos_data in last_positions.items():
                                curr_p = engine.data.get(sym, {}).get("price")
                                if curr_p and pos_data.get("entry_price"):
                                    p_entry = float(pos_data["entry_price"])
                                    pos_data["current_price"] = round(curr_p, 8)
                                    pos_data["pnl_pct"] = round(((curr_p / p_entry) - 1) * 100 * sniper.leverage, 4)
                            state.update_live_data(
                                positions=list(last_positions.values()),
                                balance=current_balance_snapshot,
                                api_status=api_status,
                            )
                            continue
                            
                        if o.get("x") == "TRADE" and o.get("X") == "FILLED":
                            rp = _safe_float(o.get("rp", 0.0), 0.0)
                            symbol = o.get("s")
                            price = _safe_float(o.get("ap"), 0.0)
                            
                            # SPRINT 12.115: Certeza absoluta no Telegram OPEN/CLOSED para LIVE
                            if telegram:
                                if rp != 0: # Fechamento (Lucro Realizado detectado)
                                    reason = "TP/SL Server-side" if o.get("ot") in ["STOP_MARKET", "TAKE_PROFIT_MARKET"] else "Sniper/Manual"
                                    asyncio.create_task(telegram._send(f"✅ <b>LIVE CLOSED:</b> {symbol}\nPreço: {price}\nPnL: ${rp:.2f}\nMotivo: {reason}"))
                                else: # Abertura
                                    asyncio.create_task(telegram._send(f"🚀 <b>LIVE OPEN:</b> {symbol}\nPreço: {price}\nModo: Sniper DNA"))

                            if rp != 0:
                                trade_record = {
                                    "id": f"live-{o.get('i')}-{int(time.time())}",
                                    "symbol": symbol,
                                    "status": "closed",
                                    "size": _safe_float(o.get("q"), 0.0),
                                    "pnl_usdt": rp,
                                    "fee_exit": _safe_float(o.get("n"), 0.0),
                                    "exit": {
                                        "time": time.time(),
                                        "price": _safe_float(o.get("ap"), 0.0),
                                        "reason": "tp_sl_server_side" if o.get("ot") in ["STOP_MARKET", "TAKE_PROFIT_MARKET"] else "manual_market"
                                    }
                                }
                                try:
                                    with state.cfg.live_closed_jsonl.open("a", encoding="utf-8") as f:
                                        f.write(json.dumps(trade_record) + "\n")
                                    recent = getattr(state, "_live_closed_recent", [])
                                    recent.insert(0, trade_record)
                                    setattr(state, "_live_closed_recent", recent[:20])
                                except Exception as e:
                                    logger.error("Erro ao persistir trade live: %s", e)

                    # FIX BUG 1: Só processa balanço/posição para ACCOUNT_UPDATE
                    # ACCOUNT_UPDATE emitido pela Binance ao abrir/fechar posições e receber funding
                    if event == "ACCOUNT_UPDATE":
                        data = msg.get("a") or {}
                        balance_updates = data.get("B") or []

                        if balance_updates:
                            for bal_entry in balance_updates:
                                if bal_entry.get("a") == "USDT":
                                    current_balance_snapshot = {
                                        "totalWalletBalance": float(bal_entry.get("wb", 0)),
                                        "totalMarginBalance": float(bal_entry.get("mb", 0)),
                                        "availableBalance": float(bal_entry.get("aw", 0)),
                                    }
                                    break
                            if sniper.compound_enabled and current_balance_snapshot:
                                # BUG FIX: Garante que o Sniper use o saldo real para cálculo de Kelly/Sizing
                                new_bal = current_balance_snapshot.get("totalMarginBalance")
                                if new_bal:
                                    sniper.usdt_amount = float(new_bal)
                                    state._live_balance["totalMarginBalance"] = float(new_bal)

                        pos_updates = data.get("P") or []
                        next_positions: Dict[str, Dict[str, Any]] = {}

                        for p in pos_updates:
                            sym = p.get("s") or p.get("symbol")
                            if not sym:
                                continue

                            amt = _safe_float(p.get("pa") or p.get("positionAmt"), 0.0)
                            if abs(amt) <= 0:
                                continue

                            entry_price = p.get("ep") or p.get("entryPrice") or None
                            try:
                                entry_price_f = float(entry_price) if entry_price is not None else None
                            except Exception:
                                entry_price_f = None

                            unrealized = p.get("up") or p.get("unRealizedProfit") or None
                            try:
                                unrealized_f = float(unrealized) if unrealized is not None else None
                            except Exception:
                                unrealized_f = None

                            side = "LONG" if amt > 0 else "SHORT"
                            qty = abs(amt)

                            current_p_raw = state.market_data.get(sym, {}).get("price") or entry_price_f
                            current_p = float(current_p_raw) if current_p_raw is not None else 0.0

                            active_lev = sniper.leverage
                            pnl_pct = round(((current_p / entry_price_f) - 1) * 100 * active_lev, 4) if (current_p > 0 and entry_price_f) else 0.0
                            notional = round(qty * current_p, 8) if current_p > 0 else None
                            fee_entry_sim = round(qty * entry_price_f * state.cfg.fee_pct, 8) if entry_price_f else 0.0
                            fee_exit_sim = round(qty * current_p * state.cfg.fee_pct, 8) if current_p > 0 else 0.0
                            expected = getattr(state, "_live_expected_prices", {}).get(sym)
                            fee_total = fee_entry_sim + fee_exit_sim
                            pnl_net_usdt = (unrealized_f - fee_total) if unrealized_f is not None else None

                            next_positions[sym] = {
                                "symbol": sym,
                                "status": "open",
                                "side": side,
                                "entry_price": round(entry_price_f, 8) if entry_price_f else None,
                                "expected_price": expected,
                                "current_price": round(current_p, 8),
                                "size": qty,
                                "notional_usdt": notional,
                                "usdt_margin": round((notional or 0.0) / active_lev, 8) if notional else None,
                                "leverage": active_lev,
                                "fee_entry": fee_entry_sim,
                                "fee_exit": fee_exit_sim,
                                "pnl_pct": pnl_pct,
                                "pnl_usdt": unrealized_f,
                                "pnl_net_usdt": pnl_net_usdt,
                                "funding_rate": state.market_data.get(sym, {}).get("funding_rate"),
                                "mfe_pct": None,
                                "mae_pct": None,
                                "sl_price": None,
                                "tp_price": None,
                                "duration_sec": None,
                                "quality": None,
                            }

                        last_positions.update(next_positions)

                    # Sincroniza PnL flutuante via DataEngine para todas as posições (roda a cada evento)
                    for sym, pos_data in last_positions.items():
                        curr_p = engine.data.get(sym, {}).get("price")
                        if curr_p and pos_data.get("entry_price"):
                            p_entry = float(pos_data["entry_price"])
                            pos_data["current_price"] = round(curr_p, 8)
                            pos_data["pnl_pct"] = round(((curr_p / p_entry) - 1) * 100 * sniper.leverage, 4)

                    state.update_live_data(
                        positions=[p for p in last_positions.values() if abs(p.get("size", 0)) > 0],
                        balance=current_balance_snapshot,
                        api_status=api_status,
                    )

        except asyncio.CancelledError:
            return
        except Exception as e:
            # SPRINT 11.8: Sincroniza o estado de banimento global para evitar extensão da punição
            engine._maybe_set_rest_ban_from_exception(e)
            err_s = str(e)
            logger.warning("⚠️ live_monitor_loop user-stream erro: %s", err_s)
            state.update_live_data(
                positions=[],
                balance={},
                api_status={"ok": False, "error": err_s, "ts": time.time()},
            )
            # backoff simples (user-stream: se falhar por -1003, não dá pra martelar)
            await asyncio.sleep(max(10, interval_seconds))

async def _daily_reset_loop(engine: DataEngine, state: BotState) -> None:
    """Executa reset exato às 00:00 UTC. Previne contaminação de slopes."""
    log_dr = logging.getLogger("DailyReset")

    while True:
        now_utc = datetime.now(timezone.utc)
        next_midnight = (now_utc + timedelta(days=1)).replace(
            hour=0, minute=0, second=10, microsecond=0
        )
        wait = (next_midnight - now_utc).total_seconds()
        log_dr.info("⏰ Reset diário em %.0fmin (00:00 UTC = 21:00 BRT)", wait/60)
        await asyncio.sleep(wait)

        try:
            if hasattr(engine, "store") and engine.store:
                if hasattr(engine.store, "reset_daily_history"):
                    engine.store.reset_daily_history()
            
            # Forçar re-warmup de 5 minutos para estabilizar os slopes (Roadmap 12.3)
            state.restart_warmup(300.0)
            state.daily_reset_active = True
            
            if hasattr(engine, "store") and engine.store:
                if hasattr(engine.store, "save_state"):
                    engine.store.save_state()
                    
            log_dr.info("✅ Reset diário concluído — warmup de 5min ativado")
            await asyncio.sleep(310)
            state.daily_reset_active = False
        except Exception as e:
            log_dr.error("Erro no reset diário: %s", e)


async def heartbeat(engine: DataEngine, signals: SqueezeIgnition, state: BotState) -> None:
    """Log periódico — confirma que o processo não travou."""
    await asyncio.sleep(15)
    while True:
        try:
            hb = Path("logs/heartbeat_debug.jsonl")
            hb.parent.mkdir(parents=True, exist_ok=True)
            hb.open("a", encoding="utf-8").write(
                json.dumps(
                    {
                        "ts": time.time(),
                        "event": "heartbeat_tick",
                        "symbol_count": len(engine.symbols),
                        "trading_mode": getattr(engine, "trading_mode", None),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        except Exception:
            pass

        with_price = sum(
            1 for s in engine.symbols if (engine.data.get(s, {}).get("price") or 0) > 0
        )
        with_oi = sum(
            1 for s in engine.symbols if (engine.data.get(s, {}).get("oi") or 0) > 0
        )
        with_trend = sum(
            1 for s in engine.symbols if engine.data.get(s, {}).get("oi_trend:5m") is not None
        )
        
        # DNA Sniper: Auditoria de saúde para os top ativos
        if engine.store:
            for s in engine.symbols[:10]:
                engine.store.log_data_gaps(s)
        
        # DNA Sniper P3: Telemetria do Cache
        c_stats = state.get_score_stats()
        if c_stats["total"] > 0:
            logger.info("⚡ CPU Guard: Cache Score Hit Rate %.1f%% (%d hits)", c_stats["hit_rate_pct"], c_stats["hits"])
        
        # SPRINT 12.1: Visibilidade de Sinais Bloqueados
        ref_stats = signals.get_refusal_stats()
        top_r = " | ".join([f"{k}:{v}" for k, v in ref_stats["top_motivos"].items()])

        logger.info(
            "💓 ativo | preço %s/%s | OI %s | trends %s | Ctrl+C para parar",
            with_price,
            len(engine.symbols),
            with_oi,
            with_trend,
        )
        logger.info(
            "🛡️ DNA BLOCKER (1h): %d sinais | Top: %s",
            ref_stats["total_blocked"], top_r
        )
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            return


def _kill_process_tree() -> None:
    """Mata o processo atual e todos os filhos (árvore completa) via taskkill do Windows.
    Garante que nenhum subprocesso do bot sobreviva após o encerramento.
    """
    import subprocess
    pid = os.getpid()
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    # Fallback: se taskkill falhar (ex: Linux/Mac), força saída dura
    os._exit(0)


async def _shutdown(
    engine: DataEngine,
    engine_task: Optional[asyncio.Task[Any]],
    tasks: List[asyncio.Task[Any]],
) -> None:
    # SPRINT 11.25: Ordem de encerramento rigorosa para evitar AssertionError no WebSocket
    logger.info("Encerrando bot (limpeza de conexões)...")
    engine.running = False
    
    try:
        # Primeiro paramos o engine (WebSockets da Binance)
        await asyncio.wait_for(engine.stop(), timeout=5.0)
    except Exception:
        pass

    with contextlib.suppress(asyncio.CancelledError, Exception):
        for t in tasks:
            if t: t.cancel()
        if engine_task:
            engine_task.cancel()

        # SPRINT 11.2: Filtragem de None para evitar "None is not awaitable"
        gather_list = [t for t in tasks if t is not None]
        if engine_task:
            gather_list.append(engine_task)
        if gather_list:
            # SPRINT 11.3: Cast explícito para Any evita que o Pylance confunda Tasks com KeepAliveWebsocket
            await asyncio.gather(*cast(List[Any], gather_list), return_exceptions=True)


async def run_terminal_dashboard(engine: DataEngine) -> None:
    ui = Dashboard()
    with Live(ui.render(engine.data), refresh_per_second=1) as live:
        while True:
            live.update(ui.render(engine.data))
            await asyncio.sleep(1)


def _is_port_in_use(host: str, port: int) -> bool:
    """
    Checagem robusta em Windows: tenta BIND em (host,port).
    Se já estiver ocupado por outro listener, levanta EADDRINUSE/WSAEADDRINUSE.
    """
    # Força loopback local para evitar falsos positivos quando host vem como 0.0.0.0
    if host == "0.0.0.0":
        host = "127.0.0.1"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Evita que TIME_WAIT cause falso positivo
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
    except OSError:
        return True


async def _validate_live_account(client: AsyncClient, min_balance: float) -> bool:
    """Valida se a conta tem permissão de trade e saldo suficiente."""
    try:
        acc = await client.futures_account()
        if not acc.get("canTrade"):
            logger.critical("❌ [SEGURANÇA] Conta Binance SEM permissão para trading de futuros!")
            return False
        
        balance = float(acc.get("totalMarginBalance", 0))
        if balance < min_balance:
            logger.critical(
                "❌ [SEGURANÇA] Saldo insuficiente para LIVE: %.2f USDT (mínimo %.2f USDT)",
                balance, min_balance
            )
            return False
            
        logger.info("✅ [SEGURANÇA] Conta LIVE validada: canTrade=True, balance=%.2f USDT", balance)
        return True
    except Exception as e:
        logger.critical("❌ [SEGURANÇA] Falha crítica ao validar conta LIVE: %s", e)
        return False

async def _get_public_ip() -> str:
    """Detecta o IP público atual para auxiliar no Whitelisting da Binance."""
    try:
        # Timeout curto para não travar o bot se o serviço de IP estiver fora
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org?format=json", timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                data = await resp.json()
                return data.get("ip", "unknown")
    except Exception:
        return "IP não detectado"

async def ip_drift_guard_loop(state: BotState, telegram: Optional[TelegramAlert], interval_minutes: int = 10):
    """
    SPRINT 11.17: Monitora mudanças no IP público durante a execução.
    Avisa o operador se o IP mudar para evitar rejeições da Binance em modo LIVE.
    """
    startup_ip = await _get_public_ip()
    logger.info("🛡️ IP Guard iniciado. Monitorando mudanças a partir de: %s", startup_ip)
    
    while True:
        await asyncio.sleep(interval_minutes * 60)
        current_ip = await _get_public_ip()
        
        if current_ip != "IP não detectado" and current_ip != startup_ip:
            msg = (
                f"🚨 <b>ALERTA DE SEGURANÇA: MUDANÇA DE IP</b>\n"
                f"Seu IP público mudou de <code>{startup_ip}</code> para <code>{current_ip}</code>.\n"
                f"<b>AÇÃO NECESSÁRIA:</b> Atualize a Whitelist da sua API na Binance agora!"
            )
            logger.critical("⚠️ [SEGURANÇA] IP MUDOU! De %s para %s. Atualize a Binance!", startup_ip, current_ip)
            
            if telegram:
                await telegram._send(msg)
            
            # Atualiza o IP de referência para não repetir o alerta incessantemente
            startup_ip = current_ip


def _apply_runtime_mode(
    mode: ModeName,
    *,
    persist: bool,
    prefs_path: Path,
    state: BotState,
    sniper: Sniper,
    signal_engine: SqueezeIgnition,
    cfg: BotConfig,
    paper_tracker: Optional[PaperTradeTracker],
) -> Dict[str, Any]:
    mode_val = str(mode).strip().lower()
    if mode_val not in {"paper", "live"}:
        return {"ok": False, "error": "invalid mode"}
    mode = cast(ModeName, mode_val)

    prefs = load_preferences(prefs_path)
    mode_node = get_mode_node(prefs, mode)
    exec_node = get_mode_execution(prefs, mode)
    signal_node = get_mode_signal(prefs, mode)

    state.trading_mode = mode
    state.bind_sniper(sniper)
    sniper.trading_mode = mode

    if mode == "paper":
        if paper_tracker is None:
            return {"ok": False, "error": "paper tracker not configured"}
        sniper.usdt_amount = float(getattr(paper_tracker, "usdt_amount", 0.0))
        sniper.leverage = int(mode_node.get("leverage", paper_tracker.config.leverage))
        sniper.risk_pct_per_trade = float(mode_node.get("risk_pct_per_trade", paper_tracker.risk_pct_per_trade))
        sniper.max_open_positions = int(mode_node.get("max_open_positions", paper_tracker.config.max_open_positions))
        sniper.compound_enabled = False
    else:  # mode == "live"
        sniper.usdt_amount = float(mode_node.get("usdt_amount", cfg.usdt_amount))
        sniper.leverage = int(mode_node.get("leverage", cfg.leverage))
        sniper.risk_pct_per_trade = float(mode_node.get("risk_pct_per_trade", cfg.risk_pct_per_trade))
        sniper.max_open_positions = int(mode_node.get("max_open_positions", cfg.live_max_open_positions))
        sniper.compound_enabled = bool(mode_node.get("compound_enabled", False))

    sniper.sl_pct = float(exec_node.get("sl_pct", cfg.sl_pct))
    sniper.tp_pct = float(exec_node.get("tp_pct", cfg.tp_pct))
    sniper.max_hold_seconds = int(exec_node.get("max_hold_seconds", 0))
    sniper.sl_trailing_swing_low = bool(exec_node.get("sl_trailing_swing_low", True))
    sniper.auto_pilot = bool(mode_node.get("auto_pilot", False))
    sniper.kelly_enabled = bool(exec_node.get("kelly_enabled", False))
    setattr(state, "compound_enabled", bool(getattr(sniper, "compound_enabled", False)))  # Sincroniza estado para o dashboard

    signal_engine.refresh_thresholds(
        signal_mode=str(signal_node.get("signal_mode", "conservative")),
        min_cvd_change_pct=float(signal_node.get("min_cvd_change_pct", cfg.min_cvd_change_pct)),
        cvd_streak_min=int(signal_node.get("cvd_streak_min", cfg.cvd_streak_min)),
        max_bid_ask_spread=float(signal_node.get("max_bid_ask_spread", cfg.max_bid_ask_spread)),
        min_trades_1m=int(signal_node.get("min_trades_1m", cfg.min_trades_1m)),
        min_vol_adaptive_ratio=float(signal_node.get("min_vol_adaptive_ratio", cfg.min_vol_adaptive_ratio)),
        min_oi_accel=float(signal_node.get("min_oi_accel", cfg.min_oi_accel)),
        min_oi_change_pct=float(signal_node.get("min_oi_change_pct", cfg.min_oi_change_pct)),
        max_lsr_change_pct=float(signal_node.get("max_lsr_change_pct", cfg.max_lsr_change_pct)),
        min_oi_trend=float(signal_node.get("min_oi_trend", cfg.min_oi_trend)),
        blacklist=list(prefs.get("blacklist", [])),
        fit_score_min=float(prefs.get("fit_score_min", cfg.fit_score_min)),
        min_cvd_change_pct_no_cascade=float(signal_node.get("min_cvd_change_pct_no_cascade", 1.0)),
    )

    if persist:
        prefs["trading_mode"] = mode  # Persiste o último modo ativo para reidratação da UI
        _save_prefs(prefs)

    logger.info(
        "✅ runtime mode=%s | usdt=%.2f lev=%d risk=%.2f%% sl=%.2f%% tp=%.2f%% max_pos=%d | compound=%s",
        mode,
        sniper.usdt_amount,
        sniper.leverage,
        sniper.risk_pct_per_trade * 100.0,
        sniper.sl_pct * 100.0,
        sniper.tp_pct * 100.0,
        sniper.max_open_positions,
        "ON" if sniper.compound_enabled else "OFF",
    )
    return {"ok": True, "mode": mode}


async def main():
    # SPRINT 11.2: Inicialização explícita para evitar UnboundLocalError e avisos de tipo
    engine_task: Optional[asyncio.Task[Any]] = None
    tasks: List[asyncio.Task[Any]] = []
    engine_client: Optional[AsyncClient] = None
    live_tracker: Optional[LiveTracker] = None  # AUDITORIA 2026-06-01: Declaração explícita

    # SPRINT 12.118: Define base_dir no topo para evitar Erro 1, 2 e 3 (Possibly Unbound)
    base_dir = Path(__file__).resolve().parent

    # Debug: registrar CWD e arquivo executado para garantir que estamos rodando a versão correta.
    try:
        debug_path = base_dir / "logs/runtime_main_debug.jsonl"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.open("a", encoding="utf-8").write(
            json.dumps(
                {
                    "ts": time.time(),
                    "event": "main_started",
                    "cwd": os.getcwd(),
                    "main_file": str(Path(__file__).resolve()),
                    "python_executable": sys.executable,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    except Exception:
        pass

    # ---- AVISO: Arquivo de Preferências Oficial ----
    # AUDITORIA 2026-05-31: Informa qual arquivo está sendo usado
    try:
        prefs_file = resolve_preferences_path()
        logger.info("=" * 80)
        logger.info("📋 ARQUIVO DE PREFERÊNCIAS ATIVO: %s", prefs_file.name)
        logger.info("⚠️  IMPORTANTE: Mudanças via Dashboard salvam neste arquivo!")
        logger.info("⚠️  Edições manuais devem ser feitas em: %s", prefs_file)
        logger.info("=" * 80)
    except Exception as e:
        logger.warning("Não foi possível determinar arquivo de preferências: %s", e)

    # ---- Guard: obrigar execução dentro do venv (.venv) ----
    # Se o processo foi iniciado sem o `.venv` (ex.: VSCode Code Runner), reexecuta automaticamente
    # para você não ter que trocar o interpretador manualmente.
    try:
        venv_root = (base_dir / ".venv").resolve()
        exe_path = Path(sys.executable).resolve()

        if venv_root.exists() and (venv_root not in exe_path.parents):
            if os.name == "nt":
                venv_python = venv_root / "Scripts" / "python.exe"
            else:
                venv_python = venv_root / "bin" / "python"

            if venv_python.exists():
                # SPRINT 12.106: Resolve o caminho absoluto do script para evitar erros com o '#' no path
                script_path = Path(__file__).resolve()
                cmd = [str(venv_python), str(script_path), *sys.argv[1:]]
                
                import subprocess

                pretty = " ".join(map(str, cmd))

                logger.warning(
                    "[-] Execução fora do .venv detectada. Reexecutando com: %s",
                    str(venv_python),
                )
                # Garantir que aparece mesmo quando o logger não renderiza bem no Output do VSCode
                print(f"\n[venv guard] Reexecutando no .venv com:\n  {pretty}\n", flush=True)

                # SPRINT 12.105: Bloqueia o processo pai e propaga o código de saída do venv
                result = subprocess.run(cmd, cwd=str(base_dir))
                sys.exit(result.returncode)

            logger.error(
                "[-] Deve rodar dentro do venv (.venv), mas python do venv não foi encontrado em: %s",
                str(venv_python),
            )
            print(
                f"\n[venv guard] Python do .venv não encontrado em: {venv_python}\n"
                "Selecione o interpretador do .venv no VSCode ou rode manualmente:\n"
                "  .venv/Scripts/python.exe main.py\n",
                flush=True,
            )
            return
    except Exception:
        # Se falhar o check, não bloqueia (melhor rodar do que quebrar por path estranho)
        pass

    _lock_acquired, _lock_pid = _acquire_instance_lock()
    if not _lock_acquired:
        logger.warning("🧷 Outro processo já está rodando (pid=%s). Abortando para evitar paralelismo/bans.", _lock_pid)
        return

    # --- Gerenciamento de Sinais ---
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    stop_requested = False

    def _on_signal():
        nonlocal stop_requested
        if stop_requested:
            return
        stop_requested = True
        logger.info("🛑 Sinal de parada recebido!")
        loop.call_soon_threadsafe(stop_event.set)

    # No Windows, signals são limitados, mas o Ctrl+C (SIGINT) funciona
    # Se estiver no Windows, add_signal_handler pode falhar.
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _on_signal)
            except NotImplementedError:
                pass
    else:
        # No Windows, usamos signal.signal para SIGINT
        signal.signal(signal.SIGINT, lambda s, f: _on_signal())
        signal.signal(signal.SIGTERM, lambda s, f: _on_signal())

    prefs_path = resolve_preferences_path()
    prefs = load_preferences(prefs_path)
    cfg = load_config(prefs_path)

    dash_cfg = prefs.get("dashboard") or {}
    log_cfg = prefs.get("logging") or {}
    dash_enabled = bool(dash_cfg.get("enabled", True))
    terminal_fallback = bool(dash_cfg.get("terminal_fallback", False))
    # SPRINT 6.47: 127.0.0.1 é mais estável para WebSockets no Windows local
    dash_host = str(dash_cfg.get("host", "127.0.0.1"))
    dash_port = int(dash_cfg.get("port", 8765))
    auto_open = bool(dash_cfg.get("auto_open_browser", True))

    logger.info(
        "Prefs: %s | modo=%s | top_n=%s | dashboard=%s",
        prefs_path.name,
        prefs.get("trading_mode", "paper"), # Mostra o modo salvo no preferences
        cfg.top_n,
        "web" if dash_enabled else "off",
    )

    exchange_info_cache_path = Path("logs/exchange_info_cache.json")
    exchange_info_cache_max_age_seconds = 60 * 60 * 6  # 6h

    info = None
    used_fallback_symbols = False

    try:
        if exchange_info_cache_path.exists():
            age = time.time() - exchange_info_cache_path.stat().st_mtime
            if age <= exchange_info_cache_max_age_seconds:
                info = json.loads(exchange_info_cache_path.read_text(encoding="utf-8"))
                logger.info(
                    "📦 Usando cache de exchangeInfo (idade: %.0fs) — evitando REST call",
                    age,
                )
    except Exception:
        info = None

    # Se exchangeInfo REST falhar (ex: IP ban), caímos para logs/metric_state.json
    if info is None:
        try:
            temp_client = await AsyncClient.create(
                api_key=cfg.api_key,
                api_secret=cfg.api_secret,
            )
            try:
                logger.info("🔍 Buscando símbolos de Futures (REST)...")
                info = await temp_client.futures_exchange_info()
                exchange_info_cache_path.parent.mkdir(parents=True, exist_ok=True)
                exchange_info_cache_path.write_text(
                    json.dumps(info, ensure_ascii=False), encoding="utf-8"
                )
            finally:
                await temp_client.close_connection()
        except Exception as e:
            logger.warning(
                "⚠️ exchangeInfo REST falhou (%s). Usando fallback via logs/metric_state.json.",
                str(e),
            )
            used_fallback_symbols = True

    if used_fallback_symbols or info is None:
        try:
            metric_state = json.loads(
                Path("logs/metric_state.json").read_text(encoding="utf-8")
            )
            data = metric_state.get("data") or {}
            metric_symbols = list(data.keys())

            # garante macros essenciais
            for macro in ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]:
                if macro not in metric_symbols:
                    metric_symbols.append(macro)

            # limita tamanho parecido com top_n, mantendo macros
            non_macros = [s for s in metric_symbols if s not in ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]]
            limited_non_macros = non_macros[: max(0, cfg.top_n - 3)]
            all_symbols = ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"] + limited_non_macros
            sym_stats = {"total": len(all_symbols), "usdt": len(all_symbols)}
        except Exception as e:
            logger.error("❌ Fallback de símbolos falhou: %s", str(e))
            return
    else:
        all_symbols, sym_stats = list_usdt_perpetual_symbols(info)

    logger.info(
        "✅ Usando %s símbolos (top_n=%s) para o engine.",
        len(all_symbols),
        cfg.top_n,
    )

    engine = DataEngine(
        all_symbols,
        top_n=cfg.top_n,
        exchange_info=info,
        api_key=cfg.api_key,
        api_secret=cfg.api_secret,
        oi_poll_seconds=cfg.oi_poll_seconds,
        skip_ticker_filter=False,
        skip_bootstrap_prices=False,
        volume_24h_refresh_seconds=3600.0,
    )
    # SPRINT 12.85: SignalEngine é inicializado com defaults do config.py,
    # mas será atualizado pelo _apply_runtime_mode
    signal_engine = SqueezeIgnition(
        min_exp=cfg.min_exp,
        min_oi_trend=cfg.min_oi_trend,
        max_lsr_trend=cfg.max_lsr_trend,
        min_vol_1m=cfg.min_vol_1m,
        min_rsi_5m=cfg.min_rsi_5m,
        mtf_1h_crash_threshold=cfg.mtf_1h_crash_threshold,
        min_exp_btc_for_btc_dump=cfg.min_exp_btc_for_btc_dump,
        min_cvd_change_pct=cfg.min_cvd_change_pct,
        min_oi_change_pct=cfg.min_oi_change_pct,
        max_lsr_change_pct=cfg.max_lsr_change_pct,
        cvd_streak_min=cfg.cvd_streak_min,
        min_trades_1m=cfg.min_trades_1m,
        min_vol_adaptive_ratio=cfg.min_vol_adaptive_ratio,
        cooldown_seconds=cfg.signal_cooldown_seconds,
        fit_score_min=cfg.fit_score_min,
        blacklist=cfg.blacklist,
        signal_mode=cfg.signal_mode,
        min_cvd_change_pct_no_cascade=1.0,
    )
    journal = SignalJournal(log_cfg.get("signals_jsonl", "logs/signals.jsonl"))
    
    telegram = None
    if cfg.telegram_token and cfg.telegram_chat_id:
        telegram = TelegramAlert(cfg.telegram_token, cfg.telegram_chat_id)
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
            with Path("logs/telegram_wiring_debug.jsonl").open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "event": "telegram_instantiated",
                            "enabled": bool(getattr(telegram, "enabled", None)),
                            "has_token": bool(getattr(telegram, "token", None)),
                            "has_chat_id": bool(getattr(telegram, "chat_id", None)),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            pass

    paper_cfg_raw = prefs.get("paper") or {}
    paper_tracker = None
    if paper_cfg_raw.get("enabled", True):
        paper_tracker = PaperTradeTracker(
            PaperConfig(
                json_path=Path(paper_cfg_raw.get("json_path", "logs/paper_opportunities.json")),  # type: ignore
                csv_path=Path(paper_cfg_raw.get("csv_path", "logs/paper_opportunities.csv")),
                closed_jsonl=Path(
                    paper_cfg_raw.get("closed_jsonl", "logs/paper_closed.jsonl")
                ),
                update_seconds=float(paper_cfg_raw.get("update_seconds", 1)),
                max_open_per_symbol=int(paper_cfg_raw.get("max_open_per_symbol", 1)),
                min_hold_seconds=int(paper_cfg_raw.get("execution", {}).get("min_hold_seconds", 0)),
                max_hold_seconds=int(paper_cfg_raw.get("execution", {}).get("max_hold_seconds", 0)),
                leverage=int(paper_cfg_raw.get("leverage", cfg.leverage)),
                sl_pct=cfg.sl_pct,
                tp_pct=cfg.tp_pct,
                initial_capital=float(paper_cfg_raw.get("initial_capital", cfg.initial_capital)),
                risk_pct_per_trade=float(paper_cfg_raw.get("risk_pct_per_trade", cfg.risk_pct_per_trade)),
                sl_decay_interval_minutes=cfg.sl_decay_interval_minutes,
                sl_decay_step_pct=cfg.sl_decay_step_pct,
                partial_tp_breakeven_pct=cfg.partial_tp_breakeven_pct,
                sl_trailing_swing_low=cfg.sl_trailing_swing_low,
                swing_low_tf=cfg.swing_low_tf,
                max_open_positions=int(paper_cfg_raw.get("max_open_positions", cfg.paper_max_open_positions)),
                slippage_pct=float(paper_cfg_raw.get("slippage_pct", 0.05)),
                trailing_activation_delay_sec=int(paper_cfg_raw.get("execution", {}).get("trailing_activation_delay_sec", 30)),
                trailing_stop_callback=float(paper_cfg_raw.get("execution", {}).get("trailing_stop_callback", 0.6)),
            ),
            telegram=telegram,
        )
        logger.info("📝 Configurações PAPER carregadas: Capital=%.2f, Leverage=%d, Risk=%.2f%%, MaxPos=%d",
                    paper_tracker.initial_capital,
                    paper_tracker.config.leverage,
                    paper_tracker.risk_pct_per_trade * 100,
                    paper_tracker.config.max_open_positions)

    # SPRINT 12.20: Inicializar LiveTracker para rastrear trades LIVE com funding fees, comissões, PnL real
    live_tracker = LiveTracker(
        LiveConfig(
            json_path=Path(getattr(cfg, "live_opportunities_json", "logs/live_opportunities.json")),
            csv_path=Path(getattr(cfg, "live_opportunities_csv", "logs/live_opportunities.csv")),
            closed_jsonl=Path(cfg.live_closed_jsonl),
            leverage=cfg.leverage,
            sl_pct=cfg.sl_pct,
            tp_pct=cfg.tp_pct,
            initial_capital=cfg.initial_capital,
            # DNA do Sniper
            max_open_positions=cfg.live_max_open_positions,
            max_notional_usdt=getattr(cfg, "max_notional_usdt", 500.0),
            min_hold_seconds=int(prefs.get("live", {}).get("execution", {}).get("min_hold_seconds", 0)),
            max_hold_seconds=int(prefs.get("live", {}).get("execution", {}).get("max_hold_seconds", 0)),
            risk_pct_per_trade=cfg.risk_pct_per_trade,
            sl_trailing_swing_low=cfg.sl_trailing_swing_low if hasattr(cfg, 'sl_trailing_swing_low') else False,
            swing_low_tf=cfg.swing_low_tf if hasattr(cfg, 'swing_low_tf') else "5m",
            partial_tp_breakeven_pct=cfg.partial_tp_breakeven_pct if hasattr(cfg, 'partial_tp_breakeven_pct') else 0.0,
            sl_decay_interval_minutes=cfg.sl_decay_interval_minutes if hasattr(cfg, 'sl_decay_interval_minutes') else 0,
            sl_decay_step_pct=cfg.sl_decay_step_pct if hasattr(cfg, 'sl_decay_step_pct') else 0.0,
            slippage_pct=float(prefs.get("live", {}).get("slippage_pct", 0.05)),
            trailing_activation_delay_sec=int(prefs.get("live", {}).get("execution", {}).get("trailing_activation_delay_sec", 30)),
            trailing_stop_callback=float(prefs.get("live", {}).get("execution", {}).get("trailing_stop_callback", 0.6)),
        )
    )

    state = BotState(
        cfg,
        signal_thresholds={
            "min_exp": cfg.min_exp,
            "min_oi_trend": cfg.min_oi_trend,
            "max_lsr_trend": cfg.max_lsr_trend,
        },
        # SPRINT 12.116: Resolvido Erro 4 do Pyright
        liq_history_path=cfg.liq_history_path, # SPRINT 12.116: Passa o path para persistência do histórico de liquidações
    )

    # SPRINT 12.18: Inicializa estado do Compound no BotState para o Dashboard
    # Garante que o valor persistido no preferences.json chegue ao front no boot.
    live_p = prefs.get("live", {})
    setattr(state, "compound_enabled", bool(live_p.get("compound_enabled", False)))

    # SPRINT 11.34: Inicialização de armazenamento dinâmico para evitar erros de acesso no monitor LIVE
    setattr(state, "_live_expected_prices", {})
    
    # SPRINT 12.116: Carrega histórico de liquidações ao iniciar
    state.load_liquidation_history() # Resolvido Erro 5 do Pyright

    # SPRINT 12.10: Restaurar histórico LIVE do disco para o Dashboard
    live_history = []
    live_log = Path(cfg.live_closed_jsonl)
    if live_log.exists():
        try:
            with live_log.open("r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-20:]: # Pega os últimos 20
                    try:
                        live_history.insert(0, json.loads(line))
                    except: continue
            logger.info("re-hidratado %d trades LIVE do histórico local.", len(live_history))
        except Exception as e:
            logger.warning("Falha ao carregar histórico LIVE: %s", e)
    setattr(state, "_live_closed_recent", live_history)

    # SPRINT 12.40: Protocolo de Segurança - Iniciar SEMPRE em PAPER.
    # Mesmo que o preferences.json aponte para 'live', o bot aguarda o mando do operador via dashboard.
    state.trading_mode = "paper"
    logger.info("🛡️ [SEGURANÇA] Sistema iniciado em modo PAPER. Aguardando comando via Dashboard para LIVE.")
    
    # SPRINT 11.16: Diagnóstico de Segurança de Rede (Visibilidade Crítica)
    public_ip = await _get_public_ip()
    logger.warning("🌐 [SEGURANÇA] Seu IP Público detectado: %s", public_ip)
    logger.warning("🛡️  [AÇÃO OBRIGATÓRIA] Para evitar hacks, use este IP na Whitelist da sua API na Binance.")
    logger.warning("🛡️  [DICA] Ative 'Restrict access to trusted IPs only' para inutilizar suas chaves caso o .env vaze.")

    # SPRINT 11.20: Warmup de Segurança (DNA Sniper)
    # 300s (5m) garante que os slopes de 5m tenham 30 amostras reais antes do primeiro tiro.
    # Usar menos que isso faz o bot operar com rastro estatisticamente incompleto.
    warmup_sec = 300.0
    state.restart_warmup(warmup_sec)

    if paper_tracker:
        state.bind_paper_tracker(paper_tracker)

    inflight: set = set()

    engine_task = asyncio.create_task(engine.start())
    await asyncio.sleep(4)
    if engine.client is None:
        logger.error("❌ Falha ao inicializar cliente Binance.")
        engine_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await engine_task
        await engine.stop()
        return
    engine_client = engine.client

    # SPRINT 12.85: Configuração do Sniper e Estado (Ordem Corrigida)
    sniper = Sniper(
        engine.client,
        usdt_amount=cfg.usdt_amount,
        leverage=cfg.leverage,
        risk_pct_per_trade=cfg.risk_pct_per_trade,
        trading_mode="paper",
        max_open_positions=cfg.live_max_open_positions,
        sl_pct=cfg.sl_pct,
        tp_pct=cfg.tp_pct,
        paper_tracker=paper_tracker,
        live_tracker=live_tracker,
        telegram=telegram, # Resolvido Erro 6 do Pyright
        signal_engine=signal_engine, # SPRINT 13: Para throttling de trades
    )

    if info:
        sniper.hydrate_filters(info)
        
    state.bind_sniper(sniper)

    # SPRINT 12.119: BUG #3 Auditoria - Sincroniza estado imediatamente após criação
    _apply_runtime_mode(
        "paper",
        persist=False,
        prefs_path=prefs_path,
        state=state,
        sniper=sniper,
        signal_engine=signal_engine,
        cfg=cfg,
        paper_tracker=paper_tracker,
    )
    logger.info("🛡️ Boot seguro concluído: PAPER ativo, LIVE só por comando explícito.")
    # Garante que o dashboard mostre o saldo real da Binance assim que o bot liga.
    try:
        assert engine_client is not None
        acc_data = await engine_client.futures_account()
        boot_bal = {
            "totalWalletBalance": float(acc_data.get("totalWalletBalance", 0)),
            "totalMarginBalance": float(acc_data.get("totalMarginBalance", 0)),
            "availableBalance": float(acc_data.get("availableBalance", 0)),
        }
        state.update_live_data(positions=[], balance=boot_bal, api_status={"ok": True, "error": None, "ts": time.time()})
        logger.info("💰 Conexão Automática: Capital Binance detectado no boot: %.2f USDT", boot_bal["totalMarginBalance"])
    except Exception as e:
        logger.warning("⚠️ Falha na leitura automática de saldo: %s", e)

    def _on_set_mode(mode: str):
        try:
            raw = mode
            mode = mode.strip().lower()
            logger.info("📣 Dashboard set-mode called raw=%r mode=%s (before state=%s sniper=%s)", raw, mode, getattr(state, "trading_mode", None), getattr(sniper, "trading_mode", None))

            if mode not in ("paper", "live"):
                return {"ok": False, "error": "invalid mode"}

            # P0: 5.1 Validação ao trocar para LIVE via Dashboard
            if mode == "live":
                # Sprint 11 requirement: iniciar em PAPER e só permitir LIVE após warmup de 300s.
                remaining = float(state.get_warmup_remaining() or 0)
                if remaining > 0:
                    remaining_i = int(remaining)
                    logger.warning(
                        "🚫 LIVE bloqueado durante WARMUP: faltam ~%ss (estado em paper).",
                        remaining_i,
                    )
                    return {
                        "ok": False,
                        "error": f"LIVE locked during warmup: wait {remaining_i}s",
                    }

                # Precisamos de um loop para rodar o await
                # Como estamos em uma thread (web_dashboard), usamos run_coroutine_threadsafe
                min_bal = float(getattr(cfg, "min_balance_usdt", 0.0) or 0.0)
                assert engine_client is not None
                future = asyncio.run_coroutine_threadsafe(
                    _validate_live_account(engine_client, min_bal),
                    loop
                )
                # P2 FIX: Timeout para não travar o loop do Dashboard
                if not future.result(timeout=10):
                    logger.warning("🚫 [SEGURANÇA] Troca para LIVE rejeitada: validação falhou.")
                    return {"ok": False, "error": "LIVE validation failed (check logs)"}
            
            # SPRINT 12.85: Usa a função unificada para aplicar o modo
            return _apply_runtime_mode(
                cast(ModeName, mode),
                persist=True,
                prefs_path=prefs_path,
                state=state,
                sniper=sniper,
                signal_engine=signal_engine,
                cfg=cfg,
                paper_tracker=paper_tracker,
            )
        except Exception as e:
            logger.exception("❌ set-mode handler error: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_reset_paper():
        try:
            if paper_tracker is None:
                return {"ok": False, "error": "paper tracker not configured"}

            logger.info(
                "🧹 Dashboard reset-paper called (before open=%s closed=%s)",
                len(getattr(paper_tracker, "_open", {}) or {}),
                len(getattr(paper_tracker, "_closed", []) or []),
            )

            paper_tracker.reset()
            state.reset_signals()

            logger.info(
                "✅ reset-paper done (after open=%s closed=%s)",
                len(getattr(paper_tracker, "_open", {}) or {}),
                len(getattr(paper_tracker, "_closed", []) or []),
            )
            return {"ok": True}
        except Exception as e:
            logger.exception("❌ reset-paper handler error: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_update_paper_settings(cap: float, risk: float, lev: int, m_pos: int):
        """SPRINT 11.28: Unificação de configurações Paper."""
        try:
            if paper_tracker:
                paper_tracker.set_initial_capital(cap)
                paper_tracker.set_risk_pct(risk / 100.0)
                paper_tracker.set_leverage(lev)
                paper_tracker.config.max_open_positions = m_pos
                
                # Persistência no nó 'paper'
                p = load_preferences(prefs_path)
                paper_node = p.setdefault("paper", {})
                paper_node["initial_capital"] = cap
                paper_node["risk_pct_per_trade"] = risk / 100.0
                paper_node["leverage"] = lev
                paper_node["max_open_positions"] = m_pos
                _save_prefs(p)
                
                # Atualiza executor Sniper se o modo for paper
                if state.trading_mode == "paper":
                    _apply_runtime_mode(
                        "paper",
                        persist=False, # Já persistido acima
                        prefs_path=prefs_path,
                        state=state,
                        sniper=sniper,
                        signal_engine=signal_engine,
                        cfg=cfg,
                        paper_tracker=paper_tracker,
                    )
            return {"ok": True}
        except Exception as e: return {"ok": False, "error": str(e)}

    def _on_update_live_settings(amt: float, risk: float, lev: int, m_pos: int):
        """SPRINT 11.28: Unificação de configurações Live."""
        try:
            p = load_preferences(prefs_path)
            live_node = p.setdefault("live", {})
            live_node["usdt_amount"] = amt
            live_node["risk_pct_per_trade"] = risk / 100.0
            live_node["leverage"] = lev
            live_node["max_open_positions"] = m_pos
            _save_prefs(p)

            # SPRINT 11.30: Se estiver em LIVE, atualiza o executor em tempo real
            if state.trading_mode == "live":
                # O capital operacional (amt) nunca pode ser maior que o saldo real detectado
                real_balance = state._live_balance.get("totalMarginBalance", 0)
                # SPRINT 12.85: Usa _apply_runtime_mode para garantir consistência
                _apply_runtime_mode(
                    "live",
                    persist=False, # Já persistido acima
                    prefs_path=prefs_path,
                    state=state,
                    sniper=sniper,
                    signal_engine=signal_engine,
                    cfg=cfg,
                    paper_tracker=paper_tracker,
                )
            return {"ok": True}
        except Exception as e: return {"ok": False, "error": str(e)}

    def _on_update_live_advanced(auto_pilot: bool, sl_pct: float, tp_pct: float, max_hold_min: int, signal_mode: str, trailing_enabled: bool, kelly_enabled: bool = False):
        """SPRINT 12.21: Handler para configurações avançadas LIVE (incluindo AUTO-PILOT)."""
        try:
            p = load_preferences(prefs_path)
            # SPRINT 12.85: Persistência isolada no bloco LIVE
            live_node = p.setdefault("live", {})
            exec_node = live_node.setdefault("execution", {})
            sig_node = live_node.setdefault("signal", {})
            
            # AUTO-PILOT: Salva flag
            live_node["auto_pilot"] = auto_pilot
            
            exec_node["sl_pct"] = sl_pct / 100.0
            exec_node["tp_pct"] = tp_pct / 100.0
            exec_node["max_hold_seconds"] = max_hold_min * 60
            exec_node["sl_trailing_swing_low"] = trailing_enabled
            exec_node["kelly_enabled"] = kelly_enabled
            sig_node["signal_mode"] = signal_mode
            _save_prefs(p)

            # SPRINT 12.122: Feedback visual honesto sobre o Auto-Pilot
            mode_str = "🤖 AUTO-PILOT (ATR Override)" if auto_pilot else "👤 MANUAL"
            
            # Atualiza executor em tempo real se estiver em LIVE
            if state.trading_mode == "live":
                # SPRINT 12.85: Usa _apply_runtime_mode para garantir consistência
                _apply_runtime_mode(
                    "live",
                    persist=False, # Já persistido acima
                    prefs_path=prefs_path,
                    state=state,
                    sniper=sniper,
                    signal_engine=signal_engine,
                    cfg=cfg,
                    paper_tracker=paper_tracker,
                )
            
            logger.info("📝 Configurações LIVE [%s]: SL_Ref=%.2f%%, TP_Ref=%.2f%%, Mode=%s, Kelly=%s",
                        mode_str, sl_pct, tp_pct, signal_mode, kelly_enabled)
            return {"ok": True}
        except Exception as e:
            logger.exception("Erro ao atualizar configurações avançadas LIVE: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_toggle_live_compound(enabled: bool):
        """SPRINT 12.18: Handler para habilitar/desabilitar juros compostos no modo LIVE."""
        try:
            p = load_preferences(prefs_path)
            p.setdefault("live", {})["compound_enabled"] = enabled
            _save_prefs(p)

            # SPRINT 11.30: Se estiver em LIVE, atualiza o executor em tempo real
            if state.trading_mode == "live":
                # SPRINT 12.85: Usa _apply_runtime_mode para garantir consistência
                _apply_runtime_mode(
                    "live",
                    persist=False, # Já persistido acima
                    prefs_path=prefs_path,
                    state=state,
                    sniper=sniper,
                    signal_engine=signal_engine,
                    cfg=cfg,
                    paper_tracker=paper_tracker,
                )
                logger.info("⚙️ Compound Mode alterado para: %s", "ON" if enabled else "OFF")

            return {"ok": True, "compound_enabled": enabled}
        except Exception as e:
            logger.error("❌ Erro ao alternar compound mode: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_hard_reset(deep_clean: bool = False):
        try:
            if paper_tracker is None:
                return {"ok": False, "error": "paper tracker not configured"}

            logger.warning("🔥 HARD RESET iniciado via Dashboard... (deep_clean=%s)", deep_clean)
            
            # 1. Limpa trades e arquivos (incluindo metric_state.json e history)
            paper_tracker.reset()
            
            state.reset_liquidation_history() # Resolvido Erro 7 do Pyright
            # 1.1 Limpa rastreador LIVE se existir
            if live_tracker:
                live_tracker.reset()

            # 2. Reseta o rastro institucional em memória para forçar novo warmup
            if engine and engine.store:
                engine.store.reset_session_state()
            
            # 2.1 Reinicia relógio de warmup (Roadmap 12.3)
            state.restart_warmup(300.0)
            state.trading_mode = "paper" # Garante que o modo volte para paper
            sniper.trading_mode = "paper"
            _apply_runtime_mode( # Reaplica as configurações padrão de paper
                "paper",
                persist=False,
                prefs_path=prefs_path,
                state=state,
                sniper=sniper,
                signal_engine=signal_engine,
                cfg=cfg,
                paper_tracker=paper_tracker,
            )
            
            # 3. Limpa rastro de sinais no estado do dashboard
            state.reset_signals()

            # 4. Deep clean opcional: só remove debug/telemetria "rastro"
            #    (NÃO mexe em archive/ e history/ — já são limpos pelo reset principal via PaperTradeTracker.reset()).
            if deep_clean:
                debug_paths = [
                    "logs/paper_debug.jsonl",
                    "logs/pipeline_debug.jsonl",
                    "logs/pipeline_debug_error.jsonl",
                    "logs/runtime_main_debug.jsonl",
                    "logs/sniper_debug.jsonl",
                    "logs/signals.jsonl",
                    "logs/signal_refusals.jsonl",
                    "logs/ws_smoke_markers.txt",
                    "logs/heartbeat_debug.jsonl",
                    "logs/error.log",
                ]
                for p in debug_paths:
                    try:
                        Path(p).unlink(missing_ok=True)
                    except Exception:
                        pass
                logger.info("🧹 deep_clean executado: rastro/debug removidos.")

            logger.info("✅ HARD RESET concluído. Sistema em estado puro.")
            return {"ok": True}
        except Exception as e:
            logger.exception("❌ hard-reset handler error: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_exit():
        nonlocal stop_requested
        try:
            if stop_requested:
                return {"ok": True, "already_requested": True}
            stop_requested = True
            logger.warning("🛑 EXIT iniciado via Dashboard (gracioso)...")
            loop.call_soon_threadsafe(stop_event.set)
            return {"ok": True}
        except Exception as e:
            logger.exception("❌ exit handler error: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_close_trade(symbol: str, mode: str):
        try:
            symbol = symbol.strip().upper()
            mode = mode.strip().lower()
            logger.info("📣 Dashboard close-trade called symbol=%s mode=%s", symbol, mode)

            async def _do_close():
                if mode == "paper":
                    if paper_tracker:
                        return paper_tracker.close_manual(symbol, engine.data)
                elif mode == "live":
                    if sniper:
                        await sniper.close_position(symbol)
                        return True
                return None

            future = asyncio.run_coroutine_threadsafe(_do_close(), loop)
            try:
                res = future.result(timeout=10)
                if res:
                    return {"ok": True, "message": f"Trade {symbol} ({mode}) fechado."}
                return {"ok": False, "error": "Não foi possível fechar o trade."}
            except Exception as fe:
                return {"ok": False, "error": str(fe)}
        except Exception as e:
            logger.exception("❌ close-trade handler error: %s", e)
            return {"ok": False, "error": str(e)}

    def _on_close_all_live():
        try:
            logger.warning("🔥 Dashboard close-all-live called!")
            future = asyncio.run_coroutine_threadsafe(sniper.close_all_positions(), loop)
            future.result(timeout=20)
            return {"ok": True, "message": "Comando STOP ALL LIVE processado."}
        except Exception as e:
            logger.exception("❌ close-all-live error: %s", e)
            return {"ok": False, "error": str(e)}

    if dash_enabled:
        _main_dash_diag(
            f"dashboard_start attempt host={dash_host} port={dash_port} auto_open={auto_open} enabled=true"
        )
        if _is_port_in_use("127.0.0.1", dash_port) or _is_port_in_use(dash_host, dash_port):
            _main_dash_diag(
                f"dashboard_start blocked=true host={dash_host} port={dash_port}"
            )
            logger.error(
                "🔴 DASHBOARD BLOQUEADO: porta %s:%s em uso por outro processo!\n"
                "   Feche o terminal anterior ou rode: taskkill /F /IM python.exe (Windows)\n"
                "   O bot continua mas SEM dashboard web.",
                dash_host, dash_port,
            )
            print(f"\n⚠️  PORTA {dash_port} OCUPADA — Dashboard não iniciará. Mate o processo antigo.\n")
        else:
            _main_dash_diag(
                f"dashboard_start blocked=false launching thread host={dash_host} port={dash_port}"
            )
            run_dashboard_thread(
                state,
                signal_engine=signal_engine,
                host=dash_host,
                port=dash_port,
                auto_open=auto_open,
                browser=str(dash_cfg.get("browser", "chrome")),
                chrome_path=(dash_cfg.get("chrome_path") or None),
                on_set_mode=_on_set_mode,
                on_hard_reset=_on_hard_reset if paper_tracker else None,
                on_reset_paper=_on_reset_paper if paper_tracker else None,
                on_update_paper_settings=_on_update_paper_settings if paper_tracker else None,
                on_update_live_settings=_on_update_live_settings,
                on_update_live_advanced=cast(Any, _on_update_live_advanced),
                on_exit=_on_exit,
                on_toggle_live_compound=_on_toggle_live_compound,
                on_close_trade=_on_close_trade,
                on_close_all_live=_on_close_all_live,
                live_tracker=live_tracker,  # SPRINT 12.20: Passar LiveTracker para o dashboard
                engine=engine,
            )

    _min_trades_cal = int((prefs.get("paper") or {}).get("min_trades_for_calibration", 30))
    paper_analyzer = PaperAnalyzer(paper_tracker.config.closed_jsonl, min_trades_for_calibration=_min_trades_cal) if (paper_tracker is not None and paper_tracker.config is not None) else None

    # SPRINT 12.155: Instancia o Gerenciador de Risco (DNA Sniper)
    risk_manager = DrawdownManager(max_dd_pct=15.0)

    tasks = [
        asyncio.create_task(
            trading_loop(
                engine,
                signal_engine,
                sniper,
                state,
                journal,
                inflight,
                telegram=telegram,
                risk_manager=risk_manager
            )
        ),
        asyncio.create_task(heartbeat(engine, signal_engine, state)),
        asyncio.create_task(_daily_reset_loop(engine, state)),
        asyncio.create_task(ip_drift_guard_loop(state, telegram, interval_minutes=5)),
        # SPRINT 12.19: Trailing Stop Loop para modo LIVE
        # SPRINT 12.210: Injeção do state para otimização REST (Pilar 3)
        asyncio.create_task(sniper._trailing_stop_loop(base_interval=30.0, engine=engine, state=state)),
    ]

    async def _stop_watcher() -> None:
        await stop_event.wait()
        logger.info("🛑 Stop watcher: cancelando tasks e engine...")
        for t in list(tasks):
            t.cancel()
        engine_task.cancel()

    tasks.append(asyncio.create_task(_stop_watcher()))

    # 4.2 Painel LIVE (read-only): roda sempre enquanto o bot estiver ativo
    assert engine_client is not None
    tasks.append(asyncio.create_task(live_monitor_loop(state, engine_client, sniper, engine, telegram, interval_seconds=30)))

    # Relatórios 1h e diário em LIVE (Paper-only já é tratado nos loops paper)
    if telegram:
        tasks.append(asyncio.create_task(live_hourly_report_loop(live_tracker, telegram, state)))
        tasks.append(asyncio.create_task(live_daily_report_loop(live_tracker, telegram, state)))

    if paper_tracker:
        tasks.append(
            asyncio.create_task(
                paper_monitor_loop(
                    paper_tracker,
                    engine,
                    paper_tracker.config.update_seconds,
                )
            )
        )
        # Roadmap 3.4: hourly report enviado dentro de paper_analysis_loop (Paper-only).
        # Mantemos o loop antigo desativado para evitar duplicidade.
        if paper_analyzer:
            # Garante para o linter que os objetos não são None antes de disparar a task
            assert paper_tracker is not None
            tasks.append(
                asyncio.create_task(
                    paper_analysis_loop(
                        paper_analyzer,
                        signal_engine,
                        sniper,
                        paper_tracker,
                        telegram,
                        state,
                        interval_minutes=15
                    )
                )
            )
            # SPRINT 12.112: Ativa o loop de relatório horário que estava esquecido
            if telegram:
                tasks.append(asyncio.create_task(paper_hourly_report_loop(paper_tracker, telegram, state)))
        # Relatório diário às 20:50 UTC-3
        if telegram:
            tasks.append(
                asyncio.create_task(
                    paper_daily_report_loop(paper_tracker, telegram, state)
                )
            )

    if terminal_fallback and not dash_enabled:
        tasks.append(asyncio.create_task(run_terminal_dashboard(engine)))
    logger.info(
        "🎯 SqueezeSniper-V4 | paper=%s | signals=%s",
        state.trading_mode == "paper", # Usa o modo real do state
        journal.path,
    )
    if paper_tracker:
        logger.info(
            "📊 Paper tracker: %s | %s",
            paper_tracker.config.json_path,
            paper_tracker.config.csv_path,
        )
    if dash_enabled:
        logger.info("🌐 Dashboard: http://%s:%s (thread separada)", dash_host, dash_port)
    logger.info("Aguardando dados… trends levam ~50s após o primeiro ciclo OI.")

    try:
        if engine_task:
            # SPRINT 11.3: Cast de segurança no loop principal
            await asyncio.gather(*cast(List[Any], [engine_task] + tasks), return_exceptions=False)
    except Exception as e:
        logger.error("[CRITICAL] Erro detectado no loop principal: %s", e, exc_info=True)
        raise
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Encerrando bot…")
        await _shutdown(engine, engine_task, tasks)
        _release_instance_lock()
        try:
            create_backup()
        except Exception as _be:
            logger.warning("Backup automatico falhou: %s", _be)
        logger.info("Ate logo. Encerrando arvore de processos...")
        _kill_process_tree()

# ATENÇÃO: Se houver QUALQUER código abaixo desta linha, delete-o.
# O erro na linha 2182 indica que o arquivo foi duplicado por erro de colagem.

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
