"""Runtime state shared between trading loop and web dashboard."""
import json
import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, TYPE_CHECKING, Tuple
from pathlib import Path

from config import BotConfig
if TYPE_CHECKING:
    from src.sniper import Sniper
    from src.paper_tracker import PaperTradeTracker

from src.market_view import calculate_fit_score

logger = logging.getLogger("BotState")


class BotState:
    """Shared runtime state for bot loop + web dashboard thread."""

    def __init__(self, cfg: BotConfig, signal_thresholds: Optional[Dict[str, float]] = None, liq_history_path: Optional[Path] = None):
        self.cfg = cfg
        self.signal_thresholds = signal_thresholds or {}
        self.market_data: Dict[str, Dict] = {}
        self.symbol_count: int = 0
        self.market_squeeze_level: float = 0.0
        self.low_squeeze_since: Optional[float] = None
        self.market_paused: bool = False

        # Uptime clock (process lifetime)
        self.boot_started_at: float = time.time()

        # Warmup clock (decoupled from uptime)
        self.warmup_duration_sec: float = 300.0
        self.warmup_started_at: float = self.boot_started_at
        self.warmup_remaining: float = self.warmup_duration_sec
        self.warmup_elapsed: float = 0.0
        self.warmup_pct: float = 0.0

        # trading_mode mutável em runtime (BotConfig é frozen)
        self.sniper_trading_mode: str = cfg.trading_mode # Inicializa com o modo do config
        self.trading_mode: str = cfg.trading_mode

        # Thread-safety: Bot loop + WebDashboard thread chamam snapshot()
        self._lock = threading.RLock()

        # DNA Sniper P1: Cache centralizado de scores
        self._score_cache: Dict[str, Tuple[float, float]] = {}
        self._SCORE_CACHE_TTL = 2.0
        self._cache_hits = 0
        self._cache_misses = 0

        self._signals: Deque[Dict[str, Any]] = deque(maxlen=80)
        # Deque para armazenar os últimos 20 sinais fantasma
        self._ghosts: Deque[Dict[str, Any]] = deque(maxlen=20)
        self.paper_trades = 0

        # Sprint 11: Fonte de dados pura para o Gráfico de Liquidações
        self._total_liq_accumulated = 0.0
        self._liq_history: Deque[Dict[str, Any]] = deque(maxlen=500)
        self.daily_reset_active = False

        self.liq_history_path = liq_history_path

        self._paper_tracker: Optional['PaperTradeTracker'] = None
        self._sniper: Optional['Sniper'] = None
        self._cached_rows: List[Dict[str, Any]] = []
        self._cached_macro: Dict[str, Any] = {}
        self._cached_stats: Dict[str, Any] = {}
        # (Note: Estrutura de cache unificada para evitar conflitos de snapshot)

        # 4.2 LIVE Long — estado para o painel LIVE
        self._live_positions: List[Dict[str, Any]] = []
        self._live_balance: Dict[str, Any] = {}
        self._live_api_status: Dict[str, Any] = {"ok": False, "error": None, "ts": None}

        # Initialize warmup derived fields
        self._recompute_warmup_fields_locked()

    # ---------------- Warmup clock API (Roadmap 12.3) ----------------
    def restart_warmup(self, seconds: float = 300.0) -> None:
        with self._lock:
            self.warmup_duration_sec = float(seconds)
            self.warmup_started_at = time.time()
            self._recompute_warmup_fields_locked()

    def get_warmup_remaining(self) -> float:
        with self._lock:
            self._recompute_warmup_fields_locked()
            return float(self.warmup_remaining)

    def get_warmup_pct(self) -> float:
        with self._lock:
            self._recompute_warmup_fields_locked()
            return float(self.warmup_pct)

    def get_warmup_elapsed(self) -> float:
        with self._lock:
            self._recompute_warmup_fields_locked()
            return float(self.warmup_elapsed)

    def get_warmup_total(self) -> float:
        with self._lock:
            return float(self.warmup_duration_sec)

    def warmup_active(self) -> bool:
        with self._lock:
            self._recompute_warmup_fields_locked()
            return self.warmup_remaining > 0.0

    def _recompute_warmup_fields_locked(self) -> None:
        """Must be called under _lock."""
        now = time.time()
        elapsed = max(0.0, now - float(self.warmup_started_at))
        remaining = max(0.0, float(self.warmup_duration_sec) - elapsed)
        total = float(self.warmup_duration_sec) if self.warmup_duration_sec > 0 else 1.0
        pct = max(0.0, min(100.0, (elapsed / total) * 100.0))

        self.warmup_elapsed = elapsed
        self.warmup_remaining = remaining
        self.warmup_pct = pct

    # ---------------- Dashboard / Engine shared data ----------------
    def set_dashboard_data(self, rows: List[Dict], macro: Dict, stats: Dict) -> None:
        """Chamado pelo loop principal para atualizar o rastro visual."""
        with self._lock:
            self._cached_rows = rows
            self._cached_macro = macro
            self._cached_stats = stats

    def update_live_data(
        self,
        *,
        positions: List[Dict[str, Any]],
        balance: Dict[str, Any],
        api_status: Dict[str, Any],
    ) -> None:
        """Atualiza dados LIVE para renderização no dashboard (Painel LIVE)."""
        with self._lock:
            self._live_positions = positions
            self._live_balance = balance
            self._live_api_status = api_status

    def bind_paper_tracker(self, tracker) -> None:
        with self._lock:
            self._paper_tracker = tracker

    def bind_sniper(self, sniper_instance) -> None:
        with self._lock:
            self._sniper = sniper_instance

    def get_fit_score(self, symbol: str, data: Dict[str, Any]) -> float:
        """Retorna score fit (0-100) usando cache interno para poupar CPU."""
        now = time.time()
        # RLock permite reentrada com segurança
        with self._lock:
            if symbol in self._score_cache:
                val, ts = self._score_cache[symbol]
                if (now - ts) < self._SCORE_CACHE_TTL:
                    self._cache_hits += 1
                    return val
            
            self._cache_misses += 1
            # Sprint 12.95: Cálculo real via motor matemático
            score_raw = calculate_fit_score(data)
            score = float(score_raw) if score_raw is not None else 0.0
            self._score_cache[symbol] = (score, now)
            return score

    def get_score_stats(self) -> Dict[str, Any]:
        """Retorna telemetria de performance do cache para o Heartbeat."""
        total = self._cache_hits + self._cache_misses
        rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_pct": rate
        }

    def bind_market(self, market_data: Dict[str, Dict], symbol_count: int) -> None:
        with self._lock:
            self.market_data = market_data
            self.symbol_count = symbol_count

            # Acumula liquidação total do mercado para o gráfico
            current_batch_liq = sum(d.get("liq_short_1m", 0) or 0 for d in market_data.values())
            self._total_liq_accumulated += current_batch_liq
            if not self._liq_history or abs(self._liq_history[-1]["value"] - self._total_liq_accumulated) > 100:
                event = {"ts": time.time(), "value": self._total_liq_accumulated}
                self._liq_history.append(event)
                self._save_liquidation_event(event)

    def _save_liquidation_event(self, event: Dict[str, Any]):
        if not self.liq_history_path:
            return
        try:
            self.liq_history_path.parent.mkdir(parents=True, exist_ok=True)
            with self.liq_history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("❌ Erro ao persistir evento de liquidação: %s", e)

    def load_liquidation_history(self):
        if self.liq_history_path and self.liq_history_path.exists():
            try:
                with self.liq_history_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event = json.loads(line)
                            self._liq_history.append(event)
                            self._total_liq_accumulated = event.get("value", 0.0)
                        except json.JSONDecodeError:
                            continue
                logger.info("✅ Histórico de liquidações carregado: %d eventos.", len(self._liq_history))
            except Exception as e:
                logger.error("❌ Erro ao carregar histórico de liquidações: %s", e)

    def reset_liquidation_history(self):
        with self._lock:
            self._liq_history.clear()
            self._total_liq_accumulated = 0.0
            if self.liq_history_path and self.liq_history_path.exists():
                try:
                    self.liq_history_path.unlink()
                except Exception:
                    pass
            logger.info("✅ Histórico de liquidações resetado.")

    def add_signal(self, signal: Dict[str, Any], *, paper: bool) -> None:
        with self._lock:
            entry = {**signal, "paper": paper, "logged_at": time.time()}
            self._signals.appendleft(entry)
            if paper:
                self.paper_trades += 1

    def add_ghost_signal(self, ghost: Dict[str, Any]) -> None:
        """Adiciona um sinal que não disparou por filtros de gating."""
        with self._lock:
            # Evita duplicatas imediatas do mesmo símbolo
            if not any(g["symbol"] == ghost["symbol"] for g in list(self._ghosts)[:3]):
                self._ghosts.appendleft({**ghost, "logged_at": time.time()})

    def reset_signals(self) -> None:
        """Resetar os sinais recentes para nova coleta."""
        with self._lock:
            self._signals.clear()
            self._ghosts.clear()
            self._liq_history.clear()
            self._total_liq_accumulated = 0.0
            self.paper_trades = 0
    
    def update_sniper_mode(self, mode: str) -> None:
        with self._lock:
            self.sniper_trading_mode = mode

    def update_market_status(self) -> None:
        """Calcula o Squeezometer e verifica se o mercado deve ser pausado (Sprint 5.8)."""
        with self._lock:
            if not self.market_data:
                return

            # Calcula scores de todos para achar a média dos Top 10 (Squeezometer)
            # SPRINT 12.95: Usa o cache centralizado
            scores = [self.get_fit_score(sym, d) for sym, d in self.market_data.items()]
            scores.sort(reverse=True)
            top_10 = scores[:10]
            self.market_squeeze_level = sum(top_10) / 10 if top_10 else 0

            # Lógica de Pausa: abaixo de 20 por > 10 min (600s)
            if self.market_squeeze_level < 20.0:
                if self.low_squeeze_since is None:
                    self.low_squeeze_since = time.time()
            else:
                self.low_squeeze_since = None

            # Pausa após 10 minutos de marasmo institucional
            self.market_paused = (
                self.low_squeeze_since is not None
                and (time.time() - self.low_squeeze_since) > 600
            )

    def snapshot(self) -> Dict[str, Any]:
        # Mantém lock por um “copy moment” para o JSON ficar consistente
        with self._lock:
            self._recompute_warmup_fields_locked()

            paper_snapshot = (
                self._paper_tracker.snapshot()
                if self._paper_tracker
                else {"open": [], "closed_recent": [], "stats": {}}
            )

            # SPRINT 11.28: Adiciona configurações do Sniper ao snapshot
            sniper_inst = self._sniper
            if sniper_inst:
                sniper_config = {
                    "usdt_amount": getattr(sniper_inst, "usdt_amount", 0.0),
                    "leverage": getattr(sniper_inst, "leverage", 1),
                    "risk_pct_per_trade": getattr(sniper_inst, "risk_pct_per_trade", 0.0),
                    "max_open_positions": getattr(sniper_inst, "max_open_positions", 0),
                }
            else:
                sniper_config = {"usdt_amount": 0.0, "leverage": 1, "risk_pct_per_trade": 0.0, "max_open_positions": 0}

            return {
                "ts": time.time(),
                # Uptime do processo continua independente do warmup (Roadmap 12.3)
                "uptime_sec": int(time.time() - self.boot_started_at),
                "trading_mode": self.trading_mode,
                "symbol_count": self.symbol_count,
                "market_squeeze_level": self.market_squeeze_level,
                "market_paused": self.market_paused,

                # Warmup (Roadmap 12.3 / 12.4)
                "warmup_active": self.warmup_remaining > 0.0,
                "warmup_remaining": float(self.warmup_remaining),
                "warmup_elapsed": float(self.warmup_elapsed),
                "warmup_pct": float(self.warmup_pct),
                "warmup_total": float(self.warmup_duration_sec),

                # Back-compat: mantém campo antigo caso front ainda dependa
                "warmup_duration_sec": float(self.warmup_duration_sec),

                "top_n": self.cfg.top_n,
                # SPRINT 11.11: Garante que stats reflitam o estado de warmup no dashboard
                "stats": self._cached_stats if not self.daily_reset_active else {
                    "with_price": self._cached_stats.get("with_price", 0),
                    "with_oi": 0,
                    "with_trend": 0,
                    "total_blocked": self._cached_stats.get("total_blocked", 0),
                    "efficiency_pct": self._cached_stats.get("efficiency_pct", 0),
                    "total_analyzed": self._cached_stats.get("total_analyzed", 0),
                    "status": "RESET_ACTIVE",  # type: ignore[dict-item]
                },
                "macro": self._cached_macro,
                "rows": self._cached_rows,
                "signals": list(self._signals)[:25],
                "ghosts": list(self._ghosts),
                "paper_trades": self.paper_trades,
                "paper": paper_snapshot,
                "liq_history": list(self._liq_history)[-100:],  # fonte para o gráfico
                "live": {
                    "config": sniper_config, # SPRINT 11.28: Configurações do Sniper
                    "compound_enabled": bool(getattr(self._sniper, "compound_enabled", False)) if self._sniper else False,
                    "positions": list(self._live_positions),
                    "balance": dict(self._live_balance),
                    "api_status": dict(self._live_api_status),
                },
            }
