"""Paper LONG: abertura, mark-to-market, SL/TP, export JSON + CSV (estilo fast-track)."""
import csv
import json
import logging
import asyncio
import math
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.metrics_snapshot import capture_metrics
from src.sizing_utils import calculate_position_size, calculate_kelly_risk, calculate_dynamic_risk_with_hft
from src.risk_manager import CORR_GROUPS

logger = logging.getLogger("PaperTracker")


def _utc_iso(ts: Optional[float] = None) -> str:
    t = ts if ts is not None else time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(symbol: str) -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{symbol}-{uuid.uuid4().hex[:6]}"


@dataclass
class PaperConfig:
    json_path: Path = Path("logs/paper_opportunities.json")
    csv_path: Path = Path("logs/paper_opportunities.csv")
    closed_jsonl: Path = Path("logs/paper_closed.jsonl")
    # Debug para entender por que o paper não está abrindo trades apesar de sinais
    debug_jsonl: Path = Path("logs/paper_debug.jsonl")

    update_seconds: float = 1.0
    max_open_per_symbol: int = 1
    max_open_positions: int = 5  # Máximo de trades simultâneos (global)
    min_hold_seconds: int = 0
    max_hold_seconds: int = 0
    leverage: int = 10
    sl_pct: float = 0.02
    max_notional_usdt: float = 500.0  # SPRINT 10: Limite de Tier Binance para segurança
    tp_pct: float = 0.04
    initial_capital: float = 1000.0
    risk_pct_per_trade: float = 0.05
    sl_decay_interval_minutes: int = 0
    fee_pct: float = 0.0004 # SPRINT 6.38: Taxa real (0.04% taker)
    sl_decay_step_pct: float = 0.0
    partial_tp_breakeven_pct: float = 0.0 # Novo: % da posição a fechar no breakeven
    tp_partial_roi: float = 4.0 # SPRINT 12.190: Realiza lucro em 4% ROI
    tp_partial_pct: float = 0.33 # SPRINT 12.190: Fecha 33% da mão
    sl_trailing_swing_low: bool = False
    swing_low_tf: str = "5m"
    slippage_pct: float = 0.05 # SPRINT 12.220: Slippage realista (Pilar 4)
    trailing_activation_delay_sec: int = 60 # AUDITORIA BRUTAL v4.2: Aumentado de 30s para 60s (deixa squeeze desenvolver)
    trailing_stop_callback: float = 0.6


class PaperTradeTracker:
    def __init__(self, config: PaperConfig, telegram: Optional[Any] = None):
        self.config = config
        self.telegram = telegram
        self._open: Dict[str, Dict[str, Any]] = {}
        self._closed: List[Dict[str, Any]] = []
        self._closed_max = 500
        self._post_trade_pending: Dict[str, Dict[str, Any]] = {} # Trades aguardando alpha decay

        self.current_capital: float = config.initial_capital
        self.initial_capital: float = config.initial_capital
        self.peak_capital: float = config.initial_capital
        self.risk_pct_per_trade: float = config.risk_pct_per_trade
        self._capital_history: List[Dict[str, Any]] = []
        self._history_max = 500
        # Lock para evitar colisões de escrita no Windows (WinError 32 / Permission denied)
        self._io_lock = threading.RLock()
        for p in (config.json_path, config.csv_path, config.closed_jsonl, config.debug_jsonl):
            p.parent.mkdir(parents=True, exist_ok=True)
        self._load_disk_state()

        # Debug: confirmar que o tracker foi instanciado (e o arquivo debug criado).
        self._append_debug(
            {
                "ts": time.time(),
                "event": "paper_tracker_init",
                "current_capital": self.current_capital,
                "risk_pct_per_trade": self.risk_pct_per_trade,
                "max_open_positions": self.config.max_open_positions,
                "max_open_per_symbol": self.config.max_open_per_symbol,
                "json_path": str(self.config.json_path),
                "closed_jsonl": str(self.config.closed_jsonl),
                "telegram_present": self.telegram is not None,
                "telegram_enabled": bool(getattr(self.telegram, "enabled", None)) if self.telegram is not None else None,
            }
        )

        if not self._capital_history:
            self._capital_history.append({
                "ts": time.time(), 
                "capital": self.current_capital,
                "risk_pct": self.risk_pct_per_trade
            })

    def reset(self) -> None:
        """
        Limpa TODAS as informações de trades paper em memória e em disco,
        para começar uma coleta "pura".
        """
        self._open = {}
        self._closed = []
        self._capital_history = [{
            "ts": time.time(), 
            "capital": self.initial_capital,
            "risk_pct": self.risk_pct_per_trade
        }]
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital

        # JSON: sobrescreve com estrutura vazia
        empty_payload = {
            "updated_at": _utc_iso(),
            "current_capital": self.current_capital,
            "capital_history": self._capital_history,
            "stats": self._stats(),
            "open": [],
            "closed": [],
        }
        try:
            tmp = self.config.json_path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(empty_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.config.json_path)
        except OSError as e:
            logger.error("Falha ao resetar paper JSON: %s", e)

        # JSONL/CSV: zera removendo arquivos para evitar "restos" visuais
        try:
            if self.config.closed_jsonl.exists():
                self.config.closed_jsonl.unlink()
        except OSError as e:
            logger.error("Falha ao resetar paper closed_jsonl: %s", e)

        try:
            if self.config.csv_path.exists():
                self.config.csv_path.unlink()
        except OSError as e:
            logger.error("Falha ao resetar paper csv: %s", e)
        
        # Zera os snapshots históricos (DailySnapshotLogger) para uma limpeza completa
        try:
            history_dir = Path("logs/history")
            if history_dir.exists():
                shutil.rmtree(history_dir)
                logger.info("Pasta de snapshots históricos (logs/history) removida.")
        except OSError as e:
            logger.error("Falha ao resetar logs de history: %s", e)

        # Zera o estado das métricas para evitar dados antigos contaminando a nova coleta
        try:
            metric_state_path = Path("logs/metric_state.json")
            if metric_state_path.exists():
                metric_state_path.unlink()
                logger.info("Estado das métricas (metric_state.json) resetado com sucesso.")
        except OSError as e:
            logger.error("Falha ao resetar metric_state.json: %s", e)

    def close_manual(self, symbol: str, market_data: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """Fecha manualmente um trade em aberto."""
        with self._io_lock:
            trade = self._open.get(symbol)
            if not trade:
                return None

            d = market_data.get(symbol) or {}
            price = float(d.get("price") or 0)
            if price <= 0:
                price = trade["live"].get("last_price") or trade["entry"]["price"]

            closed = self._close_trade(trade, price, "manual_exit", market_data)
            self._persist()
            return closed

    def _load_disk_state(self) -> None:
        if not self.config.json_path.is_file():
            return
        try:
            raw = json.loads(self.config.json_path.read_text(encoding="utf-8"))
            for t in raw.get("open", []):
                sym = t.get("symbol")
                # SPRINT 11: Validação de integridade do preço na carga
                if sym and t.get("status") == "open" and t.get("entry", {}).get("price", 0) > 0:
                    # Normalização de dados legados (Governança)
                    if "breakeven_partial_closed" not in t:
                        t["breakeven_partial_closed"] = False
                    if "breakeven_sl_moved" not in t:
                        t["breakeven_sl_moved"] = False
                    
                    entry = t.get("entry", {})
                    # Garante que as quantidades existam no dicionário entry (Sprint 6.1)
                    if "current_quantity" not in entry:
                        sig = entry.get("signal", {})
                        # Se não encontrar no sinal (onde foi colocado por erro), calcula via notional
                        entry["current_quantity"] = sig.get("current_quantity") or (
                            entry.get("notional_usdt", 0) / entry.get("price", 1)
                        )
                        entry["initial_quantity"] = sig.get("initial_quantity") or entry["current_quantity"]

                    self._open[sym] = t
            self._closed = list(raw.get("closed", []))[-self._closed_max :]

            # Backfill para campos initial_* (legado de sessões antes da correção)
            # Objetivo: o dashboard mostrar "margem/notional inicial" mesmo após partial breakeven.
            def _backfill_entry_initial_fields(entry: Dict[str, Any]) -> None:
                price = entry.get("price")
                leverage = entry.get("leverage", self.config.leverage)
                initial_qty = entry.get("initial_quantity", entry.get("current_quantity"))

                if price is None or leverage is None or initial_qty is None:
                    return

                if entry.get("initial_notional_usdt") is None:
                    try:
                        entry["initial_notional_usdt"] = float(initial_qty) * float(price)
                    except (TypeError, ValueError):
                        return

                if entry.get("initial_usdt_margin") is None:
                    try:
                        entry["initial_usdt_margin"] = float(entry["initial_notional_usdt"]) / float(leverage)
                    except (TypeError, ValueError, KeyError):
                        return

                # SPRINT 11.25: Backfill de Fees para trades legados
                if entry.get("fee_usdt") is None:
                    try:
                        entry["fee_usdt"] = float(entry.get("initial_notional_usdt", 0)) * self.config.fee_pct
                    except (TypeError, ValueError, KeyError):
                        return

            # open
            for t in self._open.values():
                entry = t.get("entry") or {}
                _backfill_entry_initial_fields(entry)
                t["entry"] = entry

            # closed
            for t in self._closed:
                entry = t.get("entry") or {}
                _backfill_entry_initial_fields(entry)
                t["entry"] = entry

            self.initial_capital = raw.get(
                "initial_capital", self.config.initial_capital
            )
            self.current_capital = raw.get("current_capital", self.initial_capital)
            self.peak_capital = raw.get("peak_capital", self.current_capital)
            self._capital_history = raw.get("capital_history", [])
            self.risk_pct_per_trade = raw.get(
                "risk_pct_per_trade", self.config.risk_pct_per_trade
            )
        except (OSError, json.JSONDecodeError) as e:
            # Se o arquivo JSON principal falhar, tentar carregar apenas os trades fechados do JSONL
            # para garantir que o histórico de PnL não seja perdido.
            logger.warning("Não foi possível carregar paper state do JSON principal: %s. Tentando carregar closed do JSONL.", e)
            try:
                if self.config.closed_jsonl.exists():
                    with self.config.closed_jsonl.open("r", encoding="utf-8") as f:
                        for line in f:
                            trade = json.loads(line)
                            self._closed.append(trade)
            except (OSError, json.JSONDecodeError) as e_jsonl:
                logger.error("Falha ao carregar trades fechados do JSONL: %s", e_jsonl)
            logger.warning("Não foi possível carregar paper state: %s", e)

    def _append_debug(self, record: Dict[str, Any]) -> None:
        """Registra motivos/inputs relevantes quando o paper aborta open_long()."""
        try:
            with self._io_lock:
                with self.config.debug_jsonl.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Falha em gravar paper debug jsonl: %s", e)

    def _maybe_telegram_trade_open(self, trade: Dict[str, Any]) -> None:
        """Notifica abertura real do paper (best-effort, sem travar o bot)."""
        telegram = getattr(self, "telegram", None)
        try:
            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "telegram_maybe_open_enter",
                    "telegram_none": telegram is None,
                    "enabled": bool(getattr(telegram, "enabled", None)) if telegram is not None else None,
                    "trade_symbol": trade.get("symbol"),
                    "trade_id": trade.get("id"),
                }
            )
        except Exception:
            pass

        if not telegram:
            return

        symbol = str(trade.get("symbol") or "")
        trade_id = trade.get("id")

        try:
            loop = asyncio.get_running_loop()

            async def _runner() -> None:
                self._append_debug(
                    {
                        "ts": time.time(),
                        "event": "telegram_trade_open_start",
                        "symbol": symbol,
                        "id": trade_id,
                    }
                )
                try:
                    await telegram.trade_open(trade, mode="paper")
                except Exception as e:
                    self._append_debug(
                        {
                            "ts": time.time(),
                            "event": "telegram_trade_open_exception",
                            "symbol": symbol,
                            "id": trade_id,
                            "error": str(e),
                        }
                    )

            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "telegram_trade_open_scheduled",
                    "symbol": symbol,
                    "id": trade_id,
                }
            )
            loop.create_task(_runner())
        except RuntimeError:
            # Se não houver loop rodando (execução fora do async), ignora.
            return
        except Exception as e:
            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "telegram_trade_open_schedule_exception",
                    "symbol": symbol,
                    "id": trade_id,
                    "error": str(e),
                }
            )

    def _maybe_telegram_trade_close(self, trade: Dict[str, Any]) -> None:
        """Notifica fechamento real do paper (best-effort, sem travar o bot).
        Instrumentado para registrar agendamento e falhas em logs/paper_debug.jsonl.
        """
        telegram = getattr(self, "telegram", None)
        if not telegram:
            return

        symbol = str(trade.get("symbol") or "")
        trade_id = trade.get("id")

        try:
            loop = asyncio.get_running_loop()

            async def _runner() -> None:
                self._append_debug(
                    {
                        "ts": time.time(),
                        "event": "telegram_trade_close_start",
                        "symbol": symbol,
                        "id": trade_id,
                    }
                )
                try:
                    await telegram.trade_close(trade, mode="paper")
                except Exception as e:
                    self._append_debug(
                        {
                            "ts": time.time(),
                            "event": "telegram_trade_close_exception",
                            "symbol": symbol,
                            "id": trade_id,
                            "error": str(e),
                        }
                    )

            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "telegram_trade_close_scheduled",
                    "symbol": symbol,
                    "id": trade_id,
                }
            )
            loop.create_task(_runner())
        except RuntimeError:
            return
        except Exception as e:
            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "telegram_trade_close_schedule_exception",
                    "symbol": symbol,
                    "id": trade_id,
                    "error": str(e),
                }
            )

    def has_open(self, symbol: str) -> bool:
        return symbol in self._open

    def _check_correlation_guard(self, symbol: str) -> bool:
        """DNA Sniper: Evita abrir múltiplas posições no mesmo grupo de correlação."""
        for group_name, symbols in CORR_GROUPS.items():
            if symbol in symbols:
                for open_sym in self._open.keys():
                    if open_sym in symbols and open_sym != symbol:
                        logger.warning("🛡️ Correlation guard: %s bloqueado (já existe %s no grupo %s)",
                                       symbol, open_sym, group_name)
                        self._append_debug({
                            "ts": time.time(),
                            "event": "correlation_guard_block",
                            "symbol": symbol,
                            "existing_symbol": open_sym,
                            "group": group_name,
                        })
                        return False
        return True

    def _get_kelly_risk(
        self, 
        trades_1m: Optional[int] = None,
        score: float = 0.0,
        is_high_quality: bool = False
    ) -> float:
        """
        Sprint 5.2: Kelly Criterion (Quarter-Kelly)
        Calcula o risco dinâmico com base na performance real dos últimos trades.
        P2-1: Usa função compartilhada para paridade com Live.
        """
        kelly_risk = calculate_kelly_risk(self._closed, self.risk_pct_per_trade, score=score, is_high_quality=is_high_quality)
        # SPRINT 13.2: Aplica decaimento de risco baseado em HFT trades se fornecido (Contexto de Entrada)
        if trades_1m is not None:
            return calculate_dynamic_risk_with_hft(kelly_risk, trades_1m)
        return kelly_risk

    def _round_quantity(self, qty: float, step_size: str) -> float:
        """Round quantity DOWN to nearest step with correct floating precision."""
        step = float(step_size)
        precision = len(step_size.split('.')[-1].rstrip('0')) if '.' in step_size else 0
        return round(math.floor(qty / step) * step, precision)

    def _round_price(self, price: float, tick_size: str, up: bool = False) -> float:
        """Round price to nearest tick. UP=ceil (TakeProfit), DOWN=floor (StopLoss)."""
        tick = float(tick_size)
        precision = len(tick_size.split('.')[-1].rstrip('0')) if '.' in tick_size else 0
        if up:
            res = round(math.ceil(price / tick) * tick, precision)
        else:
            res = round(math.floor(price / tick) * tick, precision)
            
        # SPRINT 12.2: Se o arredondamento causar um salto > 10% no preço alvo, aborta o snapping
        if abs(res - price) / price > 0.10:
            return price

        # SPRINT 11.43: Proteção contra rounding to zero em ativos sub-penny
        return res if res > 0 else price

    def open_long(
        self,
        symbol: str,
        price: float,
        signal: Dict[str, Any],
        market_data: Dict[str, Dict],
    ) -> Optional[Dict[str, Any]]:
        # P1-2: Simulação de latência de execução (100-200ms) para aproximar do live
        import random
        latency_ms = random.uniform(100, 200)
        time.sleep(latency_ms / 1000.0)
        
        # Debug: confirmar se open_long está sendo chamado (antes de qualquer return/abort)
        self._append_debug(
            {
                "ts": time.time(),
                "event": "paper_open_called",
                "symbol": symbol,
                "price": price,
                "simulated_latency_ms": latency_ms,
                "has_open": self.has_open(symbol),
                "signal": {
                    "exp": signal.get("exp"),
                    "oi_trend": signal.get("oi_trend"),
                    "lsr_trend": signal.get("lsr_trend"),
                    "trades_1m": signal.get("trades_1m"),
                    "cvd_1m": signal.get("cvd_1m"),
                    "timestamp": signal.get("timestamp"),
                },
            }
        )

        # --- SPRINT 13.1: Anti-Weak-Signal Guard ---
        # Rejeita trades com score muito baixo para evitar entradas no escuro
        signal_score = signal.get("score", 0)
        if signal_score < 85:
            self._append_debug({
                "ts": time.time(),
                "event": "paper_open_abort_weak_score",
                "symbol": symbol,
                "signal_score": signal_score,
                "threshold": 85,
                "reason": "Score abaixo do mínimo de qualidade"
            })
            logger.warning(
                "🛡️ WEAK SIGNAL bloqueado em %s: score=%.1f (threshold=85)",
                symbol, signal_score
            )
            return None

        # --- SPRINT 11.40: Anti-Hallucination Entry Guard ---
        # Se o preço de entrada divergir > 5% do preço estável no market_data, aborta.
        stable_price = float(market_data.get(symbol, {}).get("price") or 0)
        if stable_price > 0 and abs(price - stable_price) / stable_price > 0.05:
            self._append_debug({
                "ts": time.time(),
                "event": "hallucination_entry_blocked",
                "symbol": symbol, "signal_price": price, "stable_price": stable_price
            })
            return None

        # --- Sprint 9.2: Proteção global por limite de posições abertas ---
        # Lógica deve ocorrer antes de qualquer validação específica por símbolo.
        if len(self._open) >= self.config.max_open_positions:
            # Se já existe posição neste símbolo, não trata como “nova abertura”.
            if self.has_open(symbol):
                logger.debug("Paper: já existe posição aberta em %s", symbol)
                return None

            logger.info(
                "🛡️ Max posições atingido (%d/%d) — %s ignorado por proteção global",
                len(self._open),
                self.config.max_open_positions,
                symbol,
            )
            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "paper_open_ignored_max_open_positions",
                    "symbol": symbol,
                    "open_count": len(self._open),
                    "max_open_positions": self.config.max_open_positions,
                }
            )
            return None

        # DNA Sniper: Validação de Correlação
        if not self._check_correlation_guard(symbol):
            return None

        if self.has_open(symbol):
            logger.debug("Paper: já existe posição aberta em %s", symbol)
            return None

        entry_metrics = capture_metrics(symbol, market_data)

        # Integridade do trade paper: não abrir se LSR bruto estiver ausente E lsr_trend também.
        # Se lsr_trend existe, podemos considerar o sinal válido mesmo que o LSR bruto esteja None/0.
        lsr_val = entry_metrics.get("lsr")
        lsr_trend_val = entry_metrics.get("lsr_trend:5m")
        if (lsr_val is None or lsr_val == 0) and (lsr_trend_val is None or lsr_trend_val >= 0):
            # Debug persistente: console/logger pode não chegar em arquivo.
            self._append_debug(
                {
                    "ts": time.time(),
                    "event": "paper_open_abort_lsr",
                    "symbol": symbol,
                    "price": price,
                    "lsr": lsr_val,
                    "lsr_trend_5m": lsr_trend_val,
                    "signal": {
                        "exp": signal.get("exp"),
                        "oi_trend": signal.get("oi_trend"),
                        "lsr_trend": signal.get("lsr_trend"),
                        "trades_1m": signal.get("trades_1m"),
                        "cvd_1m": signal.get("cvd_1m"),
                        "timestamp": signal.get("timestamp"),
                    },
                    "metrics": {
                        "exp:5m": entry_metrics.get("exp:5m"),
                        "oi_trend:5m": entry_metrics.get("oi_trend:5m"),
                        "lsr_trend:5m": entry_metrics.get("lsr_trend:5m"),
                    },
                }
            )
            logger.warning(
                "📋 PAPER OPEN abortado: %s sem LSR bruto (lsr=%r) e sem lsr_trend válido (%r).",
                symbol,
                lsr_val,
                lsr_trend_val,
            )
            return None

        # Cálculo de SL/TP Dinâmico (DNA Sniper)
        dyn_sl_pct = self.config.sl_pct
        dyn_tp_pct = self.config.tp_pct
        
        # Se o CVD (Fluxo de volume) for massivo, estica o Take Profit para capturar a perna inteira
        cvd_val = signal.get("cvd_1m", 0) or 0
        if cvd_val > 50000:
            dyn_tp_pct *= 2.0
        elif cvd_val > 10000:
            dyn_tp_pct *= 1.5
            
        # --- Sprint 5.1: SL/TP Dinâmico por Volatilidade (DNA Sniper) ---
        pc_5m = abs(entry_metrics.get("price_change:5m", 0) or 0)
        pc_1h = abs(entry_metrics.get("price_change:1h", 0) or 0)

        if pc_1h > 5.0:
            dyn_sl_pct *= 1.5   # Mercado muito volátil (Macro): SL 50% mais largo
        elif pc_5m > 1.5:
            dyn_sl_pct *= 1.2   # Movimento explosivo recente: SL 20% mais largo

        # SPRINT 5.8: Bônus de Cascata de Liquidação (Execução Agressiva)
        if signal.get("liq_cascade"):
            dyn_tp_pct *= 1.5 # Alvo mais longo para capturar o pânico institucional
            dyn_sl_pct *= 0.8 # Stop ligeiramente mais curto (momentum forte a favor)

        tick_size = entry_metrics.get("tick_size", "0.001")
        step_size = entry_metrics.get("step_size", "0.001")

        # SPRINT 12.220: Slippage Realista na Entrada (Pilar 4)
        # Simula o spread do livro: o preço de execução é ligeiramente pior que o sinal.
        slipped_entry_price = price * (1 + self.config.slippage_pct / 100.0)
        slipped_entry_price = self._round_price(slipped_entry_price, tick_size, up=True)

        # SL/TP calculados a partir do preço de execução REAL (com slippage)
        sl_price = self._round_price(slipped_entry_price * (1 - dyn_sl_pct), tick_size, up=False)
        tp_price = self._round_price(slipped_entry_price * (1 + dyn_tp_pct), tick_size, up=True)
        
        # --- SPRINT 13.2: Spread Mínimo Guard ---
        # Garante que sempre há PELO MENOS 0.3% de distância entre SL e entrada
        # Evita que o SL seja "disparado" por volatilidade micro-intra-segundo
        MIN_SL_SPREAD_PCT = 0.003  # 0.3%
        min_sl_allowed = slipped_entry_price * (1 - MIN_SL_SPREAD_PCT)

        if sl_price > min_sl_allowed:
            original_sl = sl_price
            sl_price = self._round_price(min_sl_allowed, tick_size, up=False)
            
            self._append_debug({
                "ts": time.time(),
                "event": "paper_sl_spread_guard_applied",
                "symbol": symbol,
                "original_sl_pct": dyn_sl_pct * 100,
                "original_sl_price": original_sl,
                "adjusted_sl_price": sl_price,
                "spread_pct": (slipped_entry_price - sl_price) / slipped_entry_price * 100 if slipped_entry_price > 0 else 0,
            })
            
            logger.info(
                "📈 [PAPER] SL Spread Guard ativado em %s: SL ajustado para garantir 0.3%% mínimo",
                symbol
            )

        # --- SPRINT 13.3: SL/TP Ratio Guard ---
        # Garante que o ratio SL/TP seja pelo menos 1:2.5
        # Exemplo: se SL é 2%, TP deve ser pelo menos 5%
        MIN_RATIO = 2.5

        tp_distance = (tp_price - slipped_entry_price) / slipped_entry_price if slipped_entry_price > 0 else 0
        sl_distance = (slipped_entry_price - sl_price) / slipped_entry_price if slipped_entry_price > 0 else 0.001

        if tp_distance > 0 and sl_distance > 0:
            actual_ratio = tp_distance / sl_distance
            
            if actual_ratio < MIN_RATIO:
                # Aumentar TP se necessário
                new_tp_distance = sl_distance * MIN_RATIO
                new_tp_price = self._round_price(slipped_entry_price * (1 + new_tp_distance), tick_size, up=True)
                
                self._append_debug({
                    "ts": time.time(),
                    "event": "paper_ratio_sl_tp_guard_applied",
                    "symbol": symbol,
                    "original_ratio": round(actual_ratio, 2),
                    "min_ratio": MIN_RATIO,
                    "original_tp": tp_price,
                    "adjusted_tp": new_tp_price,
                })
                
                tp_price = new_tp_price
                logger.info(
                    "📊 [PAPER] SL/TP Ratio Guard: aumentado TP em %s (ratio original: %.2f, mínimo: %.1f)",
                    symbol, actual_ratio, MIN_RATIO
                )
        
        # P2-1: Usa função compartilhada de sizing para paridade com Live
        committed_margin = sum(t["entry"]["usdt_margin"] for t in self._open.values())
        
        # Calcula o risco dinâmico (Kelly)
        hft_trades = int(signal.get("trades_1m", 0))
        risk_pct = self._get_kelly_risk(hft_trades)
        
        # Calcula max_notional dinâmico (compounding)
        max_notional_usdt = self.config.max_notional_usdt
        if self.initial_capital > 0 and self.current_capital > self.initial_capital:
            max_notional_usdt = max_notional_usdt * (self.current_capital / self.initial_capital)
        
        # Cap de margem durante calibração: sem histórico suficiente,
        # Kelly não tem dados confiáveis — limita exposição por trade.
        CALIBRATION_TRADE_THRESHOLD = 50
        CALIBRATION_MARGIN_CAP = 20.0  # USDT máximo por trade até ter dados
        margin_cap = (
            CALIBRATION_MARGIN_CAP
            if len(self._closed) < CALIBRATION_TRADE_THRESHOLD
            else float("inf")
        )

        # Floor mínimo $20: alinhado com o CALIBRATION_MARGIN_CAP — durante calibração,
        # todos os trades usam $20 fixo (floor = cap), eliminando variância de tamanho
        # que contamina o Kelly. Abaixo de $20 as fees consomem retornos mínimos e
        # a posição não tem significância estatística.
        # Guarda de segurança: nunca mais que 10% do capital disponível como floor.
        MIN_TRADE_MARGIN = min(CALIBRATION_MARGIN_CAP, self.current_capital * 0.10)
        sizing_result = calculate_position_size(
            available_capital=min(self.current_capital, margin_cap * self.config.leverage),
            risk_pct=risk_pct,
            leverage=self.config.leverage,
            price=slipped_entry_price,
            committed_margin=committed_margin,
            min_margin_usdt=max(MIN_TRADE_MARGIN, self.current_capital * risk_pct * 0.8),
            max_notional_usdt=min(max_notional_usdt, margin_cap * self.config.leverage),
            step_size=step_size,
        )
        
        # Telemetria de governança: valida compounding no sizing (paper_debug.jsonl)
        self._append_debug(
            {
                "ts": time.time(),
                "event": "paper_sizing_risk_check",
                "current_capital": self.current_capital,
                "committed_margin": committed_margin,
                "effective_capital": sizing_result["effective_capital"],
                "risk_pct": risk_pct,
                "usdt_margin_target": sizing_result["usdt_margin"],
                "risk_pct_per_trade_config": self.risk_pct_per_trade,
                "leverage": self.config.leverage,
                "max_open_positions": self.config.max_open_positions,
                "open_count": len(self._open),
            }
        )
        
        if sizing_result.get("error") == "margin_too_baixa":
            return None
        
        quantity = sizing_result["quantity"]
        actual_notional = sizing_result["notional_usdt"]
        actual_margin = sizing_result["usdt_margin"]
        
        # Taxa de abertura (subtraída imediatamente do PnL realizado do trade)
        opening_fee = actual_notional * self.config.fee_pct

        now = time.time()

        trade = {
            "id": _new_id(symbol),
            "symbol": symbol,
            "side": "LONG",
            "status": "open",
            "entry": {
                "time": now,
                "time_iso": _utc_iso(now),
                "price": slipped_entry_price,
                "usdt_margin": actual_margin,
                "initial_usdt_margin": actual_margin,
                "leverage": self.config.leverage,
                "price_change_24h": market_data.get(symbol, {}).get("price_change_24h", 0),
                "notional_usdt": actual_notional,
                "initial_notional_usdt": actual_notional,
                "realized_pnl_usdt": -opening_fee, # Começa negativo pela taxa
                "fee_usdt": opening_fee, # SPRINT 11.21
                "initial_quantity": quantity,
                "current_quantity": quantity,
                "signal": {**signal, "kelly_risk_applied": risk_pct},
                "metrics": entry_metrics,
            },
            "targets": {
                "sl_price": sl_price,
                "tp_price": tp_price,
                "sl_pct": dyn_sl_pct,
                "tp_pct": dyn_tp_pct,
            },
            "breakeven_partial_closed": False, # Flag para controlar o fechamento parcial no breakeven
            "breakeven_sl_moved": False, # Flag para garantir que SL→breakeven aconteça só 1x (evita spam)
            "live": {
                "last_price": price,
                "last_update": now,
                "pnl_pct": 0.0,
                "pnl_usdt": 0.0,
                "mfe_pct": 0.0,
                "mae_pct": 0.0,
                "duration_sec": 0,
                "dist_sl_pct": (price - sl_price) / price * 100 if price else 0,
                "dist_tp_pct": (tp_price - price) / price * 100 if price else 0,
                "metrics": entry_metrics,
            },
            "exit": None,
            "quality": {
                "favorable_early": False,
                "notes": "",
                "decay_milestones_persisted": [], # SPRINT 10: Para rastrear quais marcos já foram persistidos
            },
        }
        self._open[symbol] = trade
        entry_dict = trade.get("entry") or {}
        if not isinstance(entry_dict, dict):
            entry_dict = {}
        targets_dict = trade.get("targets") or {}
        if not isinstance(targets_dict, dict):
            targets_dict = {}
        self._append_debug(
            {
                "ts": time.time(),
                "event": "paper_open_success",
                "symbol": symbol,
                "id": trade["id"],
                "open_count": len(self._open),
                "entry": {
                    "signal_price": price,
                    "price": entry_dict.get("price", 0.0), # Executed price with slippage
                    "sl_price": targets_dict.get("sl_price", 0.0),  # type: ignore[union-attr]
                    "tp_price": targets_dict.get("tp_price", 0.0),  # type: ignore[union-attr]
                },
            }
        )

        logger.info(
            "📋 PAPER OPEN %s @ %.4f | SL %.4f TP %.4f | Capital: %.2f USDT | Risco: %.2f USDT | id=%s",
            symbol,
            price,
            sl_price,
            tp_price,
            self.current_capital,
            actual_margin,
            trade["id"],
        )
        self._persist()
        self._append_debug(
            {
                "ts": time.time(),
                "event": "telegram_object_check_open_long",
                "symbol": symbol,
                "id": trade.get("id"),
                "telegram_present": bool(getattr(self, "telegram", None)),
            }
        )
        self._maybe_telegram_trade_open(trade)
        self._append_debug(
            {
                "ts": time.time(),
                "event": "paper_open_persisted",
                "symbol": symbol,
                "id": trade["id"],
                "open_count": len(self._open),
            }
        )
        return trade

    def tick(self, market_data: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Atualiza PnL; fecha em SL/TP/timeout. Retorna trades fechados neste tick."""
        closed_now: List[Dict[str, Any]] = []
        now = time.time()
        milestone_hit = False
        
        # SPRINT 10: Rastreio Pós-Trade (Alpha Decay Analysis) com persistência progressiva e DNA completo
        for trade_id in list(self._post_trade_pending.keys()):
            trade = self._post_trade_pending[trade_id]
            if "exit" not in trade: # Deve ter um exit para iniciar o decay
                continue
            exit_time = trade["exit"]["time"]
            elapsed = now - exit_time

            symbol = trade["symbol"]
            d = market_data.get(symbol)
            if not d:
                continue
            current_price = float(d.get("price") or 0)
            if current_price <= 0:
                continue

            # Sprint 11: Garantir estrutura post_trade robusta e tipagem Any para silenciar o Pylance
            if "post_trade" not in trade or not isinstance(trade["post_trade"], dict):
                trade["post_trade"] = {"current_drift": None, "snapshots": {}}
            
            pt: Any = trade["post_trade"]
            if "snapshots" not in pt:
                pt["snapshots"] = {}

            exit_price = trade["exit"]["price"]
            change_pct = (current_price - exit_price) / exit_price * 100

            DECAY_WINDOWS = [
                ("5m",  300),   ("15m", 900),   ("30m", 1800),
                ("60m", 3600),  ("4h",  14400), ("12h", 43200), ("24h", 86400),
            ]

            snapshots: Any = pt["snapshots"]
            for label, threshold in DECAY_WINDOWS:
                if elapsed >= threshold and label not in snapshots:
                    snapshots[label] = {
                        "pct":       round(change_pct, 4),
                        "price":     current_price,
                        "ts":        now,
                        "exp_btc":    d.get("exp_btc:5m"),
                        "exp":        d.get("exp:5m"),
                        "oi_trend":   d.get("oi_trend:5m"),
                        "lsr_trend":  d.get("lsr_trend:5m"),
                        "lsr":        d.get("lsr"),
                        "oi_chg":     d.get("oi_change_pct:5m"),
                        "lsr_chg":    d.get("lsr_change_pct:5m"),
                        "cvd_1m":     d.get("volume_delta_1min_stable"),
                        "rsi_5m":     d.get("rsi:5m"),
                        "ema_trend":  d.get("ema_trend:5m"),
                        "liq_short":  d.get("liq_short_1m_stable"),
                        "cascade":    d.get("liq_cascade", False),
                    }
                    # SPRINT 11: Persistência síncrona para evitar perda de dados
                    if label in pt: # Compatibilidade visual
                        pt[label] = round(change_pct, 4)
                    self._rewrite_closed_entry(trade)
                    # Adicionar ao persisted milestones para o dashboard/UI
                    trade["quality"]["decay_milestones_persisted"].append(label)
                    milestone_hit = True

            # Atualiza o preço atual "ao vivo" pós-trade para visualização imediata
            if "current_drift" not in pt:
                pt["current_drift"] = None
            pt["current_drift"] = round(change_pct, 4) # Sempre atualiza

            # Remove trade from active monitoring if 24h has passed
            if "24h" in snapshots:
                del self._post_trade_pending[trade_id]

        for symbol in list(self._open.keys()):
            trade = self._open[symbol]
            tick_size = trade["entry"]["metrics"].get("tick_size", "0.001")
            d = market_data.get(symbol) or {}
            price = float(d.get("price") or 0)
            
            # --- SPRINT 11: Price Sanity Guard ---
            # SPRINT 11.26: Sanidade apertada para 10% para evitar contaminação cross-symbol
            if price <= 0: continue
            
            # --- SPRINT 11.41: Anti-Outlier Tick Guard (O FIM DO DINHEIRO FAKE) ---
            entry_price = trade["entry"]["price"]
            last_price = trade["live"].get("last_price", entry_price)
            
            # SPRINT 11.41: Tolerância reduzida para 5% para evitar alucinações de PnL
            if abs(price - last_price) / last_price > 0.05:
                logger.warning("🚫 TICK MENTIROSO detectado em %s: %.4f (ignorado)", symbol, price)
                continue

            if abs(price - entry_price) / entry_price > 0.10:
                logger.warning("⚠️ Outlier de preço ignorado em %s: %.4f", symbol, price)
                continue

            pnl_pct_price = (price - entry_price) / entry_price * 100
            notional = trade["entry"]["notional_usdt"]

            # --- FIX SPRINT 10: Cálculo de PnL Robusto para Sub-Penny Assets ---
            # Em vez de (notional * pct), usamos (qty * delta_price) para evitar erros de escala
            current_qty = trade["entry"]["current_quantity"]
            unrealized_pnl_usdt = current_qty * (price - entry_price)
            
            # SPRINT 11.42: Hard Cap de PnL por Trade (DNA de Governança)
            # O Squeeze Sniper busca ignições. Um movimento de > 50% de PREÇO (500% PnL) 
            # em tempo recorde no radar de 5m é 99% das vezes um erro de dado.
            max_allowed_pnl = notional * 0.5 # Cap de 50% do valor total da posição (500% da margem)
            if abs(unrealized_pnl_usdt) > max_allowed_pnl:
                logger.debug("🛡️ PnL Capping em %s: %.2f -> %.2f", symbol, unrealized_pnl_usdt, max_allowed_pnl)
                unrealized_pnl_usdt = max(min(unrealized_pnl_usdt, max_allowed_pnl), -notional)
            
            pnl_usdt = unrealized_pnl_usdt + trade["entry"].get("realized_pnl_usdt", 0.0)

            # PnL% consistente com o pnl_usdt: % sobre a margem INICIAL (inclui taxa/partials)
            initial_margin = trade["entry"].get("initial_usdt_margin") or trade["entry"].get("usdt_margin") or 0.0
            pnl_pct = (pnl_usdt / initial_margin * 100.0) if initial_margin > 0 else pnl_pct_price

            live = trade["live"]
            duration = int(now - trade["entry"]["time"])
            mfe = max(live.get("mfe_pct", 0), pnl_pct)
            mae = min(live.get("mae_pct", 0), pnl_pct)

            if duration <= 60 and pnl_pct >= 0.15:
                trade["quality"]["favorable_early"] = True

            # --- Trailing SL dinâmico (paper/live) ---
            # Se o trade já está em lucro, ajusta o SL para reduzir drawdown e capturar mais winners.
            tp_pct_decimal = trade["targets"]["tp_pct"]
            tp_pct_pct = tp_pct_decimal * 100.0

            # SPRINT 13: Verifica delay de ativação do trailing stop
            entry_time = trade["entry"]["time"]
            duration_sec = now - entry_time
            trailing_delay_passed = duration_sec >= self.config.trailing_activation_delay_sec

            # DNA Sniper: Trailing Adaptativo por MFE (Paridade Live/Paper)
            current_mfe = max(live.get("mfe_pct", 0), pnl_pct)
            
            # SPRINT 13.5: Impedir choking inicial. 
            # Só ativa cálculo de novo SL se o trade estiver em lucro real (> 1%) E delay passado
            if pnl_pct < 1.0 or not trailing_delay_passed:
                adaptive_sl = 0.0
                profit_guard_sl = 0.0
            else:
                # --- DNA Sniper: Trailing Adaptativo por MFE ---
                # Quando MFE > 3%: trava mais agressivo (50% do MFE) — squeeze está ativo.
                # Quando MFE <= 3%: callback padrão do preferences (75%) — deixa respirar.
                # Dados: 10 trades com MFE alto saíram em loss com callback fixo de 75%.
                mfe_distance_pct = current_mfe / 100.0  # Converte para decimal
                cb_base = getattr(self.config, 'trailing_stop_callback', 0.75)
                cb = 0.50 if current_mfe >= 3.0 else cb_base
                trailing_distance_pct = mfe_distance_pct * cb
                adaptive_sl = entry_price * (1 + trailing_distance_pct)
                
                # DNA Sniper: Usa a distância mínima configurada no JSON (Paridade Total)
                dist_pct = getattr(self.config, 'trailing_stop_distance_pct', 0.015)
                min_trailing_sl = entry_price * (1 + dist_pct)
                adaptive_sl = max(adaptive_sl, min_trailing_sl)

            # --- DNA Sniper: Opção 3 - Profit Guard (Locking) ---
            profit_guard_sl = 0.0
            if pnl_pct >= 10.0:
                profit_guard_sl = entry_price * 1.05 # Trava 5% de lucro real
            elif pnl_pct >= 5.0:
                profit_guard_sl = entry_price * 1.02 # Trava 2% de lucro real

            # Busca swing low como referência técnica
            tech_sl = 0.0
            if d:
                tech_sl = d.get(f"swing_low:{self.config.swing_low_tf}", 0.0)

            current_sl = trade["targets"]["sl_price"]
            # SPRINT 13.5: Removido 'entry_price' do max() inicial para permitir pullback.
            # O SL só deve subir para o entry_price via lógica de Breakeven ou Profit Guard.
            new_sl_raw = max(adaptive_sl, profit_guard_sl, tech_sl, current_sl)
            new_sl = self._round_price(new_sl_raw, tick_size)

            # SPRINT 13.6: Paridade Live - Gatilho de Breakeven Clássico (85% do TP)
            breakeven_threshold_pct = tp_pct_pct * 0.85
            breakeven_reached = pnl_pct >= breakeven_threshold_pct
            breakeven_sl = self._round_price(entry_price * 1.001, tick_size, up=True)
            
            if breakeven_reached and not trade.get("breakeven_sl_moved", False) and current_sl < breakeven_sl:
                # Fechamento parcial no breakeven (se configurado e ainda não feito)
                if self.config.partial_tp_breakeven_pct > 0 and not trade.get("breakeven_partial_closed", False):
                    qty_to_close = trade["entry"]["current_quantity"] * self.config.partial_tp_breakeven_pct
                    pnl_from_partial = qty_to_close * (price - entry_price)
                    trade["entry"]["realized_pnl_usdt"] = trade["entry"].get("realized_pnl_usdt", 0.0) + pnl_from_partial
                    trade["entry"]["current_quantity"] -= qty_to_close
                    
                    # SPRINT 6.21: Notional é simplesmente Quantidade * Preço (sem multiplicar leverage de novo)
                    trade["entry"]["notional_usdt"] = trade["entry"]["current_quantity"] * entry_price
                    trade["entry"]["usdt_margin"] = trade["entry"]["notional_usdt"] / self.config.leverage
                    
                    trade["breakeven_partial_closed"] = True
                    logger.info("🎯 [PAPER] Partial Breakeven executado: %s (-%.0f%% posicao | PnL parcial: %.4f)",
                                symbol, self.config.partial_tp_breakeven_pct * 100, pnl_from_partial)

                trade["targets"]["sl_price"] = breakeven_sl
                current_sl = breakeven_sl
                trade["breakeven_sl_moved"] = True
                logger.info("📋 SLIPING-STOP: Risco Zero! SL movido para Breakeven (~85%% TP) em %s", symbol)
            
            # SPRINT 12.190: Real PTP (Partial Take Profit em Lucro)
            # AUDITORIA BRUTAL 2026-06-02: DNA PTP DESABILITADO TEMPORARIAMENTE
            # Motivo: Interfere com trailing delay de 60s (fecha trades em 17s)
            # TODO: Reabilitar após validar trailing stop puro
            # if pnl_pct >= self.config.tp_partial_roi and not trade.get("tp_partial_done", False):
            #     qty_to_close = trade["entry"]["current_quantity"] * self.config.tp_partial_pct
            #     pnl_realized = qty_to_close * (price - entry_price)
            #
            #     trade["entry"]["realized_pnl_usdt"] = trade["entry"].get("realized_pnl_usdt", 0.0) + pnl_realized
            #     trade["entry"]["current_quantity"] -= qty_to_close
            #     trade["entry"]["notional_usdt"] = trade["entry"]["current_quantity"] * entry_price
            #     trade["entry"]["usdt_margin"] = trade["entry"]["notional_usdt"] / self.config.leverage
            #
            #     # Move SL para lucro garantido (Entry + 1%)
            #     profit_lock_sl = self._round_price(entry_price * 1.01, tick_size, up=True)
            #     trade["targets"]["sl_price"] = max(trade["targets"]["sl_price"], profit_lock_sl)
            #
            #     trade["tp_partial_done"] = True
            #     logger.info("🎯 DNA PTP: Realizado lucro de %.1f%% em %s. SL travado em +1%%.",
            #                 self.config.tp_partial_pct * 100, symbol)
            
            # Atualização do SL se o novo alvo for superior
            if new_sl > current_sl:
                trade["targets"]["sl_price"] = new_sl
                log_type = "PROFIT GUARD" if new_sl_raw == profit_guard_sl else "TRAILING ADAPTATIVO"
                logger.info(f"📈 [PAPER-{log_type}] {symbol} SL subiu para: {new_sl:.4f} (MFE: {current_mfe:.2f}%)")

            sl = trade["targets"]["sl_price"]
            tp = trade["targets"]["tp_price"]
            live.update(
                {
                    "last_price": price,
                    "last_update": now,
                    "pnl_pct": round(pnl_pct, 4),
                    "pnl_usdt": round(pnl_usdt, 4),
                    "mfe_pct": round(mfe, 4),
                    "mae_pct": round(mae, 4),
                    "duration_sec": duration,
                    "duration_s": duration,  # F-14: alias para scripts de análise do Brain
                    "dist_sl_pct": round((price - sl) / price * 100, 4),
                    "dist_tp_pct": round((tp - price) / price * 100, 4),
                    "metrics": capture_metrics(symbol, market_data),
                }
            )

            exit_reason = None
            exit_price = price

            # P1 v4.2.5: Respeita min_hold_seconds antes de permitir trailing stop
            min_hold = getattr(self.config, 'min_hold_seconds', 0)
            can_trailing = (min_hold == 0 or duration >= min_hold)

            # Gate "squeeze morto": se após 90s o preço nunca subiu 0.3%, o squeeze
            # não vai acontecer — sair antes de segurar por 8 minutos pagando SL.
            current_mfe = live.get("mfe_pct", 0) or 0
            current_pnl = live.get("pnl_pct", 0) or 0

            if (not trade.get("squeeze_dead_checked")
                    and duration >= 90
                    and current_mfe < 0.3
                    and current_mfe >= 0):
                trade["squeeze_dead_checked"] = True
                exit_reason = "squeeze_failed"

            # Gate "squeeze morreu após movimento": MFE chegou mas voltou forte.
            # Se após 120s o PnL está < -1.5% e o MFE nunca passou de 0.5%,
            # o squeeze confirmou falso — sair antes de arrastar até max_hold.
            if exit_reason is None and not trade.get("squeeze_abort_checked"):
                if duration >= 120 and current_pnl < -1.5 and current_mfe < 0.5:
                    trade["squeeze_abort_checked"] = True
                    exit_reason = "squeeze_aborted"

            # Gate "MAE crítico": Se o preço caiu mais de 2% após 120s sem MFE relevante,
            # o squeeze não veio — evita os trades de -9% a -22% que seguramos até max_hold.
            if exit_reason is None and not trade.get("mae_guard_checked"):
                if duration >= 120 and current_pnl < -2.0 and current_mfe < 1.0:
                    trade["mae_guard_checked"] = True
                    exit_reason = "mae_guard"

            # F-14: Late mae_guard aos 240s — cobre janela entre 120s e trailing (180s).
            # F-17: threshold mfe < 3.0 (era 2.0) — BBUSDT MFE=2.98% escapou com -15.92%.
            if exit_reason is None and not trade.get("mae_guard_late_checked"):
                if duration >= 240 and current_pnl < -3.0 and current_mfe < 3.0:
                    trade["mae_guard_late_checked"] = True
                    exit_reason = "mae_guard_late"

            if exit_reason is None and price <= sl:
                if sl >= entry_price:
                    if can_trailing:
                        exit_reason = "trailing_stop"
                else:
                    exit_reason = "stop_loss"
            elif exit_reason is None and price >= tp:
                exit_reason = "take_profit"
            elif exit_reason is None and (
                self.config.max_hold_seconds > 0
                and duration >= self.config.max_hold_seconds
            ):
                exit_reason = "max_hold"

            if exit_reason:
                # Exits baseados em tempo/MAE são imediatos — o gate com _checked flag
                # não re-dispara no tick 2, quebrando a lógica de 2 confirmações.
                _immediate = exit_reason in ("squeeze_failed", "squeeze_aborted", "mae_guard", "mae_guard_late", "max_hold")
                if _immediate:
                    closed = self._close_trade(trade, exit_price, exit_reason, market_data)
                    closed_now.append(closed)
                else:
                    # SPRINT 11.26: Confirmação de Gatilho para exits de preço (SL/TP/trailing)
                    trade["_close_confirmations"] = trade.get("_close_confirmations", 0) + 1
                    if trade["_close_confirmations"] >= 2:
                        closed = self._close_trade(trade, exit_price, exit_reason, market_data)
                        closed_now.append(closed)
                    else:
                        logger.info("⏳ Sniper confirmando saída real em %s (Tick 1/2)...", symbol)
            else:
                # Reset da confirmação se o preço voltar para a zona segura
                trade["_close_confirmations"] = 0

        if self._open or closed_now or milestone_hit:
            self._persist()
        return closed_now

    def _close_trade(
        self,
        trade: Dict[str, Any],
        exit_price: float,
        reason: str,
        market_data: Dict[str, Dict],
    ) -> Dict[str, Any]:
        # SPRINT 12.220: Slippage Realista na Saída (Pilar 4)
        # Simula fill parcial e spread: o preço de venda é ligeiramente pior que o trigger.
        tick_size = trade["entry"]["metrics"].get("tick_size", "0.00000001")
        slipped_exit_price = exit_price * (1 - self.config.slippage_pct / 100.0)
        slipped_exit_price = self._round_price(slipped_exit_price, tick_size, up=False)

        symbol = trade["symbol"]
        entry_price = trade["entry"]["price"]
        
        # --- FIX SPRINT 10: PnL Realizado Final ---
        current_qty = trade["entry"]["current_quantity"]
        remaining_pnl_usdt = current_qty * (slipped_exit_price - entry_price)
        
        # Total Realizado = O que já fechou + O que está fechando agora
        total_pnl_usdt = trade["entry"].get("realized_pnl_usdt", 0.0) + remaining_pnl_usdt
        # SPRINT 11.21: Taxa de fechamento baseada no preço de saída real para precisão total
        closing_fee = (slipped_exit_price * current_qty * self.config.fee_pct)
        final_pnl_usdt = total_pnl_usdt - closing_fee

        # PnL% consistente com PnL USDT: % sobre a margem INICIAL (taxas + parciais)
        initial_margin = trade["entry"].get("initial_usdt_margin") or trade["entry"].get("usdt_margin") or 0.0
        pnl_pct = (final_pnl_usdt / initial_margin * 100.0) if initial_margin > 0 else 0.0

        now = time.time()
        mfe = trade["live"].get("mfe_pct", 0)
        mae = trade["live"].get("mae_pct", 0)

        if reason == "take_profit":
            entry_quality = "excellent" if mfe >= self.config.tp_pct * 100 * 0.8 else "good"
        elif reason == "stop_loss":
            entry_quality = "poor" if mfe < 0.1 else "mixed"
        else:
            entry_quality = "good" if pnl_pct > 0 else "weak"

        trade["status"] = "closed"
        trade["exit"] = {
            "time": now,
            "time_iso": _utc_iso(now),
            "price": slipped_exit_price,
            "reason": reason,
            "pnl_pct": round(pnl_pct, 4),
            "fee_usdt": closing_fee, # SPRINT 11.21
            "pnl_usdt": round(final_pnl_usdt, 4),
            "metrics": capture_metrics(symbol, market_data),
        }
        trade["quality"].update(
            {
                "entry_assertiveness": entry_quality,
                "exit_assertiveness": "target_hit"
                if reason in ("take_profit", "stop_loss")
                else "time_exit",
                "mfe_pct": mfe,
                "mae_pct": mae,
                "win": pnl_pct > 0,
            }
        )

        # Sprint 11: Inicialização tipada para compatibilidade Pylance e Dashboard
        # Usamos Any para evitar que o Pyright infira Dict[str, dict] devido à chave 'snapshots'
        post_trade_init: Any = {
            "current_drift": None,  # Primeiro item para forçar Any no literal
            "snapshots": {},
            "5m": None, # Dashboard espera estas chaves planas
            "15m": None,
            "30m": None,
            "60m": None,
            "4h": None,
            "12h": None,
            "24h": None,
        }
        trade["post_trade"] = post_trade_init

        del self._open[symbol]
        self._closed.append(trade)
        
        # SPRINT 10: Não truncar _closed aqui. A remoção será feita no tick()
        # quando o ciclo de decay estiver completo.

        # Marcar como pendente de persistência no JSONL até completar o ciclo de decay.
        trade_id = trade.get("id")
        if trade_id:
            self._post_trade_pending[trade_id] = trade # Adiciona para monitoramento de decay
            self._append_closed_jsonl(trade) # Escreve a entrada inicial no JSONL

        # --- SPRINT 11: Gestão de Capital Incremental ---
        # O capital não deve ser recalculado via sum(), pois a lista _closed é truncada.
        # Adicionamos o PnL líquido diretamente ao capital atual.
        self.current_capital = round(self.current_capital + final_pnl_usdt, 2)
        
        # Notifica o Telegram com os dados já processados
        self._maybe_telegram_trade_close(trade)

        # JSONL só será persistido quando post_trade["60m"] for preenchido no tick()
        logger.info(
            "📋 PAPER CLOSE %s %s @ %.4f | PnL %+.2f%% (%+.2f USDT) | Capital: %.2f USDT | %s",
            symbol,
            reason,
            exit_price,
            pnl_pct,
            trade["exit"]["pnl_usdt"],
            self.current_capital,
            entry_quality,
        )
        return trade

    def get_stats(self) -> Dict[str, Any]:
        """SPRINT 12.215: API unificada para paridade com LiveTracker."""
        return self._stats()

    def _stats(self) -> Dict[str, Any]:
        closed = self._closed
        wins = sum(1 for t in closed if (t.get("exit") or {}).get("pnl_pct", 0) > 0)
        total = len(closed)
        avg_pnl = sum((t.get("exit") or {}).get("pnl_pct", 0) for t in closed) / total if total else 0.0
        
        # SPRINT 12.195: Métrica de Eficiência de Captura (DNA Audit)
        avg_mfe = sum((t.get("quality") or {}).get("mfe_pct", 0) for t in closed) / total if total else 1.0
        capture_ratio = (avg_pnl / avg_mfe * 100) if avg_mfe > 0 else 0.0

        open_pnl = sum(t["live"].get("pnl_usdt", 0) for t in self._open.values())

        # SPRINT 6.23: Cálculo de Win Rate por Símbolo para o gráfico no Dashboard
        win_rate_by_symbol = {}
        sym_wins: Dict[str, int] = {}
        sym_totals: Dict[str, int] = {}
        for t in closed:
            s = t["symbol"].replace("USDT", "")
            sym_totals[s] = sym_totals.get(s, 0) + 1
            if (t.get("exit") or {}).get("pnl_pct", 0) > 0:
                sym_wins[s] = sym_wins.get(s, 0) + 1
        
        for s in sym_totals:
            win_rate_by_symbol[s] = round((sym_wins.get(s, 0) / sym_totals[s]) * 100, 1)

        return {
            "open_count": len(self._open),
            "closed_count": total, # Chave primária para o DrawdownManager
            "wins": wins,
            "losses": total - wins,
            "win_rate_pct": round(wins / total * 100, 2) if total else 0.0,
            "avg_closed_pnl_pct": round(avg_pnl, 4),
            "capture_efficiency_pct": round(capture_ratio, 2),
            "unrealized_pnl_usdt": round(open_pnl, 4),
            "win_rate_by_symbol": win_rate_by_symbol,
        }

    def set_initial_capital(self, value: float) -> None:
        """Atualiza o capital inicial (e reseta o capital atual)."""
        self.initial_capital = value
        self.current_capital = value
        self._persist()
        # self._recalculate_usdt_amount() # SPRINT 11.28: Recalcula usdt_amount ao mudar capital
        logger.info("Capital inicial atualizado para %.2f USDT", value)

    def set_risk_pct(self, value: float) -> None:
        """Atualiza o percentual de risco por trade."""
        self.risk_pct_per_trade = value
        self._persist()
        # self._recalculate_usdt_amount() # SPRINT 11.28: Recalcula usdt_amount ao mudar risco
        logger.info("Risco por trade atualizado para %.2f%%", value * 100)

    def set_leverage(self, value: int) -> None:
        """
        Atualiza alavancagem (paper).
        Segurança: rejeita se houver trades paper abertas, pois muda margin/SL/TP.
        """
        if value < 1:
            raise ValueError("leverage must be >= 1")

        # Se houver trades abertas, não mexe
        if self._open:
            raise ValueError("Cannot change leverage while paper trades are open")

        self.config.leverage = value
        self._persist()
        logger.info("Alavancagem paper atualizada para %sx", self.config.leverage)

    @property
    def usdt_amount(self) -> float:
        """SPRINT 11.28: Retorna o usdt_amount (base de sizing) para o paper, derivado do capital e risco."""
        # SPRINT 12.6: Paridade semântica — retorna o capital base atual para o dashboard
        return self.current_capital

    def snapshot(self) -> Dict[str, Any]:
        return {
            "updated_at": _utc_iso(),
            "current_capital": self.current_capital,
            "initial_capital": self.initial_capital,
            "risk_pct_per_trade": self.risk_pct_per_trade,
            "max_open_positions": self.config.max_open_positions,
            "stats": self._stats(),
            "capital_history": self._capital_history,
            "open": list(self._open.values()),
            "closed_recent": list(reversed(self._closed[-20:])),
        }

    def _persist(self) -> None:
        # Lock evita colisão de escrita (Windows) entre open_long/tick/close.
        with self._io_lock:
            # Sprint 4E: Record capital history
            now = time.time()
            current_risk = self._get_kelly_risk()
            
            # Sprint 5.8: Cálculo de Drawdown (queda a partir do pico)
            self.peak_capital = max(self.peak_capital, self.current_capital)
            drawdown_pct = (self.peak_capital - self.current_capital) / self.peak_capital if self.peak_capital > 0 else 0

            # Record point if changed or if it's the first
            last_entry = self._capital_history[-1] if self._capital_history else None
            if not last_entry or last_entry["capital"] != self.current_capital or last_entry.get("risk_pct") != current_risk:
                self._capital_history.append({
                    "ts": now, 
                    "capital": self.current_capital, 
                    "risk_pct": current_risk,
                    "drawdown_pct": drawdown_pct
                })
                if len(self._capital_history) > self._history_max:
                    self._capital_history.pop(0)

            payload = {
                "updated_at": _utc_iso(),
                "current_capital": self.current_capital,
                "initial_capital": self.initial_capital,
                "peak_capital": self.peak_capital,
                "risk_pct_per_trade": self.risk_pct_per_trade,
                "stats": self._stats(),
                "capital_history": self._capital_history,
                "open": list(self._open.values()),
                "closed": self._closed,
            }
            
            # Tenta gravar JSON com retentativas (Windows safety)
            for attempt in range(5):
                try:
                    # tmp único evita colisão entre múltiplos writes (ou múltiplas execuções do programa)
                    tmp = self.config.json_path.with_name(
                        f"{self.config.json_path.stem}.{uuid.uuid4().hex}.tmp"
                    )
                    tmp.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    # Path.replace usa os.replace (atômico no Windows quando possível)
                    tmp.replace(self.config.json_path)
                    break
                except (OSError, PermissionError) as e:
                    if attempt == 2:
                        logger.error(
                            "Falha persistente ao gravar paper JSON (attempt %d): %s",
                            attempt,
                            e,
                        )
                    time.sleep(0.1 * (attempt + 1)) # Backoff progressivo para liberar o arquivo

            self._write_csv()

    def _append_closed_jsonl(self, trade: Dict[str, Any]) -> None:
        """Escreve a entrada inicial de um trade fechado no JSONL."""
        try:
            with self.config.closed_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(trade, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Falha closed jsonl: %s", e)

    def _rewrite_closed_entry(self, updated_trade: Dict) -> None:
        """
        Atualiza a linha do trade fechado no JSONL com os dados de alpha decay.
        Esta operação é I/O intensiva e deve ser usada com parcimônia.
        """
        trade_id = updated_trade.get("id")
        if not trade_id:
            logger.warning("Tentativa de reescrever trade sem ID: %s", updated_trade)
            return

        try:
            path = self.config.closed_jsonl
            if not path.exists():
                return

            # SPRINT 11: Processamento linha a linha para evitar bloqueio do Event Loop e lentidão
            target_sym = updated_trade.get("symbol")
            target_ts  = updated_trade.get("entry", {}).get("time", 0)
            updated_lines = []
            found = False
            
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    t = json.loads(line)
                    is_match = (
                        (trade_id and t.get("id") == trade_id) or
                        (t.get("symbol") == target_sym and
                         abs(t.get("entry", {}).get("time", 0) - target_ts) < 2.0)
                    )
                    if is_match:
                        updated_lines.append(json.dumps(updated_trade, ensure_ascii=False))
                        found = True
                    else:
                        updated_lines.append(line.strip())

            if found:
                # Escrita atômica rápida
                tmp_path = path.with_suffix(".tmp")
                tmp_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
                tmp_path.replace(path)
            else:
                logger.warning("Trade com ID %s não encontrado no JSONL para reescrita.", trade_id)
        except Exception as e:
            logger.error("Erro ao reescrever alpha decay no JSONL para trade %s: %s", trade_id, e)

    def _write_csv(self) -> None:
        # Espera ser chamado por _persist() (já com lock), mas mantemos safety.
        with self._io_lock:
            rows = self._flatten_for_csv(self._open.values()) + self._flatten_for_csv(
                self._closed
            )
            if not rows:
                return
            fieldnames = list(rows[0].keys())
            
            for attempt in range(3):
                try:
                    # tmp único evita colisão entre múltiplos writes (ou múltiplas execuções)
                    tmp = self.config.csv_path.with_name(
                        f"{self.config.csv_path.stem}.{uuid.uuid4().hex}.tmp"
                    )
                    with tmp.open("w", newline="", encoding="utf-8") as f:
                        w = csv.DictWriter(
                            f,
                            fieldnames=fieldnames,
                            extrasaction="ignore",
                        )
                        w.writeheader()
                        w.writerows(rows)
                    tmp.replace(self.config.csv_path)
                    break
                except OSError as e:
                    if attempt == 2:
                        logger.error(
                            "Falha persistente ao gravar paper CSV (attempt %d): %s",
                            attempt,
                            e,
                        )
                    time.sleep(0.05)

    def _flatten_for_csv(self, trades) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for t in trades:
            entry = t.get("entry") or {}
            live = t.get("live") or {}
            exit_ = t.get("exit") or {}
            sig = entry.get("signal") or {}
            q = t.get("quality") or {}
            em = entry.get("metrics") or {}
            lm = live.get("metrics") or {}
            xm = exit_.get("metrics") or {}
            out.append(
                {
                    "id": t.get("id"),
                    "status": t.get("status"),
                    "symbol": t.get("symbol"),
                    "entry_time": entry.get("time_iso"),
                    "entry_price": entry.get("price"),
                    "exit_time": exit_.get("time_iso", ""),
                    "exit_price": exit_.get("price", ""),
                    "exit_reason": exit_.get("reason", ""),
                    "sl_price": (t.get("targets") or {}).get("sl_price"),
                    "tp_price": (t.get("targets") or {}).get("tp_price"),
                    "pnl_pct": live.get("pnl_pct") if t.get("status") == "open" else exit_.get("pnl_pct"),
                    "pnl_usdt": live.get("pnl_usdt") if t.get("status") == "open" else exit_.get("pnl_usdt"),
                    "fee_entry": entry.get("fee_usdt"),
                    "fee_exit": exit_.get("fee_usdt"),
                    "mfe_pct": live.get("mfe_pct"),
                    "mae_pct": live.get("mae_pct"),
                    "duration_sec": live.get("duration_sec"),
                    "entry_exp": sig.get("exp"),
                    "entry_oi_trend": sig.get("oi_trend"),
                    "entry_lsr_trend": sig.get("lsr_trend"),
                    "entry_oi": em.get("oi"),
                    "entry_lsr": em.get("lsr"),
                    "last_exp": lm.get("exp"),
                    "last_oi_trend": lm.get("oi_trend"),
                    "last_lsr_trend": lm.get("lsr_trend"),
                    "exit_exp": xm.get("exp"),
                    "favorable_early": q.get("favorable_early"),
                    "relax_label": sig.get("relax_label", "NORMAL"),
                    "entry_assertiveness": q.get("entry_assertiveness", ""),
                    "win": q.get("win", ""),
                }
            )
        return out
