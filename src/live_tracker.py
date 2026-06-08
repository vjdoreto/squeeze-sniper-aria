"""Live Tracker: Rastreia trades LIVE com funding fees, comissões, PnL real, ROI."""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.metrics_snapshot import capture_metrics
from src.sizing_utils import calculate_kelly_risk, calculate_dynamic_risk_with_hft
from src.risk_manager import CORR_GROUPS

logger = logging.getLogger("LiveTracker")


def _utc_iso(ts: Optional[float] = None) -> str:
    t = ts if ts is not None else time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id(symbol: str) -> str:
    import uuid
    return f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{symbol}-{uuid.uuid4().hex[:6]}"


@dataclass
class LiveConfig:
    json_path: Path = Path("logs/live_opportunities.json")
    closed_jsonl: Path = Path("logs/live_closed.jsonl")
    debug_jsonl: Path = Path("logs/live_debug.jsonl")  # DNA Sniper: Debug para auditoria
    csv_path: Path = Path("logs/live_opportunities.csv")  # SPRINT 13: Espelhado do PaperConfig
    update_seconds: float = 1.0
    max_open_per_symbol: int = 1
    max_open_positions: int = 3  # P0.2 FIX: Reduzido de 5 para 3 (alinhado com preferences.json)
    min_hold_seconds: int = 0
    max_hold_seconds: int = 0
    leverage: int = 10
    sl_pct: float = 0.02
    max_notional_usdt: float = 500.0  # SPRINT 10: Limite de Tier Binance para segurança
    tp_pct: float = 0.04
    initial_capital: float = 1000.0
    risk_pct_per_trade: float = 0.03  # P0.2 FIX: Reduzido de 0.05 para 0.03 (alinhado com preferences.json)
    sl_decay_interval_minutes: int = 0
    fee_pct: float = 0.0004  # SPRINT 6.38: Taxa real (0.04% taker)
    sl_decay_step_pct: float = 0.0
    partial_tp_breakeven_pct: float = 0.0  # DNA Sniper: % da posição a fechar no breakeven
    tp_partial_roi: float = 4.0 # SPRINT 12.190: Realiza lucro em 4% ROI
    tp_partial_pct: float = 0.33 # SPRINT 12.190: Fecha 33% da mão
    sl_trailing_swing_low: bool = False
    swing_low_tf: str = "5m"
    slippage_pct: float = 0.05 # SPRINT 13: Espelhado do PaperConfig (Pilar 4)
    trailing_activation_delay_sec: int = 60 # AUDITORIA BRUTAL v4.2: Aumentado de 30s para 60s (paridade com Paper)
    trailing_stop_callback: float = 0.6


class LiveTracker:
    def __init__(self, config: LiveConfig):
        self.config = config
        self._open: Dict[str, Dict[str, Any]] = {}
        self._closed: List[Dict[str, Any]] = []
        self._closed_max = 500

        self.current_capital: float = config.initial_capital
        self.initial_capital: float = config.initial_capital
        self.peak_capital: float = config.initial_capital
        self._capital_history: List[Dict[str, Any]] = []

        for p in (config.json_path, config.closed_jsonl, config.debug_jsonl):
            p.parent.mkdir(parents=True, exist_ok=True)
        self._load_disk_state()

        if not self._capital_history:
            self._capital_history.append({
                "ts": time.time(),
                "capital": self.current_capital,
            })
        
        # Debug: confirmar que o tracker foi instanciado
        self._append_debug({
            "ts": time.time(),
            "event": "live_tracker_init",
            "current_capital": self.current_capital,
            "risk_pct_per_trade": self.config.risk_pct_per_trade,
            "max_open_positions": self.config.max_open_positions,
            "max_open_per_symbol": self.config.max_open_per_symbol,
            "json_path": str(self.config.json_path),
            "closed_jsonl": str(self.config.closed_jsonl),
        })

    def _load_disk_state(self) -> None:
        if not self.config.json_path.is_file():
            return
        try:
            raw = json.loads(self.config.json_path.read_text(encoding="utf-8"))
            for t in raw.get("open", []):
                sym = t.get("symbol")
                if sym and t.get("status") == "open" and t.get("entry", {}).get("price", 0) > 0:
                    self._open[sym] = t
            self._closed = list(raw.get("closed", []))[-self._closed_max :]
            self.initial_capital = raw.get("initial_capital", self.config.initial_capital)
            self.current_capital = raw.get("current_capital", self.initial_capital)
            self.peak_capital = raw.get("peak_capital", self.current_capital)
            self._capital_history = raw.get("capital_history", [])
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Não foi possível carregar live state: %s", e)

    def reset(self) -> None:
        """Limpa todo o histórico LIVE para uma coleta pura."""
        self._open = {}
        self._closed = []
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self._capital_history = [{"ts": time.time(), "capital": self.initial_capital}]
        
        try:
            # Remove arquivos físicos para evitar re-hidratação de dados 'sujos'
            if self.config.json_path.exists():
                self.config.json_path.unlink()
            if self.config.closed_jsonl.exists():
                self.config.closed_jsonl.unlink()
            self._persist()
            logger.info("♻️ LiveTracker resetado com sucesso.")
        except Exception as e:
            logger.error("Erro ao resetar LiveTracker: %s", e)

    def _append_debug(self, record: Dict[str, Any]) -> None:
        """Registra eventos relevantes para auditoria LIVE (DNA Sniper)."""
        try:
            with self.config.debug_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Falha em gravar live debug jsonl: %s", e)

    def _check_correlation_guard(self, symbol: str) -> bool:
        """DNA Sniper: Evita abrir múltiplas posições no mesmo grupo de correlação."""
        for group_name, symbols in CORR_GROUPS.items():
            if symbol in symbols:
                for open_sym in self._open.keys():
                    if open_sym in symbols and open_sym != symbol:
                        logger.warning(
                            "🛡️ Correlation guard: %s bloqueado (já existe %s no grupo %s)",
                            symbol, open_sym, group_name
                        )
                        self._append_debug({
                            "ts": time.time(),
                            "event": "correlation_guard_block",
                            "symbol": symbol,
                            "existing_symbol": open_sym,
                            "group": group_name,
                        })
                        return False
        return True

    def _persist(self) -> None:
        try:
            payload = {
                "updated_at": _utc_iso(),
                "current_capital": self.current_capital,
                "initial_capital": self.initial_capital,
                "peak_capital": self.peak_capital,
                "capital_history": self._capital_history,
                "open": list(self._open.values()),
                "closed": self._closed[-self._closed_max :],
            }
            tmp = self.config.json_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.config.json_path)
        except OSError as e:
            logger.error("Falha ao persistir live state: %s", e)

    def _calculate_dynamic_sl_tp(
        self,
        symbol: str,
        entry_price: float,
        market_data: Optional[Dict[str, Dict]] = None,
    ) -> tuple[float, float]:
        """
        DNA Sniper AUTO-PILOT: Calcula SL/TP dinamicamente baseado em ATR.
        
        Lógica:
        - SL = 1.5x ATR abaixo do entry
        - TP = 3x SL (Risk:Reward 3:1)
        - Fallback: se ATR não disponível, usa config padrão
        
        Returns:
            (sl_pct, tp_pct) em formato decimal (ex: 0.015 = 1.5%)
        """
        try:
            if market_data and symbol in market_data:
                atr = market_data[symbol].get("atr", 0.0)
                if atr > 0:
                    # SL = 1.5x ATR
                    sl_distance = atr * 1.5
                    sl_pct = sl_distance / entry_price
                    
                    # TP = 3x SL (R:R 3:1)
                    tp_pct = sl_pct * 3.0
                    
                    # Limites de segurança
                    sl_pct = max(0.005, min(sl_pct, 0.03))  # Entre 0.5% e 3%
                    tp_pct = max(0.015, min(tp_pct, 0.15))  # Entre 1.5% e 15%
                    
                    logger.info(
                        "🤖 AUTO-PILOT %s: ATR=%.4f → SL=%.2f%% TP=%.2f%% (R:R 3:1)",
                        symbol,
                        atr,
                        sl_pct * 100,
                        tp_pct * 100,
                    )
                    
                    return (sl_pct, tp_pct)
        except Exception as e:
            logger.warning("Erro ao calcular SL/TP dinâmico para %s: %s", symbol, e)
        
        # Fallback: usa config padrão
        logger.debug("AUTO-PILOT %s: usando config padrão (ATR indisponível)", symbol)
        return (self.config.sl_pct, self.config.tp_pct)

    def open_long(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        notional_usdt: float,
        usdt_margin: float,
        leverage: int,
        signal: Optional[Dict[str, Any]] = None,
        auto_pilot: bool = False,
        market_data: Optional[Dict[str, Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Registra abertura de trade LIVE com validações do DNA do Sniper.
        
        Args:
            auto_pilot: Se True, calcula SL/TP dinamicamente baseado em ATR
            market_data: Dados de mercado para cálculo de ATR (opcional)
        """
        now = time.time()

        # DNA Sniper: Validação de max_open_positions
        if len(self._open) >= self.config.max_open_positions:
            logger.warning(
                "🛡️ Max posições atingido (%d/%d) — %s ignorado por proteção global",
                len(self._open),
                self.config.max_open_positions,
                symbol,
            )
            self._append_debug({
                "ts": now,
                "event": "max_positions_block",
                "symbol": symbol,
                "open_count": len(self._open),
                "max_allowed": self.config.max_open_positions,
            })
            return None

        # DNA Sniper: Validação de max_open_per_symbol
        if symbol in self._open:
            logger.warning("🛡️ Já existe posição aberta em %s", symbol)
            self._append_debug({
                "ts": now,
                "event": "duplicate_symbol_block",
                "symbol": symbol,
            })
            return None

        # DNA Sniper: Validação de Correlação (Evita over-exposure em setores)
        if not self._check_correlation_guard(symbol):
            return None

        # DNA Sniper: Validação de max_notional_usdt
        if notional_usdt > self.config.max_notional_usdt:
            logger.warning(
                "🛡️ Notional %.2f USDT acima do limite %.2f USDT — %s ignorado",
                notional_usdt,
                self.config.max_notional_usdt,
                symbol,
            )
            self._append_debug({
                "ts": now,
                "event": "max_notional_block",
                "symbol": symbol,
                "notional": notional_usdt,
                "max_allowed": self.config.max_notional_usdt,
            })
            return None

        # Fee de entrada (taker fee)
        opening_fee = notional_usdt * self.config.fee_pct

        # DNA Sniper: Captura métricas para cálculo dinâmico (Paridade Paper)
        entry_metrics = capture_metrics(symbol, market_data) if market_data else {}

        if auto_pilot:
            # DNA Sniper AUTO-PILOT: Calcula SL/TP dinamicamente baseado em ATR
            sl_pct, tp_pct = self._calculate_dynamic_sl_tp(symbol, entry_price, market_data)
            self._append_debug({
                "ts": now,
                "event": "auto_pilot_sl_tp_calculated",
                "symbol": symbol,
                "entry_price": entry_price,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "atr": market_data.get(symbol, {}).get("atr", 0.0) if market_data else 0.0,
            })
        else:
            # DNA Sniper: SL/TP Dinâmico por Volatilidade e CVD (Paridade Paper)
            dyn_sl_pct = self.config.sl_pct
            dyn_tp_pct = self.config.tp_pct
            
            cvd_val = signal.get("cvd_1m", 0) if signal else 0
            if cvd_val > 50000: dyn_tp_pct *= 2.0
            elif cvd_val > 10000: dyn_tp_pct *= 1.5
            
            pc_5m = abs(entry_metrics.get("price_change:5m", 0) or 0)
            pc_1h = abs(entry_metrics.get("price_change:1h", 0) or 0)
            if pc_1h > 5.0: dyn_sl_pct *= 1.5
            elif pc_5m > 1.5: dyn_sl_pct *= 1.2
            
            if signal and signal.get("liq_cascade"):
                dyn_tp_pct *= 1.5
                dyn_sl_pct *= 0.8
                
            sl_pct = dyn_sl_pct
            tp_pct = dyn_tp_pct

        trade = {
            "id": _new_id(symbol),
            "symbol": symbol,
            "side": "LONG",
            "status": "open",
            "entry": {
                "time": now,
                "time_iso": _utc_iso(now),
                "price": entry_price,
                "quantity": quantity,
                "notional_usdt": notional_usdt,
                "initial_notional_usdt": notional_usdt,
                "usdt_margin": usdt_margin,
                "initial_usdt_margin": usdt_margin,
                "leverage": leverage,
                "realized_pnl_usdt": -opening_fee,  # Começa negativo pela taxa
                "fee_usdt": opening_fee,
                "signal": signal or {},
                "auto_pilot": auto_pilot,  # DNA Sniper: Flag para auditoria
            },
            "targets": {
                "sl_price": entry_price * (1 - sl_pct),
                "tp_price": entry_price * (1 + tp_pct),
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "auto_pilot": auto_pilot,  # DNA Sniper: Registra modo usado
            },
            "breakeven_partial_closed": False,  # DNA Sniper: Flag para controle do fechamento parcial
            "breakeven_sl_moved": False,  # DNA Sniper: Flag para garantir que SL→breakeven aconteça só 1x
            "live": {
                "last_price": entry_price,
                "last_update": now,
                "pnl_pct": 0.0,
                "pnl_usdt": 0.0,
                "funding_fee_usdt": 0.0,
                "duration_sec": 0,
                "mfe_pct": 0.0,
                "mae_pct": 0.0,
            },
            "exit": None,
            "quality": {
                "favorable_early": False,
                "notes": "",
                "decay_milestones_persisted": [],  # DNA Sniper: Para rastrear marcos de decay
            },
        }

        self._open[symbol] = trade
        self._persist()

        logger.info(
            "🔴 LIVE OPEN %s @ %.4f | Qty: %.4f | Margin: %.2f USDT | Fee: %.4f USDT | Notional: %.2f USDT",
            symbol,
            entry_price,
            quantity,
            usdt_margin,
            opening_fee,
            notional_usdt,
        )

        return trade

    def _handle_partial_breakeven(
        self,
        trade: Dict[str, Any],
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """DNA Sniper P1: Fecha parcial no breakeven para proteger capital."""
        if trade.get("breakeven_partial_closed"):
            return None
        
        partial_pct = self.config.partial_tp_breakeven_pct
        if partial_pct <= 0:
            return None
        
        entry_price = trade["entry"]["price"]
        fee_entry = trade["entry"]["fee_usdt"]
        notional = trade["entry"]["notional_usdt"]
        
        # Breakeven = entry_price + fees
        breakeven_price = entry_price * (1 + (fee_entry / notional))
        
        if current_price >= breakeven_price:
            trade["breakeven_partial_closed"] = True
            self._append_debug({
                "ts": time.time(),
                "event": "partial_breakeven_triggered",
                "symbol": trade["symbol"],
                "entry_price": entry_price,
                "breakeven_price": breakeven_price,
                "current_price": current_price,
                "partial_pct": partial_pct,
            })
            
            # Retorna info para o Sniper executar o fechamento parcial
            return {
                "symbol": trade["symbol"],
                "partial_pct": partial_pct,
                "reason": "breakeven",
            }

        # SPRINT 12.190: Real PTP (Partial Take Profit em Lucro) - Paridade com Paper
        # AUDITORIA BRUTAL 2026-06-02: DNA PTP DESABILITADO TEMPORARIAMENTE
        # Motivo: Interfere com trailing delay de 60s (fecha trades prematuramente)
        # TODO: Reabilitar após validar trailing stop puro no Paper
        # pnl_pct = trade["live"].get("pnl_pct", 0.0)
        # if pnl_pct >= self.config.tp_partial_roi and not trade.get("tp_partial_done", False):
        #     trade["tp_partial_done"] = True
        #     self._append_debug({
        #         "ts": time.time(),
        #         "event": "partial_tp_triggered",
        #         "symbol": trade["symbol"],
        #         "pnl_pct": pnl_pct,
        #         "partial_pct": self.config.tp_partial_pct
        #     })
        #
        #     # Ajusta SL para entrada + 1% (Locking Profit)
        #     entry_price = trade["entry"]["price"]
        #     # Nota: O Sniper atualizará a ordem real na Binance
        #     trade["targets"]["sl_price"] = max(trade["targets"]["sl_price"], entry_price * 1.01)
        #
        #     return {
        #         "symbol": trade["symbol"],
        #         "partial_pct": self.config.tp_partial_pct,
        #         "reason": "partial_tp_roi",
        #         "new_sl": trade["targets"]["sl_price"]
        #     }
        
        return None

    def _update_trailing_sl(
        self,
        trade: Dict[str, Any],
        current_price: float,
        market_data: Optional[Dict[str, Dict]] = None
    ) -> Optional[float]:
        """DNA Sniper P1: Atualiza SL baseado em swing low."""
        if not self.config.sl_trailing_swing_low:
            return None
        
        symbol = trade["symbol"]
        entry_price = trade["entry"]["price"]
        entry_time = trade["entry"]["time"]
        current_sl = trade["targets"]["sl_price"]
        pnl_pct = trade["live"].get("pnl_pct", 0.0)
        current_mfe = trade["live"].get("mfe_pct", 0.0)
        
        # Verifica delay de ativação do trailing stop
        duration_sec = time.time() - entry_time
        trailing_delay_passed = duration_sec >= self.config.trailing_activation_delay_sec

        # min_hold_seconds: o SL não sobe acima do entry_price antes do tempo mínimo.
        # Paridade com paper_tracker — evita saída prematura em squeezes rápidos.
        min_hold = getattr(self.config, 'min_hold_seconds', 0)
        can_trailing = (min_hold == 0 or duration_sec >= min_hold)

        # Só ativa trailing após lucro mínimo (1%) E delay passado E min_hold respeitado
        if pnl_pct < 1.0 or not trailing_delay_passed or not can_trailing:
            return None

        # --- DNA Sniper: Trailing Baseado em MFE (ANÁLISE HONESTA v4.2) ---
        # DNA Sniper: Trailing Adaptativo por MFE (Paridade com Paper)
        # MFE > 3%: callback 50% (trava lucro mais rápido quando squeeze está ativo)
        # MFE <= 3%: callback padrão do preferences (deixa respirar)
        mfe_distance_pct = current_mfe / 100.0
        cb_base = getattr(self.config, 'trailing_stop_callback', 0.75)
        cb = 0.50 if current_mfe >= 3.0 else cb_base
        trailing_distance_pct = mfe_distance_pct * cb
        adaptive_sl = entry_price * (1 + trailing_distance_pct)
        
        # DNA Sniper: Paridade Live/Paper usando trailing_stop_distance_pct
        dist_pct = getattr(self.config, 'trailing_stop_distance_pct', 0.015)
        min_trailing_sl = entry_price * (1 + dist_pct)
        adaptive_sl = max(adaptive_sl, min_trailing_sl)

        # --- DNA Sniper: Opção 3 - Profit Guard (Locking) ---
        profit_guard_sl = 0.0
        if pnl_pct >= 10.0:
            profit_guard_sl = entry_price * 1.05 # Trava 5% de lucro real
        elif pnl_pct >= 5.0:
            profit_guard_sl = entry_price * 1.02 # Trava 2% de lucro real

        # Busca swing low como referência técnica (se market_data disponível)
        tech_sl = 0.0
        if market_data:
            d = market_data.get(symbol, {})
            tech_sl = d.get("swing_low_5m", 0.0)
        
        # --- DNA Sniper: Opção 4 - Classic Breakeven (Paridade com Paper) ---
        tp_pct_pct = trade["targets"]["tp_pct"] * 100.0
        breakeven_threshold_pct = tp_pct_pct * 0.85
        
        if pnl_pct >= breakeven_threshold_pct and not trade.get("breakeven_sl_moved", False):
            breakeven_sl = entry_price * 1.001
            if breakeven_sl > current_sl:
                trade["targets"]["sl_price"] = breakeven_sl
                trade["breakeven_sl_moved"] = True
                self._append_debug({
                    "ts": time.time(), "event": "classic_breakeven_triggered",
                    "symbol": symbol, "new_sl": breakeven_sl, "pnl_pct": pnl_pct
                })
                return breakeven_sl

        # O NOVO SL é o maior entre: Sl Adaptativo, Profit Guard, Swing Low ou o SL atual
        # Regra de Ouro: O SL NUNCA desce.
        # CORREÇÃO CRÍTICA: Removido 'entry_price' do max(). 
        # O SL só deve subir para o entry_price via lógica de Profit Guard (acima de 5% de lucro).
        new_sl = max(adaptive_sl, profit_guard_sl, tech_sl, current_sl)
        
        if new_sl > current_sl:
            trade["targets"]["sl_price"] = new_sl
            self._append_debug({
                "ts": time.time(),
                "event": "trailing_sl_updated",
                "symbol": symbol,
                "old_sl": current_sl,
                "new_sl": new_sl,
                "mfe_pct": current_mfe,
                "current_price": current_price,
            })
            return new_sl
        
        return None

    def update_position(
        self,
        symbol: str,
        current_price: float,
        funding_fee_usdt: float = 0.0,
        market_data: Optional[Dict[str, Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Atualiza PnL e funding fees de posição aberta com validações do DNA do Sniper."""
        trade = self._open.get(symbol)
        if not trade:
            return None

        entry_price = trade["entry"]["price"]
        quantity = trade["entry"]["quantity"]
        notional = trade["entry"]["notional_usdt"]

        duration_sec = time.time() - trade["entry"]["time"]

        # DNA Sniper: Validação de max_hold_seconds
        if self.config.max_hold_seconds > 0:
            if duration_sec >= self.config.max_hold_seconds:
                logger.warning(
                    "🛡️ Max hold atingido (%ds) — %s deve ser fechado por time-decay",
                    int(duration_sec),
                    symbol,
                )
                # Nota: O fechamento real é feito pelo sniper, aqui apenas registramos

        # PnL não realizado (mark-to-market)
        unrealized_pnl_usdt = quantity * (current_price - entry_price)
        funding_accumulated = trade["live"].get("funding_fee_usdt", 0.0) + funding_fee_usdt

        # PnL total (não realizado + funding fees)
        total_pnl_usdt = unrealized_pnl_usdt - funding_accumulated + trade["entry"].get("realized_pnl_usdt", 0.0)
        initial_margin = trade["entry"].get("initial_usdt_margin") or trade["entry"]["usdt_margin"]
        pnl_pct = (total_pnl_usdt / initial_margin * 100.0) if initial_margin > 0 else 0.0

        # DNA Sniper: Cálculo de MFE/MAE (Maximum Favorable/Adverse Excursion)
        current_mfe = trade["live"].get("mfe_pct", 0.0)
        if current_price > entry_price:
            mfe_pct = (current_price - entry_price) / entry_price * 100.0
            current_mfe = max(current_mfe, mfe_pct)
            trade["live"]["mfe_pct"] = current_mfe
        else:
            mae_pct = (entry_price - current_price) / entry_price * 100.0
            trade["live"]["mae_pct"] = max(trade["live"].get("mae_pct", 0.0), mae_pct)

        # Gate "squeeze_aborted": após 120s PnL < -1.5% e MFE < 0.5% → squeeze confirmou falso
        early_exit_reason = None
        if not trade.get("squeeze_abort_checked"):
            if duration_sec >= 120 and pnl_pct < -1.5 and current_mfe < 0.5:
                trade["squeeze_abort_checked"] = True
                early_exit_reason = "squeeze_aborted"
                logger.warning("🛡️ [LIVE] squeeze_aborted: %s | dur=%.0fs pnl=%.2f%% mfe=%.2f%%",
                               symbol, duration_sec, pnl_pct, current_mfe)

        # Gate "mae_guard": após 120s PnL < -2.0% e MFE < 1.0% → sai para evitar MAE profundo
        if early_exit_reason is None and not trade.get("mae_guard_checked"):
            if duration_sec >= 120 and pnl_pct < -2.0 and current_mfe < 1.0:
                trade["mae_guard_checked"] = True
                early_exit_reason = "mae_guard"
                logger.warning("🛡️ [LIVE] mae_guard: %s | dur=%.0fs pnl=%.2f%% mfe=%.2f%%",
                               symbol, duration_sec, pnl_pct, current_mfe)

        # F-14: Late mae_guard aos 240s — cobre janela entre 120s e trailing (180s)
        if early_exit_reason is None and not trade.get("mae_guard_late_checked"):
            if duration_sec >= 240 and pnl_pct < -3.0 and current_mfe < 2.0:
                trade["mae_guard_late_checked"] = True
                early_exit_reason = "mae_guard_late"
                logger.warning("🛡️ [LIVE] mae_guard_late: %s | dur=%.0fs pnl=%.2f%% mfe=%.2f%%",
                               symbol, duration_sec, pnl_pct, current_mfe)

        trade["live"]["last_price"] = current_price
        trade["live"]["last_update"] = time.time()
        trade["live"]["pnl_usdt"] = total_pnl_usdt
        trade["live"]["pnl_pct"] = pnl_pct
        trade["live"]["funding_fee_usdt"] = funding_accumulated
        _dur = time.time() - trade["entry"]["time"]
        trade["live"]["duration_sec"] = _dur
        trade["live"]["duration_s"] = _dur  # F-14: alias para scripts de análise do Brain

        # DNA Sniper P1: Partial breakeven
        partial_info = self._handle_partial_breakeven(trade, current_price)
        if partial_info:
            logger.info(
                "🎯 Partial breakeven triggered: %s @ %.4f (%.1f%% da posição)",
                symbol,
                current_price,
                partial_info["partial_pct"] * 100,
            )
            # Nota: O Sniper deve processar o fechamento parcial

        # DNA Sniper P1: Trailing stop
        new_sl = self._update_trailing_sl(trade, current_price, market_data)
        if new_sl:
            logger.info(
                "📈 Trailing SL updated: %s | Old: %.4f → New: %.4f",
                symbol,
                trade["targets"]["sl_price"],
                new_sl,
            )
            # Nota: O Sniper deve atualizar a ordem de SL na Binance

        self._persist()
        # Retorna dict com partial_info e early_exit_reason (ambos opcionais)
        if early_exit_reason:
            result = dict(partial_info) if partial_info else {}
            result["early_exit_reason"] = early_exit_reason
            return result
        return partial_info

    def _validate_close_price(
        self,
        symbol: str,
        close_price: float,
        market_data: Optional[Dict[str, Dict]] = None
    ) -> bool:
        """DNA Sniper P2: Valida preço de fechamento para evitar slippage extremo."""
        if not market_data:
            return True  # Sem dados, permite fechamento
        
        stable_price = market_data.get(symbol, {}).get("price")
        if not stable_price or stable_price <= 0:
            return True  # Sem preço estável, permite fechamento
        
        # Rejeita se divergência > 2%
        divergence = abs(close_price - stable_price) / stable_price
        if divergence > 0.02:
            self._append_debug({
                "ts": time.time(),
                "event": "close_price_rejected",
                "symbol": symbol,
                "close_price": close_price,
                "stable_price": stable_price,
                "divergence_pct": divergence * 100,
            })
            logger.warning(
                "🛡️ Close price rejected: %s | Close: %.4f | Stable: %.4f | Div: %.2f%%",
                symbol,
                close_price,
                stable_price,
                divergence * 100,
            )
            return False
        
        return True

    def close_position(
        self,
        symbol: str,
        close_price: float,
        close_reason: str = "sl_tp",
        market_data: Optional[Dict[str, Dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fecha posição LIVE e calcula PnL final."""
        trade = self._open.get(symbol)
        if not trade:
            return None

        # DNA Sniper P2: Valida para log, mas SEMPRE fecha para manter paridade com a Exchange
        self._validate_close_price(symbol, close_price, market_data)

        entry_price = trade["entry"]["price"]
        quantity = trade["entry"]["quantity"]
        notional = trade["entry"]["notional_usdt"]
        margin = trade["entry"]["usdt_margin"]

        # PnL de preço
        price_pnl_usdt = quantity * (close_price - entry_price)

        # Fee de saída (taker fee)
        closing_fee = notional * self.config.fee_pct

        # Funding fees acumulados
        funding_fees = trade["live"].get("funding_fee_usdt", 0.0)

        # PnL total = preço - fees - funding
        total_pnl_usdt = price_pnl_usdt - trade["entry"].get("fee_usdt", 0.0) - closing_fee - funding_fees
        pnl_pct = (total_pnl_usdt / margin * 100.0) if margin > 0 else 0.0

        # ROI (retorno sobre capital inicial)
        roi_pct = (total_pnl_usdt / self.initial_capital * 100.0) if self.initial_capital > 0 else 0.0

        now = time.time()
        duration_sec = now - trade["entry"]["time"]

        trade["exit"] = {
            "time": now,
            "time_iso": _utc_iso(now),
            "price": close_price,
            "reason": close_reason,
            "duration_sec": duration_sec,
            "pnl_usdt": total_pnl_usdt,
            "pnl_pct": pnl_pct,
            "roi_pct": roi_pct,
            "fee_usdt": closing_fee,
            "funding_fee_usdt": funding_fees,
            "total_fees_usdt": trade["entry"].get("fee_usdt", 0.0) + closing_fee + funding_fees,
        }
        trade["status"] = "closed"

        # Atualiza capital
        self.current_capital += total_pnl_usdt
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        self._capital_history.append({
            "ts": now,
            "capital": self.current_capital,
        })

        # Move para closed
        self._closed.append(trade)
        del self._open[symbol]

        # Persiste
        self._persist()
        self._append_closed_jsonl(trade)

        logger.info(
            "🟢 LIVE CLOSE %s @ %.4f | PnL: %.2f USDT (%.2f%%) | ROI: %.2f%% | Fees: %.4f USDT | Funding: %.4f USDT | Tempo: %ds",
            symbol,
            close_price,
            total_pnl_usdt,
            pnl_pct,
            roi_pct,
            trade["exit"]["total_fees_usdt"],
            funding_fees,
            int(duration_sec),
        )

        return trade

    def _append_closed_jsonl(self, trade: Dict[str, Any]) -> None:
        try:
            with self.config.closed_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(trade, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.error("Falha ao gravar live closed jsonl: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Calcula estatísticas de trades LIVE (e compatibiliza com Telegram relatórios 1h/diário)."""
        closed_trades = self._closed
        if not closed_trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "win_rate_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "total_pnl_usdt": 0.0,
                "avg_pnl_pct": 0.0,
                "total_fees_usdt": 0.0,
                "total_funding_usdt": 0.0,
                "avg_duration_sec": 0.0,
                "roi_pct": 0.0,
            }

        total_trades = len(closed_trades)
        wins = sum(1 for t in closed_trades if t.get("exit", {}).get("pnl_usdt", 0) > 0)
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

        total_pnl = sum(t.get("exit", {}).get("pnl_usdt", 0) for t in closed_trades)
        avg_pnl_pct = sum(t.get("exit", {}).get("pnl_pct", 0) for t in closed_trades) / total_trades

        total_fees = sum(t.get("exit", {}).get("total_fees_usdt", 0) for t in closed_trades)
        total_funding = sum(t.get("exit", {}).get("funding_fee_usdt", 0) for t in closed_trades)

        avg_duration = sum(t.get("exit", {}).get("duration_sec", 0) for t in closed_trades) / total_trades

        roi_pct = ((self.current_capital - self.initial_capital) / self.initial_capital * 100.0) if self.initial_capital > 0 else 0.0

        # max_drawdown_pct a partir do capital_history (em %)
        peak = self.initial_capital
        max_drawdown_pct = 0.0
        for entry in self._capital_history:
            cap = float(entry.get("capital", self.current_capital))
            if cap > peak:
                peak = cap
            if peak > 0:
                dd = (peak - cap) / peak * 100.0
                if dd > max_drawdown_pct:
                    max_drawdown_pct = dd

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "win_rate_pct": win_rate,  # compat com TelegramAlert
            "max_drawdown_pct": max_drawdown_pct,
            "total_pnl_usdt": total_pnl,
            "avg_pnl_pct": avg_pnl_pct,
            "total_fees_usdt": total_fees,
            "total_funding_usdt": total_funding,
            "avg_duration_sec": avg_duration,
            "roi_pct": roi_pct,
        }

    def get_kelly_risk(
        self, 
        base_risk_pct: float = 0.05, 
        min_trades: int = 10, 
        trades_1m: Optional[int] = None,
        score: float = 0.0,
        is_high_quality: bool = False
    ) -> float:
        """
        SPRINT 12.21: Kelly Criterion (Quarter-Kelly) para modo LIVE.
        SPRINT 13.2: Aplica decaimento de risco baseado em atividade HFT.
        """
        kelly_risk = calculate_kelly_risk(self._closed, base_risk_pct, min_trades, score=score, is_high_quality=is_high_quality)
        if trades_1m is not None:
            return calculate_dynamic_risk_with_hft(kelly_risk, trades_1m)
        return kelly_risk

    def get_snapshot(self) -> Dict[str, Any]:
        """Retorna snapshot completo para o dashboard + compatibilidade Telegram (1h/diário)."""
        snap: Dict[str, Any] = {
            "open": list(self._open.values()),
            "closed": self._closed[-50:],  # Últimos 50 trades
            "stats": self.get_stats(),
            "capital": {
                "current": self.current_capital,
                "initial": self.initial_capital,
                "peak": self.peak_capital,
                "history": self._capital_history[-100:],  # Últimos 100 pontos
            },
        }

        # TelegramAlert espera chaves no nível raiz:
        # - current_capital
        # - peak_capital
        snap["current_capital"] = self.current_capital
        snap["peak_capital"] = self.peak_capital
        snap["initial_capital"] = self.initial_capital
        snap["capital_history"] = self._capital_history[-100:]

        return snap
