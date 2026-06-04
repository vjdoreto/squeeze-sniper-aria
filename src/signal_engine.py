"""Squeeze signal detection — separated from execution and data ingestion."""
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List, Set, Any, Counter as TypingCounter
from collections import Counter as PyCounter

from src.market_view import calculate_fit_score

logger = logging.getLogger("SignalEngine")


class SymbolTradeThrottler:
    """Impede múltiplas entradas no mesmo símbolo em curto intervalo."""
    
    def __init__(self, min_interval_seconds: int = 60):
        self.last_trade_time: Dict[str, float] = {}
        self.min_interval_seconds = min_interval_seconds
    
    def can_trade(self, symbol: str) -> bool:
        """Verifica se pode abrir trade no símbolo (respeita cooldown)."""
        now = time.time()
        last_trade = self.last_trade_time.get(symbol, 0)
        if now - last_trade < self.min_interval_seconds:
            return False
        return True
    
    def record_trade(self, symbol: str):
        """Registra que um trade foi aberto no símbolo."""
        self.last_trade_time[symbol] = time.time()
    
    def get_cooldown_remaining(self, symbol: str) -> float:
        """Retorna segundos restantes de cooldown (0 se não houver)."""
        now = time.time()
        last_trade = self.last_trade_time.get(symbol, 0)
        elapsed = now - last_trade
        remaining = self.min_interval_seconds - elapsed
        return max(0, remaining)


class SqueezeIgnition:
    """
    Detecta Squeeze Ignition — versão otimizada para 'ativo mais forte que BTC'.
    Critérios principais:
      - OI exponencial subindo
      - EXP vs BTC forte (ativo descolado de BTC)
      - CVD (fluxo de compra/venda) indicando entrada institucional (robôs liquidando shorts)
      - LSR caindo drasticamente (shorts entrando em pânico)
      - RSI forte (>55) confirmando momentum

    Métricas usadas em % de crescimento (delta percentual):
      - cvd_change_pct:5m  → % de mudança do CVD nos últimos 5 min
      - oi_change_pct:5m   → % de mudança do OI nos últimos 5 min
      - lsr_change_pct:5m  → % de mudança do LSR nos últimos 5 min
    """

    def __init__(
        self,
        min_exp: float = 0.1,
        min_oi_trend: float = 0.05,
        max_lsr_trend: float = -0.002,
        cooldown_seconds: int = 320,
        min_vol_1m: float = 0.0,
        min_rsi_5m: float = 48.0,
        min_exp_btc_for_btc_dump: float = 0.0,
        # Filtros % de crescimento (P1 — primary)
        min_cvd_change_pct: float = 3.5,
        min_oi_change_pct: float = 0.35,
        max_lsr_change_pct: float = -0.05,
        cvd_streak_min: int = 2,
        min_trades_1m: int = 2,
        max_bid_ask_spread: float = 0.2, # P3: Spread máximo permitido (0.2%)
        min_vol_adaptive_ratio: float = 0.7, # SPRINT 6.1: Volume 1h deve ser > 70% do volume 24h
        min_oi_accel: float = 0.0,
        blacklist: Optional[List[str]] = None,
        fit_score_min: float = 20.0,
        signal_mode: str = "conservative", # SPRINT 12: conservative | aggressive
        trade_throttle_seconds: int = 60, # Cooldown mínimo entre trades do mesmo símbolo
    ):
        self.min_exp = min_exp
        self.min_oi_trend = min_oi_trend
        self.max_lsr_trend = max_lsr_trend
        self._cooldown_seconds = cooldown_seconds
        self._last_signal: Dict[str, float] = {}
        self.min_vol_1m = min_vol_1m
        self.min_rsi_5m = min_rsi_5m
        self.min_exp_btc_for_btc_dump = min_exp_btc_for_btc_dump
        
        # Throttler para prevenir race condition
        self._trade_throttler = SymbolTradeThrottler(min_interval_seconds=trade_throttle_seconds)
        
        # SPRINT 12: Ajusta thresholds baseado no signal_mode
        self.refresh_thresholds(
            signal_mode=signal_mode,
            min_cvd_change_pct=min_cvd_change_pct,
            cvd_streak_min=cvd_streak_min,
            max_bid_ask_spread=max_bid_ask_spread,
            min_trades_1m=min_trades_1m,
            min_vol_adaptive_ratio=min_vol_adaptive_ratio,
            min_oi_accel=min_oi_accel,
            min_oi_change_pct=min_oi_change_pct,
            max_lsr_change_pct=max_lsr_change_pct,
            min_oi_trend=min_oi_trend,
            blacklist=blacklist,
            fit_score_min=fit_score_min
        )
        # CVD streak: contador de ciclos de CVD positivo consecutivos por símbolo
        self._cvd_streak: Dict[str, int] = {}
        self._last_cvd_sign: Dict[str, float] = {}

    def refresh_thresholds(self, signal_mode: str, min_cvd_change_pct: float, cvd_streak_min: int, max_bid_ask_spread: float, min_trades_1m: int, min_vol_adaptive_ratio: float, min_oi_accel: float, min_oi_change_pct: float, max_lsr_change_pct: float, min_oi_trend: float, blacklist: Optional[List[str]] = None, fit_score_min: float = 20.0) -> None:
        """SPRINT 12.85: Atualiza thresholds sem resetar a memória de sinais/streaks."""
        self.signal_mode = signal_mode.lower()
        if self.signal_mode == "aggressive":
            # Modo agressivo: thresholds mais flexíveis
            self.min_oi_change_pct = min_oi_change_pct * 0.5  # 50% mais flexível
            self.max_lsr_change_pct = max_lsr_change_pct * 0.5  # 50% mais permissivo (ex: -0.02 -> -0.01)
            self.min_oi_trend = min_oi_trend * 0.5  # 50% mais flexível
        else:
            # Modo conservador: usa thresholds originais
            self.min_oi_change_pct = min_oi_change_pct
            self.max_lsr_change_pct = max_lsr_change_pct
            self.min_oi_trend = min_oi_trend

        # --- DNA / Auditoria de refusals (explicabilidade) ---
        # Loga motivos de por que um símbolo foi refutado (return None) antes de virar signal.
        # Ajuda a calibrar thresholds sem ficar no escuro.
        self.refusal_log_enabled: bool = (
            os.getenv("REFUSAL_LOG_ENABLED", "1").strip().lower() in ("1", "true", "yes")
        )
        self.refusal_log_seconds: int = int(os.getenv("REFUSAL_LOG_SECONDS", "30"))
        self.refusal_log_path: Path = Path(
            os.getenv("REFUSAL_LOG_PATH", "logs/signal_refusals.jsonl")
        )
        self._refusal_last_ts: Dict[str, float] = {}
        self._last_ghost_reason: Dict[str, Dict] = {}
        self._quase_la_last_ts: Dict[str, float] = {} # SPRINT 6.14

        # SPRINT 12.1: Auditor de Sinais Bloqueados (Lei de Governança)
        self._refusal_counters: PyCounter[str] = PyCounter()
        self._refusal_window_start = time.time()
        self._refusal_lock = threading.Lock()
        self._total_analyzed: int = 0  # SPRINT 12.20: Contador de vazão total

        # Filtros de % de crescimento
        self.min_cvd_change_pct = min_cvd_change_pct
        self.cvd_streak_min = cvd_streak_min
        self.max_bid_ask_spread = max_bid_ask_spread
        self.min_trades_1m = min_trades_1m
        self.min_vol_adaptive_ratio = min_vol_adaptive_ratio
        self.min_oi_accel = min_oi_accel

        self.blacklist = set(blacklist or [])

        # DNA: gate do fit score (vem de preferences, não de .env).
        self.min_fit_score: float = float(fit_score_min)

    def _maybe_log_refusal(
        self,
        symbol: str,
        reason_code: str,
        extra: Dict,
    ) -> None:
        if not self.refusal_log_enabled:
            return

        now = time.time()

        # SPRINT 12.75: Incrementa estatísticas ANTES do rate-limit de log
        # Garante que a "Contagem" no Dashboard seja matematicamente exata.
        with self._refusal_lock:
            if now - self._refusal_window_start > 3600:
                self._refusal_counters.clear()
                self._refusal_window_start = now
            self._refusal_counters[reason_code] += 1

        key = f"{symbol}:{reason_code}"
        last = self._refusal_last_ts.get(key)

        # rate limit por symbol+reason
        if last is not None and (now - last) < self.refusal_log_seconds:
            return
        self._refusal_last_ts[key] = now

        # Sprint 5.6: Armazena o motivo para o Ghost Signal Log
        self._last_ghost_reason[symbol] = {
            "reason_code": reason_code,
            "details": extra,
            "ts": now
        }

        try:
            self.refusal_log_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"ts": now, "symbol": symbol, "reason_code": reason_code}
            payload.update(extra)
            with self.refusal_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # nunca pode quebrar o motor por logging
            return

    def get_refusal_stats(self) -> Dict[str, Any]:
        """Retorna os Top 5 motivos de recusa para o Dashboard."""
        with self._refusal_lock:
            total = sum(self._refusal_counters.values())
            # SPRINT 12.35: Limpeza de cache de recusados se a janela for muito antiga
            now = time.time()
            
            return {
                "total_blocked": total,
                "window_age_min": round((time.time() - self._refusal_window_start) / 60, 1),
                "top_motivos": dict(self._refusal_counters.most_common(5)),
                "total_analyzed": self._total_analyzed,
                "efficiency_pct": round((total / self._total_analyzed * 100), 2) if self._total_analyzed > 0 else 0.0
            }

    def get_ghost_info(self, symbol: str) -> Optional[Dict]:
        """Retorna o último motivo de recusa se for recente (< 30s)."""
        info = self._last_ghost_reason.get(symbol)
        if info and (time.time() - info["ts"]) < 30:
            return info
        return None

    def record_trade_opened(self, symbol: str) -> None:
        """Registra que um trade foi aberto no símbolo (para throttler)."""
        self._trade_throttler.record_trade(symbol)

    def analyze(
        self,
        symbol: str,
        data: Dict,
        score: Optional[int] = None,
        market_squeeze_level: float = 0.0,
        trading_mode: str = "live",
        state: Any = None,
    ) -> Optional[Dict]:
        trading_mode = str(trading_mode).strip().lower()
        d = data.get(symbol, {})
        if not d.get("price"):
            return None

        # Verifica throttler para prevenir race condition
        if not self._trade_throttler.can_trade(symbol):
            self._maybe_log_refusal(
                symbol,
                "trade_throttle_active",
                {
                    "cooldown_remaining_sec": self._trade_throttler.get_cooldown_remaining(symbol),
                    "min_interval_sec": self._trade_throttler.min_interval_seconds
                }
            )
            return None

        # SPRINT 12.20: Incrementa fluxo total para estatísticas do Dashboard
        self._total_analyzed += 1

        # SPRINT 6.50: Inicialização garantida de variáveis para evitar UnboundLocalError
        now = time.time()
        liq_cascade = d.get("liq_cascade", False)
        exp_btc = d.get("exp_btc:5m") or 0.0
        cvd_change_pct = d.get("cvd_change_pct:5m") or 0.0

        # SPRINT 12.200: MTF Alignment Gate (DNA Pilar 2)
        # Impede entrar em ignição de 5m se o 15m ou 1h estiverem em colapso real.
        exp_15m = d.get("exp:15m")
        exp_1h = d.get("exp:1h")
        
        # Se o macro (1h) estiver caindo forte (> -0.05), a ignição de 5m é provavelmente um "dead cat bounce"
        if exp_1h is not None and exp_1h < -0.05 and not liq_cascade:
            self._maybe_log_refusal(symbol, "mtf_1h_crash", {"exp_1h": exp_1h, "limit": -0.05})
            return None
            
        # Se o 15m estiver caindo forte (> -0.03), ignoramos o sinal de 5m por falta de suporte intermediário
        if exp_15m is not None and exp_15m < -0.03 and not liq_cascade:
            self._maybe_log_refusal(symbol, "mtf_15m_bleeding", {"exp_15m": exp_15m, "limit": -0.03})
            return None

        oi_change_pct = d.get("oi_change_pct:5m") or 0.0
        lsr_change_pct = d.get("lsr_change_pct:5m") or 0.0

        # is_high_quality computado aqui — antes do gate CVD — para que a relaxação
        # funcione corretamente em cascatas e sinais institucionais fortes.
        is_high_quality = (
            ((exp_btc or 0.0) > 0.03 and (oi_change_pct or 0) > 0.5) or
            ((oi_change_pct or 0) > 1.2 and (lsr_change_pct or 0) < -2.0) or
            liq_cascade
        )

        # --- SPRINT 11: Gating UTC (Daily Reset Window) ---
        # SPRINT 11.13: Ajuste Ultra-Sniper (5 min antes / 5 min depois)
        # Previne contaminação de slopes durante o reset diário do MetricStore.
        now_utc = datetime.now(timezone.utc)
        is_reset_window = (
            (now_utc.hour == 23 and now_utc.minute >= 55) or
            (now_utc.hour == 0  and now_utc.minute <= 5)
        )

        if is_reset_window or getattr(state, 'daily_reset_active', False):
            self._maybe_log_refusal(
                symbol,
                "daily_reset_window",
                {"hour": now_utc.hour, "min": now_utc.minute},
            )
            return None

        # --- Gating P3 (Spread / Liquidez Real) ---
        spread = d.get("bid_ask_spread")
        if spread is not None and spread > self.max_bid_ask_spread:
            self._maybe_log_refusal(
                symbol,
                "spread_too_high",
                {"spread": spread, "max": self.max_bid_ask_spread},
            )
            # SPRINT 12.1: Visibilidade de Spread no BotState para o Dashboard
            if state and hasattr(state, "update_symbol_meta"):
                state.update_symbol_meta(symbol, {
                    "spread_blocked": True,
                    "last_spread": spread
                })
            return None

        # --- Gating Vol-Adaptive (Sprint 6.1) ---
        # Bloqueia se o volume da última hora for muito baixo comparado com o volume de 24h.
        # Isso evita sinais em períodos de baixa liquidez, onde o preço pode ser manipulado.
        debug_mode = symbol == "BTCUSDT" or (d.get("exp:5m") or 0) > 0.3  # Logar moedas minimamente ativas
        
        # SPRINT 6.1: Só aplica o gating se o MetricStore já tiver klines suficientes (Warmup)
        # Em paper, relaxamos este gate para evitar "monte de recusas" em janelas de baixa liquidez
        # (objetivo: coletar mais amostras para auditoria).
        if trading_mode != "paper" and d.get("vol_3h_warmup"):
            vol_3h_avg = d.get("volume_3h_avg", 0.0)
            vol_24h = d.get("volume_24h", 0.0)
            if vol_24h > 0 and (vol_3h_avg / vol_24h) < self.min_vol_adaptive_ratio:
                self._maybe_log_refusal(
                    symbol,
                    "vol_adaptive_gating",
                    {"vol_3h_avg": vol_3h_avg, "vol_24h": vol_24h, "ratio": vol_3h_avg / vol_24h, "min_ratio": self.min_vol_adaptive_ratio},
                )
                if debug_mode: logger.debug("Refutado %s: Volume médio 3h muito baixo (%s) vs 24h (%s)", symbol, vol_3h_avg, vol_24h)
                return None

        # --- Fit score pré-gate (reduz gates desnecessários) ---
        # SPRINT 6.27: Usa score injetado pelo main.py para performance
        if score is None:
            score = calculate_fit_score(d)

        if score < self.min_fit_score:
            self._maybe_log_refusal(
                symbol,
                "score_below_threshold",
                {
                    "score": score,
                    "min_required": self.min_fit_score,
                    "exp:5m": d.get("exp:5m"),
                    "oi_trend:5m": d.get("oi_trend:5m"),
                    "lsr_trend:5m": d.get("lsr_trend:5m"),
                },
            )
            return None

        # --- Gating P3 (Volume e Liquidez Real) ---
        # DNA/CVD precisa ser SIGNADO para streak (robôs comprando vs vendendo).
        # O gate de "volume mínimo" pode usar abs.
        cvd_delta_1m = d.get("volume_delta_1min", 0) or 0
        cvd_abs_1m = abs(cvd_delta_1m)

        # Se o volume for quase zero, ignoramos (moeda morta ou sem rastro institucional)
        if cvd_abs_1m < self.min_vol_1m:
            self._maybe_log_refusal(
                symbol,
                "cvd_abs_lt_min_vol",
                {"cvd_abs_1m": cvd_abs_1m, "min_vol_1m": self.min_vol_1m, "cvd_delta_1m": cvd_delta_1m},
            )
            return None

        # SPRINT 3 P2.4: CVD Gate - Exige compra institucional real (CVD positivo)
        # DNA: Squeeze legítimo = robôs comprando agressivamente (CVD > 0)
        # Relaxa para High Quality (cascata de liquidação ou OI explosivo)
        # AUDITORIA 2026-05-31: Compensação para CVD zero com indicadores muito fortes
        cvd_zero_compensated = False
        if cvd_delta_1m < 0:
            # Permite CVD zero/negativo SE outros indicadores forem MUITO fortes
            # Critérios: OI_change > 1% E LSR_trend < -2.0 E EXP > 0.05
            # Indica squeeze iminente mesmo sem fluxo CVD ainda
            if (
                oi_change_pct > 1.0 and
                lsr_change_pct < -2.0 and
                exp_btc > 0.05
            ):
                cvd_zero_compensated = True
                if debug_mode:
                    logger.info(
                        "CVD zero compensado para %s: OI_change=%.2f%%, LSR_change=%.2f%%, EXP_BTC=%.4f",
                        symbol, oi_change_pct, lsr_change_pct, exp_btc
                    )
            elif not is_high_quality:
                self._maybe_log_refusal(
                    symbol,
                    "cvd_negative_quarantine",
                    {"cvd_delta_1m": cvd_delta_1m, "is_high_quality": is_high_quality},
                )
                if debug_mode:
                    logger.debug("Refutado %s: CVD não positivo (%s) - sem compra institucional", symbol, cvd_delta_1m)
                return None

        # Atualiza streak sempre que temos um delta de CVD (alinha com o DNA do motor)
        self._update_cvd_streak(symbol, cvd_delta_1m)

        exp = d.get("exp:5m")
        oi_trend = d.get("oi_trend:5m")
        lsr_trend = d.get("lsr_trend:5m")
        oi_accel = d.get("oi_accel:5m")

        # Se qualquer métrica for None, não temos dados suficientes para gerar um sinal
        if exp is None or oi_trend is None or lsr_trend is None:
            self._maybe_log_refusal(
                symbol,
                "warmup_metrics_none",
                {"exp:5m": exp, "oi_trend:5m": oi_trend, "lsr_trend:5m": lsr_trend},
            )
            if debug_mode:
                logger.debug(
                    "Refutado %s: Métricas em warmup (exp=%s, oi=%s, lsr=%s)",
                    symbol,
                    exp,
                    oi_trend,
                    lsr_trend,
                )
            return None

        # --- LSR bruto pode demorar; fallback via lsr_trend ---
        # Se lsr bruto (lsr) ainda não chegou, mas o lsr_trend é forte o bastante,
        # permitimos o sinal (cache/history suficiente).
        lsr_val = d.get("lsr")
        if lsr_val is None or lsr_val == 0:
            # Se não temos rastro forte negativo, bloqueia.
            if lsr_trend is None or lsr_trend >= -0.01:
                self._maybe_log_refusal(
                    symbol,
                    "lsr_raw_missing_and_lsr_trend_weak",
                    {"lsr_trend": lsr_trend, "threshold": -0.01, "lsr_raw": lsr_val},
                )
                if debug_mode:
                    logger.debug(
                        "Refutado %s: LSR bruto ausente e lsr_trend fraco (%s)",
                        symbol,
                        lsr_trend,
                    )
                return None

        # DNA: o LSR não pode estar subindo (ruim para long). 
        # Um LSR estável (0.0) ou caindo é aceitável para a ignição.
        if lsr_trend > 0.0:
            self._maybe_log_refusal(
                symbol,
                "lsr_trend_positive",
                {"lsr_trend": lsr_trend, "threshold": 0.0},
            )
            if debug_mode: logger.debug("Refutado %s: LSR Trend subindo (%s)", symbol, lsr_trend)
            return None

        # SPRINT 11 / BUG 1: Garantia de funcionamento do RSI Gate
        # Fallback neutro 50.0 impede que o bot ignore sinais legítimos por delay de indicador
        # SPRINT 11.55: Signal Hydration (Anti-None Guard)
        # Garante que campos vitais nunca sejam None no disparo do Telegram
        rsi_5m_raw = d.get("rsi:5m")
        rsi_5m: float = float(rsi_5m_raw) if rsi_5m_raw is not None else 50.0
        rsi_15m = d.get("rsi:15m")
        rsi_1h = d.get("rsi:1h")
        ema_tr = d.get("ema_trend:5m") or 0
        hft_10s = int(d.get("last_trades_10s", 0))
        tlvl = d.get("trades_level", 0)
        liq_1m = d.get("liq_short_1m_stable", 0.0)

        last = self._last_signal.get(symbol)
        if last is not None and time.time() - last < self._cooldown_seconds:
            self._maybe_log_refusal(
                symbol,
                "cooldown_active",
                {"seconds_left": (self._cooldown_seconds - (time.time() - last))},
            )
            return None

        # --- Gating P2 (Macro Contexto e Dominância) ---
        btc_d = data.get("BTCUSDT", {})
        btcdom_d = data.get("BTCDOMUSDT", {})
        
        alt_pc_1h = d.get("price_change:1h")
        btc_pc_1h = btc_d.get("price_change:1h")
        btcdom_pc_1h = btcdom_d.get("price_change:1h")

        if trading_mode != "paper" and symbol not in ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]:
            # P2-D: Ativo mais Forte que BTC (relaxado em paper)
            # Se BTC cai e dominância sobe (dominância assassina), bloqueia em live.
            exp_btc = d.get("exp_btc:5m")
            if (
                btc_pc_1h is not None
                and btc_pc_1h < -0.3
                and exp_btc is not None
                and exp_btc < self.min_exp_btc_for_btc_dump
            ):
                self._maybe_log_refusal(
                    symbol,
                    "p2_btc_dump_gate_fail",
                    {"btc_pc_1h": btc_pc_1h, "exp_btc:5m": exp_btc, "min_exp_btc_for_btc_dump": self.min_exp_btc_for_btc_dump},
                )
                if debug_mode: logger.debug("Refutado %s: Fraco contra BTC (exp_btc=%s)", symbol, exp_btc)
                return None

            # Regra 1: Anti-Faca Caindo (Altcoin em queda livre > 4% na última 1h)
            if alt_pc_1h is not None and alt_pc_1h < -4.0:
                self._maybe_log_refusal(
                    symbol,
                    "p2_alt_down_gate",
                    {"alt_pc_1h": alt_pc_1h, "threshold": -4.0},
                )
                return None
                
            # Regra 2: Dominância Assassina (BTC cai e Dominância sobe = Altcoins sangram)
            if btc_pc_1h is not None and btcdom_pc_1h is not None:
                if btc_pc_1h < -0.5 and btcdom_pc_1h > 0.0:
                    self._maybe_log_refusal(
                        symbol,
                        "p2_btcdom_assassin_gate",
                        {"btc_pc_1h": btc_pc_1h, "btcdom_pc_1h": btcdom_pc_1h},
                    )
                    if debug_mode: logger.debug("Refutado %s: Dominância Assassina ativa", symbol)
                    return None

        # Confirmação por tendência: RSI 15m deve estar >= RSI 5m
        # (quando ambas métricas existirem) para evitar perda de momentum no TF maior.
        # Confirmação por tendência:
        # normalmente exigimos RSI15m >= RSI5m, mas permitimos tolerância
        # para não perder sinais "quase alinhados" (ex.: RSI15m um pouco abaixo).
        if rsi_5m is not None and rsi_15m is not None:
            # SPRINT 6.4: Se ambos estão em zona de força (>60), ignoramos a divergência.
            # SPRINT 6.6: Aumentado para 15 pontos para capturar ignição em mercados lentos.
            rsi_tolerance = 15.0

            if rsi_5m > 60 and rsi_15m > 60:
                pass # Ambos fortes = Squeeze saudável
            elif (rsi_15m - rsi_tolerance) > rsi_5m:
                self._maybe_log_refusal(
                    symbol,
                    "rsi15m_too_high_vs_5m",
                    {"rsi_5m": rsi_5m, "rsi_15m": rsi_15m, "rsi_tolerance": rsi_tolerance},
                )
                return None

        # RSI mínimo no 5m: bloqueia sinais em fraqueza de momentum
        if rsi_5m is not None and rsi_5m < self.min_rsi_5m:
            self._maybe_log_refusal(
                symbol,
                "rsi_lt_min_rsi_5m",
                {"rsi_5m": rsi_5m, "min_rsi_5m": self.min_rsi_5m},
            )
            return None

        # SPRINT 7.2 + P2.3: Anti-entrada tardia — bloqueia se o preço já moveu muito
        # Adicionado ANTES dos gates de confirmação (para rejeitar early)
        # P2.3: Aumentado de 1.5% para 2.0% baseado em análise de 52 rejeições
        pc_5m = d.get("price_change:5m") or 0
        pc_15m = d.get("price_change:15m") or 0

        # Se o preço já subiu 2.0%+ em 5m, o movimento está avançado
        # DNA: queremos a IGNIÇÃO, não a continuação
        if pc_5m > 2.0 and not liq_cascade:
            self._maybe_log_refusal(symbol, "entrada_tardia", {"pc_5m": pc_5m, "limit": 2.0})
            return None

        # Se o preço subiu 3%+ em 15m, é exaustão próxima
        if pc_15m > 3.0 and not liq_cascade:
            self._maybe_log_refusal(symbol, "exaustao_15m", {"pc_15m": pc_15m, "limit": 3.0})
            return None

        # --- Filtros P1: % de crescimento (delta percentual) ---
        # Métricas já inicializadas no topo da função para segurança de escopo.

        score_val = score if score is not None else (d.get("score") or 0)

        # --- Gating Suave: Funding Rate (Sprint 3A) ---
        funding = d.get("funding_rate", 0) or 0
        # Funding muito positivo (>0.05%) = longs pagando muito = cuidado
        if funding > 0.0005 and not is_high_quality:
            self._maybe_log_refusal(
                symbol,
                "funding_rate_high",
                {"funding_rate": funding, "threshold": 0.0005, "is_high_quality": is_high_quality},
            )
            if debug_mode: logger.debug("Refutado %s: Funding Rate alto (%s)", symbol, funding)
            return None

        # CVD como confirmação (não como gate hard):
        # removemos o filtro de cvd_change_pct para não zerar a taxa de sinais.
        if not is_high_quality and oi_change_pct is not None and oi_change_pct < self.min_oi_change_pct:
            self._maybe_log_refusal(
                symbol,
                "oi_change_lt_min",
                {"oi_change_pct:5m": oi_change_pct, "min_oi_change_pct": self.min_oi_change_pct, "is_high_quality": is_high_quality},
            )
            return None

        # DNA: a variação do LSR precisa ser negativa (caindo).
        if lsr_change_pct is not None:
            if lsr_change_pct >= 0:
                self._maybe_log_refusal(
                    symbol,
                    "lsr_change_not_negative",
                    {"lsr_change_pct:5m": lsr_change_pct},
                )
                if debug_mode: logger.debug("Refutado %s: LSR Change % não é negativo (%s)", symbol, lsr_change_pct)
                return None
            
            # Se não for High Quality, aplica o filtro restrito do usuário
            if not is_high_quality and lsr_change_pct > self.max_lsr_change_pct:
                self._maybe_log_refusal(
                    symbol,
                    "lsr_change_above_max",
                    {"lsr_change_pct:5m": lsr_change_pct, "max_lsr_change_pct": self.max_lsr_change_pct, "is_high_quality": is_high_quality},
                )
                return None

        # --- Filtros adicionais: trades massivos e CVD streak ---
        trades_1m = d.get("trades_count_1min", 0)
        cvd_streak = self._cvd_streak.get(symbol, 0)

        # Squeeze Detection logic (Relaxada se for High Quality DNA)
        # SPRINT 7.1: Relaxation baseada em FORÇAS INSTITUCIONAIS (OI + Liq), não em score geral
        # Score alto = sinal tardio confirmado → manter filtros
        # OI explosivo + liq_cascade = sinal precoce forte → relaxar para entrar cedo

        relax_factor = 1.0
        relax_label = "NORMAL"

        # Cascata de liquidação = sinal mais forte do DNA → entrada agressiva
        if liq_cascade:
            relax_factor = 0.6  # 40% relaxação: o squeeze JÁ começou de verdade
            relax_label = "RELAXED (CASCADE)"

        # OI explodindo sem preço ainda ter subido muito = ignição precoce
        elif (oi_change_pct or 0) > 2.0 and (exp or 0) < 0.04:
            relax_factor = 0.75  # 25% relaxação: OI confirmando mas preço ainda não subiu
            relax_label = "RELAXED (EARLY OI)"

        # is_high_quality normal (OI forte + LSR caindo)
        elif is_high_quality:
            relax_factor = 0.85  # 15% relaxação: sinal de qualidade mas sem urgência extra
            relax_label = "RELAXED (HQ DNA)"

        final_min_exp = self.min_exp * relax_factor
        final_min_oi_trend = self.min_oi_trend * relax_factor
        final_cvd_streak = max(1, self.cvd_streak_min - 1) if relax_factor < 0.9 else self.cvd_streak_min

        # Throttling de logs no terminal (Elite Ghost)
        if score >= 85:
            if (now - self._quase_la_last_ts.get(symbol, 0)) > 600:
                self._quase_la_last_ts[symbol] = now
                logger.info(
                    "🎯 ELITE GHOST: %s | Score %d | exp=%.4f (req %.4f) | oi_tr=%.4f (req %.4f) | lsr_tr=%.4f (max %.4f) | exp_btc=%.4f | streak=%d",
                    symbol, score, 
                    exp or 0, final_min_exp,
                    oi_trend or 0, final_min_oi_trend,
                    lsr_trend or 0, self.max_lsr_trend,
                    exp_btc or 0,
                    cvd_streak or 0
                )

        # SPRINT 6.32: Log de Divergência de Fluxo (Bias de Exaustão)
        # Alerta o operador se o preço sobe mas o dinheiro institucional está saindo.
        if exp >= 0.02 and oi_change_pct is not None and oi_change_pct < -0.5:
            if (now - self._quase_la_last_ts.get(f"{symbol}:div", 0)) > 600:
                self._quase_la_last_ts[f"{symbol}:div"] = now
                logger.warning("⚠️ DIVERGÊNCIA: %s Preço subindo (%.4f) mas OI caindo (%.2f%%). Possível exaustão.", symbol, exp, oi_change_pct)

        # SPRINT 7.4: EMA Trend como filtro de direção (eAssets style)
        # Bug Fix Sprint 8: Garantir que a tendência macro não bloqueie liquidações agressivas
        ema_tr = d.get("ema_trend:5m")
        if ema_tr is not None:
            # EMA trend fortemente negativo = tendência de baixa = anti-DNA LONG
            if ema_tr <= -3 and not liq_cascade:
                self._maybe_log_refusal(symbol, "ema_trend_bearish", {"ema_trend": ema_tr, "limit": -3})
                return None

        # CRITICAL FIX: Filtros endurecidos baseados em análise de logs
        # Análise mostrou CVD negativo e LSR_trend fraco passando, causando win rate 9.52%
        cvd_val = d.get("volume_delta_1min", 0)
        
        # Rejeitar CVD negativo (dinheiro saindo, não entrando)
        if cvd_val < 0 and not is_high_quality:
            self._maybe_log_refusal(
                symbol,
                "cvd_negative",
                {"cvd_1m": cvd_val, "is_high_quality": is_high_quality},
            )
            if debug_mode: logger.debug("Refutado %s: CVD negativo (%s)", symbol, cvd_val)
            return None
        
        # Rejeitar LSR_trend muito fraco (< -0.01 = shorts não estão realmente caindo)
        if lsr_trend > -0.01 and not is_high_quality:
            self._maybe_log_refusal(
                symbol,
                "lsr_trend_too_weak",
                {"lsr_trend": lsr_trend, "threshold": -0.01, "is_high_quality": is_high_quality},
            )
            if debug_mode: logger.debug("Refutado %s: LSR trend muito fraco (%s)", symbol, lsr_trend)
            return None
        
        # Rejeitar LSR_change muito fraco (> -0.05 = mudança insignificante)
        if lsr_change_pct is not None and lsr_change_pct > -0.05 and not is_high_quality:
            self._maybe_log_refusal(
                symbol,
                "lsr_change_too_weak",
                {"lsr_change_pct": lsr_change_pct, "threshold": -0.05, "is_high_quality": is_high_quality},
            )
            if debug_mode: logger.debug("Refutado %s: LSR change muito fraco (%s)", symbol, lsr_change_pct)
            return None

        if (
            exp >= final_min_exp
            and oi_trend >= final_min_oi_trend
            and lsr_trend <= self.max_lsr_trend
            and (trades_1m >= self.min_trades_1m or is_high_quality)
            and cvd_streak >= final_cvd_streak
            and (oi_accel is None or oi_accel >= self.min_oi_accel)
        ):
            self._last_signal[symbol] = time.time()
            exp_btc_val = d.get("exp_btc:5m") or 0.0
            cvd_val = d.get("volume_delta_1min", 0)
            liq_short_val = d.get("liq_short_1m", 0)
            trades_10s_val = int(d.get("last_trades_10s", 0))
            signal = {
                    "symbol": symbol,
                    "price": d["price"],
                    "exp": exp,
                    "oi_trend": oi_trend,
                    "lsr_trend": lsr_trend,
                    "oi_accel": oi_accel or 0.0,
                    "trades_1m": int(trades_1m),
                    "exp_btc": exp_btc_val,
                    "cvd_1m": cvd_val,
                    "liq_short_1m": liq_1m or liq_short_val,
                    "liq_cascade": liq_cascade,
                    "trades_10s": hft_10s or trades_10s_val,
                    "trades_level": tlvl,
                    "cvd_change_pct": cvd_change_pct or 0.0,
                    "oi_change_pct": oi_change_pct or 0.0,
                    "lsr_change_pct": lsr_change_pct or 0.0,
                    "relax_label": relax_label,
                    "cvd_streak": self._cvd_streak.get(symbol, 0),
                    "rsi_1h": rsi_1h or 50.0,
                    "ema_trend": ema_tr or 0,
                    "range_level": d.get("range_level:5m") or 0,
                    "score": score,
                    "timestamp": time.time(),
                }
            lsr_val = d.get("lsr")
            
            # --- SPRINT 13.4: Score Quality Gate ---
            # CORREÇÃO P0 v4.2.4: Score mínimo aumentado para 90
            # Análise mostrou que score 85 (PARTI) causou loss de -52%
            # Usa min_fit_score do construtor (linha 160) que vem do preferences.json
            if score < self.min_fit_score:
                self._maybe_log_refusal(
                    symbol,
                    "score_below_min",
                    {"score": score, "min_fit_score": self.min_fit_score, "is_high_quality": is_high_quality},
                )
                if debug_mode: logger.debug("Refutado %s: Score abaixo do mínimo (%d < %d)", symbol, score, self.min_fit_score)
                return None
            
            logger.info(
                "🔥 SQUEEZE IGNITION [%s]: %s | exp=%.2f | exp_btc=%.2f | oi_tr=%.2f | oi_acc=%.2f | lsr_tr=%.2f | LSR_RAW=%.2f | liq_short=%.0f | hft_10s=%d | cvd_chg=%.1f%% oi_chg=%.1f%% lsr_chg=%.1f%% streak=%d | trades_1m=%d | rsi5=%.1f",
                relax_label,
                symbol,
                exp,
                exp_btc_val or 0.0,
                oi_trend,
                oi_accel or 0.0,
                lsr_trend,
                lsr_val or 0.0,
                liq_short_val,
                trades_10s_val,
                cvd_change_pct or 0.0,
                oi_change_pct or 0.0,
                lsr_change_pct or 0.0,
                cvd_streak,
                trades_1m,
                rsi_5m or 0.0,
            )
            return signal
        else:
            # Gate final falhou — registra reason genérico com valores principais.
            self._maybe_log_refusal(
                symbol,
                "final_gate_fail",
                {
                    "exp": exp,
                    "min_exp": self.min_exp,
                    "oi_trend": oi_trend,
                    "min_oi_trend": self.min_oi_trend,
                    "lsr_trend": lsr_trend,
                    "max_lsr_trend": self.max_lsr_trend,
                    "trades_1m": trades_1m,
                    "min_trades_1m": self.min_trades_1m,
                    "cvd_streak": cvd_streak,
                    "cvd_streak_min": self.cvd_streak_min,
                    "lsr_change_pct": lsr_change_pct,
                    "oi_change_pct": oi_change_pct,
                    "cvd_change_pct": cvd_change_pct,
                    "funding_rate": funding,
                    "is_high_quality": is_high_quality,
                },
            )

            if debug_mode and exp > self.min_exp:
                logger.debug(
                    "Refutado %s: Falhou critério final (oi_tr=%.2f, lsr_tr=%.2f, streak=%d, trades=%d)",
                    symbol,
                    oi_trend,
                    lsr_trend,
                    cvd_streak,
                    trades_1m,
                )

        return None

    def _update_cvd_streak(self, symbol: str, cvd_1m: float) -> None:
        """Conta ciclos consecutivos de CVD positivo → detecta robôs de liquidação."""
        prev = self._last_cvd_sign.get(symbol, 0)
        curr = 1 if cvd_1m > 0 else (-1 if cvd_1m < 0 else 0)
        if curr == 0:
            self._cvd_streak[symbol] = 0
        elif curr == prev:
            self._cvd_streak[symbol] = self._cvd_streak.get(symbol, 0) + 1
        else:
            self._cvd_streak[symbol] = 1
        self._last_cvd_sign[symbol] = curr
