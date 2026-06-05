import json
import logging
import math
import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from binance import AsyncClient
from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
    FUTURE_ORDER_TYPE_STOP_MARKET,
    FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
)

if TYPE_CHECKING:
    from src.paper_tracker import PaperTradeTracker
    from src.telegram_alert import TelegramAlert

logger = logging.getLogger("Sniper")

_SNIPER_DEBUG_PATH = Path("logs/sniper_debug.jsonl")
_SNIPER_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _append_sniper_debug(record: Dict[str, Any]) -> None:
    try:
        with _SNIPER_DEBUG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # debug best-effort
        pass

class Sniper:
    """
    Executor de ordens para Binance Futures.
    Focado em entradas LONG durante Squeezes.
    """
    def __init__(
        self,
        client: AsyncClient,
        usdt_amount: float = 100.0,
        leverage: int = 10,
        risk_pct_per_trade: float = 0.05,
        trading_mode: str = "paper",
        sl_pct: float = 0.02,
        tp_pct: float = 0.04,
        max_open_positions: int = 3,
        max_hold_seconds: int = 0,
        sl_trailing_swing_low: bool = True,
        swing_low_tf: str = "5m",
        # SPRINT 11.28: Parâmetros específicos para o modo LIVE
        # Estes são os parâmetros ATIVOS do Sniper, que serão atualizados pelos handlers.
        # Não precisamos de live_usdt_amount, etc. O Sniper sempre reflete o estado atual.
        paper_tracker: Optional["PaperTradeTracker"] = None,
        live_tracker: Optional[Any] = None,  # SPRINT 12.20: LiveTracker para modo LIVE
        compound_enabled: bool = False, # SPRINT 12.18
        kelly_enabled: bool = False,  # SPRINT 12.21: Kelly Criterion para modo LIVE
        telegram: Optional['TelegramAlert'] = None, # SPRINT 12: Injeção para alertas LIVE
        auto_pilot: bool = False, # SPRINT 12.110: Fix attribute access issue
        risk_multiplier: float = 1.0, # SPRINT 12.156: Injetado pelo RiskManager
        signal_engine: Optional[Any] = None, # SPRINT 13: Para throttling de trades
    ):
        self.client = client
        # usdt_amount (LIVE): capital-base (ex.: "use 150 USDT da conta" para calcular margem por trade)
        self.usdt_amount = usdt_amount
        self.leverage = leverage
        self.risk_pct_per_trade = risk_pct_per_trade
        self.trading_mode = trading_mode.strip().lower()
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.max_open_positions = max_open_positions
        self.max_hold_seconds = max_hold_seconds
        self.sl_trailing_swing_low = sl_trailing_swing_low
        self.swing_low_tf = swing_low_tf
        self.paper_tracker = paper_tracker
        self.live_tracker = live_tracker  # SPRINT 12.20
        self.compound_enabled = compound_enabled
        self.kelly_enabled = kelly_enabled  # SPRINT 12.21
        self.telegram = telegram
        self.auto_pilot = auto_pilot
        self.risk_multiplier = risk_multiplier
        self.signal_engine = signal_engine  # SPRINT 13: Para throttling
        self._symbol_filters: Dict[str, Dict] = {}
        self._bracket_cache: Dict[str, float] = {}  # symbol → notionalCap para leverage atual

    async def _get_notional_cap(self, symbol: str) -> Optional[float]:
        """Retorna o notional máximo permitido para o símbolo no leverage atual via leverageBracket.
        Cacheado por símbolo — evita chamada REST a cada trade.
        Retorna None se não conseguir buscar (não bloqueia o trade)."""
        if symbol in self._bracket_cache:
            return self._bracket_cache[symbol]
        try:
            data = await self.client.futures_leverage_bracket(symbol=symbol)
            brackets = data[0].get("brackets", []) if data else []
            # Encontra o bracket onde leverage <= initialLeverage (limite máximo do tier)
            cap = None
            for b in sorted(brackets, key=lambda x: x["initialLeverage"]):
                if self.leverage <= b["initialLeverage"]:
                    cap = float(b["notionalCap"])
                    break
            if cap is not None:
                self._bracket_cache[symbol] = cap
                logger.debug("Bracket %s: notionalCap=%.0f (lev=%d)", symbol, cap, self.leverage)
            return cap
        except Exception as e:
            logger.warning("Erro ao buscar leverageBracket para %s: %s", symbol, e)
            return None

    def hydrate_filters(self, info: Dict[str, Any]) -> None:
        """SPRINT 12.86: Fix P3 - Popula cache de filtros no boot (Latência Zero)."""
        for s in info.get('symbols', []):
            sym = s['symbol']
            filters = {'minQty': '0.00000001', 'stepSize': '0.00000001', 'tickSize': '0.00000001'}
            for f in s.get('filters', []):
                if f['filterType'] == 'LOT_SIZE':
                    filters['minQty'] = f['minQty']
                    filters['stepSize'] = f['stepSize']
                elif f['filterType'] == 'PRICE_FILTER':
                    filters['tickSize'] = f['tickSize']
            self._symbol_filters[sym] = filters

    async def _get_symbol_filters(self, symbol: str) -> Dict:
        """Retorna filtros do cache ou faz fetch se ausente (Fallback)."""
        if symbol not in self._symbol_filters:
            try:
                info = await self.client.futures_exchange_info()
                self.hydrate_filters(info)
            except Exception as e:
                logger.error(f"Erro ao buscar filters para {symbol}: {e}")
                return {'minQty': '0.00000001', 'stepSize': '0.00000001', 'tickSize': '0.00000001'}
        return self._symbol_filters.get(symbol, {'minQty': '0.00000001', 'stepSize': '0.00000001', 'tickSize': '0.00000001'})

    async def _check_position(self, symbol: str) -> float:
        """Check existing position for symbol."""
        try:
            positions = await self.client.futures_position_information()
            for p in positions:
                if p['symbol'] == symbol:
                    return abs(float(p['positionAmt']))
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao checar posição {symbol}: {e}")
            return 0.0

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
        
        # SPRINT 12.2: Proteção contra snapping agressivo (> 10% de desvio)
        return res if abs(res - price) / price <= 0.10 else price

    async def prepare_account(self, symbol: str):
        """Configura alavancagem.""" # SPRINT 11.28: Usa a alavancagem ATIVA do Sniper
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=self.leverage)
        except Exception as e:
            if 'No need to change' not in str(e):
                logger.debug(f"Configuração leverage para {symbol}: {e}")

    async def close_position(self, symbol: str) -> None:
        """Fecha manualmente uma posição aberta e limpa ordens pendentes."""
        if self.trading_mode != "live":
            return

        try:
            positions = await self.client.futures_position_information()
            amt = 0.0
            entry_price = 0.0
            for p in positions:
                if p['symbol'] == symbol:
                    amt = float(p['positionAmt'])
                    entry_price = float(p.get('entryPrice', 0))
                    break

            if abs(amt) <= 0:
                logger.warning(f"⚠️ [SNIPER] Nenhuma posição aberta para {symbol} para fechar.")
                return

            side = SIDE_SELL if amt > 0 else SIDE_BUY
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=abs(amt),
                reduceOnly=True
            )
            await self.client.futures_cancel_all_open_orders(symbol=symbol)

            # SPRINT 12.20: Registrar fechamento no LiveTracker
            if self.live_tracker:
                close_price = float(order.get('avgPrice') or 0) or float(order.get('price', 0))
                self.live_tracker.close_position(
                    symbol=symbol,
                    close_price=close_price,
                    close_reason="manual_exit",
                )

            logger.info(f"🛑 [MANUAL] Posição {symbol} fechada.")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar posição LIVE {symbol}: {e}")

    async def close_all_positions(self):
        """Botão de Pânico: fecha TODAS as posições abertas na Binance Futures."""
        if self.trading_mode != "live":
            return
        
        try:
            positions = await self.client.futures_position_information()
            for p in positions:
                amt = float(p['positionAmt'])
                if abs(amt) > 0:
                    symbol = p['symbol']
                    await self.close_position(symbol)
                    logger.info(f"🛑 [STOP ALL] Posição {symbol} fechada.")
        except Exception as e:
            logger.error(f"❌ [STOP ALL] Erro ao fechar posições LIVE: {e}")

    async def _check_balance(self) -> float:
        """Retorna o saldo disponível em USDT (Futures)."""
        try:
            acc = await self.client.futures_account()
            return float(acc.get("totalMarginBalance", 0))
        except Exception as e:
            logger.error(f"Erro ao checar saldo: {e}")
            return 0.0

    async def execute_long(
        self,
        symbol: str,
        price: float,
        signal: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """
        Executa entrada LONG a mercado com SL/TP.
        Valida posição existente e quantidade correta.
        """
        _append_sniper_debug(
            {
                "ts": time.time(),
                "event": "sniper_execute_long_called",
                "symbol": symbol,
                "price": price,
                "trading_mode": self.trading_mode,
                "has_paper_tracker": self.paper_tracker is not None,
                "signal_is_none": signal is None,
                "market_data_is_none": market_data is None,
            }
        )

        if self.trading_mode == "paper":
            _append_sniper_debug(
                {
                    "ts": time.time(),
                    "event": "sniper_paper_branch",
                    "symbol": symbol,
                    "has_paper_tracker": self.paper_tracker is not None,
                    "signal_is_none": signal is None,
                    "market_data_is_none": market_data is None,
                }
            )

            if self.paper_tracker and signal is not None and market_data is not None:
                _append_sniper_debug(
                    {
                        "ts": time.time(),
                        "event": "sniper_calls_paper_open_long",
                        "symbol": symbol,
                    }
                )
                self.paper_tracker.open_long(symbol, price, signal, market_data)
                # SPRINT 13: Registra trade aberto no throttler
                if self.signal_engine:
                    self.signal_engine.record_trade_opened(symbol)
            else:
                logger.info(
                    "📋 PAPER LONG %s @ %.4f (sem tracker ou sem args)",
                    symbol,
                    price,
                )
            return

        # P0: 5.2 Sanity check antes de ordens LIVE
        if self.trading_mode != "live":
            logger.warning(f"🚫 [SEGURANÇA] Modo {self.trading_mode} ignorado no Sniper LIVE.")
            return

        if self.client is None:
            logger.error("❌ [SEGURANÇA] Cliente Binance é None no Sniper!")
            return

        try:
            # SPRINT 11.16: Audit Trail de Execução LIVE
            logger.warning("🚀 [EXECUTANDO LIVE] Ordem solicitada para %s. Verificando saldo e limites...", symbol)

            # SPRINT 11.24: Global Max Positions Guard for LIVE
            positions = await self.client.futures_position_information()
            active_count = sum(1 for p in positions if abs(float(p['positionAmt'])) > 0)
            if active_count >= self.max_open_positions:
                logger.warning(
                    "🚫 [SEGURANÇA] Max posições LIVE atingido (%d/%d). Ordem para %s abortada.",
                    active_count, self.max_open_positions, symbol
                )
                return

            # Check balance
            balance = await self._check_balance()
            
            # SPRINT 12.18: Mando do Operador - Lógica de Juros Compostos (Compounding)
            if self.compound_enabled:
                # Alinha sizing do Sniper com o capital persistido do LiveTracker (realized PnL)
                if self.live_tracker and hasattr(self.live_tracker, "current_capital"):
                    effective_capital = float(self.live_tracker.current_capital)
                    logger.info(
                        "📈 [COMPOUND] Ativo. Baseando margem no capital do LiveTracker: %.2f USDT",
                        effective_capital,
                    )
                else:
                    effective_capital = balance
                    logger.info(
                        "📈 [COMPOUND] Ativo. LiveTracker ausente. Baseando margem no saldo total: %.2f USDT",
                        effective_capital,
                    )
            else:
                # P0: 5.2 Sanity check antes de ordens LIVE - Garantir que saldo >= cota configurada
                if balance < self.usdt_amount:
                    logger.warning(
                        "🚫 [SEGURANÇA] Saldo LIVE insuficiente para capital operacional: %.2f (req: %.2f)",
                        balance, self.usdt_amount
                    )
                    return
                # Capital fixo (cota máxima)
                effective_capital = float(self.usdt_amount)
                logger.info("⚖️ [FIXED] Compound OFF. Usando cota máxima: %.2f USDT", effective_capital)

            # Risco por trade (ex.: 5% -> margem alvo = effective_capital * 0.05)
            # SPRINT 12.21: Kelly Criterion para modo LIVE
            if self.kelly_enabled and self.live_tracker:
                # SPRINT 13.2: Passa contagem de trades para aplicar penalidade de liquidez
                hft_trades = int(signal.get("trades_1m", 0)) if signal else 0
                score = float(signal.get("score", 0)) if signal else 0
                is_hq = signal.get("liq_cascade", False) if signal else False
                risk_pct = self.live_tracker.get_kelly_risk(
                    base_risk_pct=self.risk_pct_per_trade, trades_1m=hft_trades, score=score, is_high_quality=is_hq
                )
                logger.info(f"🎯 [KELLY] Risco dinâmico: {risk_pct * 100:.2f}% (base: {self.risk_pct_per_trade * 100:.2f}%)")
            else:
                risk_pct = self.risk_pct_per_trade

            # SPRINT 12.156: Aplica o multiplicador de governança (redução de 25% ou 50% se em DD)
            applied_risk = float(risk_pct) * self.risk_multiplier
            usdt_margin_target = effective_capital * applied_risk

            # Filtro mínimo de margem para evitar quantidades lixo
            if usdt_margin_target < 0.5:
                logger.warning(
                    "⚠️ [SNIPER] Margem alvo LIVE muito baixa: %.2f USDT (capital=%.2f, risk=%.4f).",
                    usdt_margin_target,
                    effective_capital,
                    self.risk_pct_per_trade,
                )
                return

            # Notional alvo = margem alvo * alavancagem
            notional_target = usdt_margin_target * float(self.leverage)

            # Valida bracket tier da Binance — cap de notional por símbolo/alavancagem
            notional_cap = await self._get_notional_cap(symbol)
            if notional_cap is not None and notional_target > notional_cap:
                logger.warning(
                    "⚠️ [BRACKET] Notional %.2f USDT excede cap do tier (%.0f USDT) para %s lev=%dx — ajustando",
                    notional_target, notional_cap, symbol, self.leverage,
                )
                notional_target = notional_cap
                usdt_margin_target = notional_target / float(self.leverage)

            # Log de sizing completo — aparece em todo trade para diagnóstico do Brain
            logger.info(
                "📐 [SIZING] %s | capital=%.2f | kelly_fraction=%.4f | risk_multiplier=%.2f | "
                "applied_risk=%.4f | margin_target=%.2f | notional_target=%.2f | notional_cap=%s",
                symbol,
                effective_capital,
                risk_pct,
                self.risk_multiplier,
                applied_risk,
                usdt_margin_target,
                notional_target,
                f"{notional_cap:.0f}" if notional_cap is not None else "N/A",
            )

            # Check existing position
            existing = await self._check_position(symbol)
            if existing > 0:
                logger.warning(f"🚫 [SEGURANÇA] Posição já aberta para {symbol}: {existing}")
                return

            await self.prepare_account(symbol)

            # Get quantity with proper rounding
            filters = await self._get_symbol_filters(symbol)
            quantity = self._round_quantity(notional_target / price, filters["stepSize"])
            
            # Validate minimum
            min_qty = float(filters['minQty'])
            if quantity < min_qty:
                logger.warning(f"🚫 [SEGURANÇA] Quantidade {quantity} abaixo do mínimo {min_qty} para {symbol}")
                return

            # Market buy
            order = await self.client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
                newClientOrderId=f"sniper_entry_{int(time.time())}"
            )
            
            avg = float(order.get('avgPrice') or 0)
            entry_price = avg if avg > 0 else price
            
            # SPRINT 11.34: Cálculo de Slippage Real (Executado vs Esperado)
            slippage_pct = ((entry_price / price) - 1) * 100 if price > 0 else 0
            slippage_color = "⚠️" if slippage_pct > 0.1 else "✅"
            logger.info(f"{slippage_color} [EXECUÇÃO] {symbol} | Fill: {entry_price:.4f} | Ideal: {price:.4f} | Slippage: {slippage_pct:.3f}%")
            
            # SPRINT 12.19: CORREÇÃO CRÍTICA - Validação de Preço de Liquidação
            # Busca mark_price (preço de liquidação) para validar SL
            try:
                mark_price_info = await self.client.futures_mark_price(symbol=symbol)
                mark_price = float(mark_price_info.get('markPrice', 0))
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível obter mark_price para {symbol}: {e}")
                mark_price = entry_price  # Fallback para entry_price

            # Cálculo de SL/TP Dinâmico
            if self.auto_pilot:
                # AUTO-PILOT: Usa ATR para calcular SL/TP
                logger.info("🤖 AUTO-PILOT ativo para %s — calculando SL/TP baseado em ATR", symbol)
                if market_data and symbol in market_data:
                    atr = market_data[symbol].get("atr", 0.0)
                    if atr > 0:
                        # SL = 1.5x ATR
                        sl_distance = atr * 1.5
                        dyn_sl_pct = sl_distance / entry_price
                        
                        # TP = 3x SL (R:R 3:1)
                        dyn_tp_pct = dyn_sl_pct * 3.0
                        
                        # Limites de segurança
                        dyn_sl_pct = max(0.005, min(dyn_sl_pct, 0.03))  # Entre 0.5% e 3%
                        dyn_tp_pct = max(0.015, min(dyn_tp_pct, 0.15))  # Entre 1.5% e 15%
                        
                        logger.info(
                            "🤖 AUTO-PILOT %s: ATR=%.4f → SL=%.2f%% TP=%.2f%% (R:R 3:1)",
                            symbol,
                            atr,
                            dyn_sl_pct * 100,
                            dyn_tp_pct * 100,
                        )
                    else:
                        # Fallback: usa config padrão
                        dyn_sl_pct = self.sl_pct
                        dyn_tp_pct = self.tp_pct
                        logger.warning("🤖 AUTO-PILOT %s: ATR indisponível, usando config padrão", symbol)
                else:
                    dyn_sl_pct = self.sl_pct
                    dyn_tp_pct = self.tp_pct
                    logger.warning("🤖 AUTO-PILOT %s: market_data indisponível, usando config padrão", symbol)
            else:
                # MANUAL: Usa lógica tradicional com ajustes de mercado
                dyn_sl_pct = self.sl_pct
                dyn_tp_pct = self.tp_pct
                
                if market_data:
                    d = market_data.get(symbol, {})
                    cvd = d.get("volume_delta_1min", 0) or 0
                    pc_1h = abs(d.get("price_change:1h", 0) or 0)
                    liq_cascade = d.get("liq_cascade", False)
                    liq_short = d.get("liq_short_1m", 0) or 0
                    
                    # SPRINT 12: Alinhamento total com DNA do PaperTracker
                    if cvd > 50_000:
                        dyn_tp_pct *= 2.0
                    elif cvd > 10000:
                        dyn_tp_pct *= 1.5
                    
                    if liq_cascade:
                        dyn_tp_pct *= 1.5
                        dyn_sl_pct *= 0.8

                    # Alta volatilidade → SL mais folgado para evitar violinos
                    if pc_1h > 5.0:
                        dyn_sl_pct *= 1.5
                    elif pc_1h > 2.0:
                        dyn_sl_pct *= 1.2

            # SPRINT 12.19: CORREÇÃO CRÍTICA - Validação de SL contra mark_price (liquidação)
            # Usar swing_low do market_data se disponível (DNA: stop abaixo do suporte)
            if market_data:
                d = market_data.get(symbol, {})
                sl_low = d.get("swing_low:5m")
                if sl_low and sl_low > 0 and sl_low < entry_price * (1 - dyn_sl_pct * 0.5):
                    # Swing low existe e está dentro do range de SL
                    sl_price = self._round_price(sl_low * 0.999, filters['tickSize'])
                else:
                    sl_price = self._round_price(entry_price * (1 - dyn_sl_pct), filters['tickSize'])
            else:
                sl_price = self._round_price(entry_price * (1 - dyn_sl_pct), filters['tickSize'])

            # SPRINT 12.19: VALIDAÇÃO CRÍTICA - SL não pode estar abaixo do mark_price (liquidação)
            # Adiciona margem de segurança de 0.5% para evitar liquidação por volatilidade
            min_safe_sl = mark_price * (1 - 0.005)  # 0.5% abaixo do mark_price
            if sl_price < min_safe_sl:
                logger.warning(
                    f"🚨 [SEGURANÇA] SL calculado ({sl_price:.4f}) abaixo do mark_price seguro ({min_safe_sl:.4f}). "
                    f"Ajustando para margem de segurança de 0.5%."
                )
                sl_price = self._round_price(min_safe_sl, filters['tickSize'])

            # SPRINT 12.19: VALIDAÇÃO CRÍTICA - SL não pode estar muito próximo do preço atual
            # Distância mínima de 1% do preço atual para evitar stop por ruído
            min_distance_sl = entry_price * (1 - 0.01)  # 1% abaixo do entry
            if sl_price > min_distance_sl:
                logger.warning(
                    f"🚨 [SEGURANÇA] SL calculado ({sl_price:.4f}) muito próximo do entry ({entry_price:.4f}). "
                    f"Ajustando para distância mínima de 1%."
                )
                sl_price = self._round_price(min_distance_sl, filters['tickSize'])

            # SPRINT 13.1: CRÍTICO - Governança: SL para LONG deve ser SEMPRE abaixo do preço de entrada.
            # Se, após todos os ajustes, o SL ainda estiver acima ou igual ao preço de entrada,
            # significa que o trade é inviável ou o risco é inaceitável. ABORTAR.
            if sl_price >= entry_price:
                logger.critical(
                    f"🚨 [SEGURANÇA FATAL] SL ({sl_price:.4f}) >= Preço de Entrada ({entry_price:.4f}) para {symbol}. "
                    "Trade abortado para evitar perda imediata. Revise a lógica de SL/TP ou condições de mercado."
                )
                return # Aborta a execução do trade

            tp_price = self._round_price(entry_price * (1 + dyn_tp_pct), filters['tickSize'])
            
            # SPRINT 11.35: Retry Loop para Ordens de Proteção (Segurança Crítica)
            for attempt in range(3):
                try:
                    await self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_STOP_MARKET,
                        stopPrice=sl_price,
                        closePosition=True,
                        newClientOrderId=f"sniper_sl_{int(time.time())}"
                    )
                    await self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                        stopPrice=tp_price,
                        closePosition=True,
                        newClientOrderId=f"sniper_tp_{int(time.time())}"
                    )
                    break # Sucesso, sai do loop de retry
                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"⚠️ Tentativa {attempt+1} de SL/TP falhou para {symbol}: {e}. Retentando...")
                        await asyncio.sleep(0.5)
                    else:
                        logger.critical(f"🚨 [PERIGO] Falha FATAL ao colocar SL/TP para {symbol} após 3 tentativas! Fechando posição imediatamente por segurança.")
                        await self.close_position(symbol)
            
            logger.info(f"🔒 PROTEÇÃO ATIVA (Server-Side): SL={sl_price:.4f} TP={tp_price:.4f} | MarkPrice={mark_price:.4f}")

            # SPRINT 12.20: Registrar trade no LiveTracker
            # DNA Sniper AUTO-PILOT: Passa flag auto_pilot e market_data para o tracker
            if self.live_tracker:
                self.live_tracker.open_long(
                    symbol=symbol,
                    entry_price=entry_price,
                    quantity=quantity,
                    notional_usdt=notional_target,
                    usdt_margin=usdt_margin_target,
                    leverage=self.leverage,
                    signal=signal,
                    auto_pilot=self.auto_pilot,
                    market_data=market_data,
                )
                # SPRINT 13: Registra trade aberto no throttler
                if self.signal_engine:
                    self.signal_engine.record_trade_opened(symbol)

        except Exception as e:
            logger.error(f"❌ Erro Sniper {symbol}: {e}")

    async def _trailing_stop_loop(self, base_interval: float = 30.0, engine=None, state=None):
        """
        SPRINT 12.19: Trailing Stop Loop para modo LIVE.
        Monitora posições abertas e ajusta SL dinamicamente (breakeven, swing_low).
        SPRINT 12.89: Adaptive Polling - Aumenta frequência se houver trade "quente".
        """
        logger.info("🔄 [TRAILING STOP] Loop iniciado (aguardando modo LIVE)")

        while True:
            current_wait = base_interval
            try:
                # Se iniciar em PAPER, o loop precisa continuar vivo.
                # Só executa quando o dashboard alternar para LIVE.
                if self.trading_mode != "live":
                    await asyncio.sleep(base_interval)
                    continue

                # SPRINT 12.210: Otimização REST (Pilar 3)
                # Prioriza posições vindas do State (WebSockets via User Data Stream) para evitar REST
                if state and hasattr(state, "_live_positions") and state._live_positions:
                    open_positions = state._live_positions
                else:
                    # Fallback REST apenas se o stream estiver offline
                    try:
                        positions = await self.client.futures_position_information()
                        open_positions = [p for p in positions if abs(float(p.get('positionAmt', 0) or p.get('size', 0))) > 0]
                    except Exception:
                        open_positions = []

                for pos in open_positions:
                    symbol = pos.get('symbol') or pos.get('s')
                    amt = float(pos.get('positionAmt') or pos.get('size') or 0)
                    if amt <= 0:  # Apenas LONG
                        continue

                    # SPRINT 12.210: Redução drástica de REST calls. Usa cache do Engine (WebSockets).
                    try:
                        if engine and symbol in engine.data and engine.data[symbol].get("price"):
                            current_price = float(engine.data[symbol]["price"])
                        else:
                            # Fallback REST se engine ainda estiver em warmup
                            mark_info = await self.client.futures_mark_price(symbol=symbol)
                            current_price = float(mark_info.get('markPrice', 0))
                        
                        entry_price = float(pos.get('entryPrice') or pos.get('entry_price') or 0)

                        if current_price <= 0 or entry_price <= 0:
                            continue

                        # SPRINT 12.88: Fetch filters uma vez por loop (Fix UnboundVariable + Performance)
                        filters = await self._get_symbol_filters(symbol)

                        # SPRINT 12.20: Atualiza LiveTracker com PnL atual
                        if self.live_tracker:
                            # SPRINT 12.210: Usa Funding Rate do rastro institucional (WebSocket/Poll centralizado)
                            funding_fee_usdt = 0.0
                            if engine and symbol in engine.data:
                                f_rate = engine.data[symbol].get("funding_rate", 0.0)
                                funding_fee_usdt = f_rate * (current_price * amt)
                            else:
                                try:
                                    f_rates = await self.client.futures_funding_rate(symbol=symbol, limit=1)
                                    f_rate = float(f_rates[-1].get("fundingRate", 0.0)) if f_rates else 0.0
                                    funding_fee_usdt = f_rate * (current_price * amt)
                                except Exception: pass

                            # DNA Sniper P1: Captura e executa gatilhos de proteção (Partial TP)
                            partial_info = self.live_tracker.update_position(
                                symbol=symbol,
                                current_price=current_price,
                                funding_fee_usdt=funding_fee_usdt,
                                market_data=engine.data if engine else None
                            )

                            # Gates de saída antecipada (squeeze_aborted / mae_guard)
                            if partial_info and partial_info.get("early_exit_reason"):
                                _reason = partial_info["early_exit_reason"]
                                logger.warning(
                                    "🛡️ [LIVE] Early exit triggered: %s → %s | Fechando posição",
                                    symbol, _reason
                                )
                                await self.close_position(symbol)
                                continue

                            if partial_info and partial_info.get("partial_pct"):
                                try:
                                    qty = self._round_quantity(amt * partial_info["partial_pct"], filters["stepSize"])
                                    if qty > 0:
                                        await self.client.futures_create_order(
                                            symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET,
                                            quantity=qty, reduceOnly=True,
                                            newClientOrderId=f"sniper_partial_{int(time.time())}"
                                        )
                                        logger.info(f"🎯 [LIVE] Partial Breakeven executado: {symbol} (-{partial_info['partial_pct']*100}%)")
                                except Exception as ep:
                                    logger.error(f"❌ Erro na execução parcial de {symbol}: {ep}")

                        # Busca ordens abertas para encontrar SL atual
                        open_orders = await self.client.futures_get_open_orders(symbol=symbol)
                        sl_order = None
                        for order in open_orders:
                            if order.get('type') == 'STOP_MARKET':
                                sl_order = order
                                break

                        if not sl_order:
                            continue

                        current_sl = float(sl_order.get('stopPrice', 0))
                        pnl_pct = (current_price - entry_price) / entry_price * 100
                        
                        # SPRINT 12.130: Opção 2 - Trailing Adaptativo baseado em MFE e Tempo
                        # Baseado no documento "Engenheiro e DNA do Sniper.md"
                        
                        # 1. Calcula MFE atual
                        current_mfe = pnl_pct # Simplificado para o loop
                        
                        # 2. Distância Base (2%)
                        base_distance = 0.02
                        
                        # 3. Multiplicador por MFE (quanto mais lucro, mais espaço para o squeeze respirar)
                        if current_mfe < 3.0:
                            mfe_mult = 1.0
                        elif current_mfe < 7.0:
                            mfe_mult = 1.3 # 30% mais largo
                        else:
                            mfe_mult = 1.6 # 60% mais largo
                            
                        # 4. Multiplicador por Tempo (trades longos precisam de stops técnicos mais largos)
                        # Nota: Precisaríamos da duração real aqui, usando 1.0 como padrão por ora
                        time_mult = 1.0 
                        
                        # Distância adaptativa final
                        adaptive_dist = base_distance * mfe_mult * time_mult
                        
                        # Novo preço de stop sugerido
                        suggested_sl = self._round_price(current_price * (1 - adaptive_dist), filters['tickSize'])

                        # SPRINT 12.19: Breakeven - move SL para entry + 0.1% quando atinge 70% do TP
                        tp_pct = self.tp_pct * 100
                        breakeven_threshold = tp_pct * 0.7

                        # SPRINT 12.131: Aumenta frequência para 5s se estiver em lucro forte (>5%)
                        if pnl_pct >= 5.0:
                            current_wait = 5.0

                        if pnl_pct >= breakeven_threshold and current_sl < entry_price * 1.001:
                            # Cancela SL atual e coloca novo SL em breakeven
                            await self.client.futures_cancel_order(symbol=symbol, orderId=sl_order['orderId'])
                            new_sl = self._round_price(entry_price * 1.001, filters['tickSize'])

                            await self.client.futures_create_order(
                                symbol=symbol,
                                side=SIDE_SELL,
                                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                                stopPrice=new_sl,
                                closePosition=True,
                                newClientOrderId=f"sniper_sl_breakeven_{int(time.time())}"
                            )
                            logger.info(f"🔄 [TRAILING STOP] {symbol} SL movido para Breakeven: {new_sl:.4f}")
                        
                        elif pnl_pct > 1.0:
                            # SPRINT 12.140: Profit Guard (Opção 3 do plano)
                            # Garante que trades com lucro forte nunca saiam no prejuízo ou zero.
                            profit_guard_sl = 0.0
                            if pnl_pct >= 10.0:
                                profit_guard_sl = self._round_price(entry_price * 1.05, filters['tickSize']) # Trava 5%
                            elif pnl_pct >= 5.0:
                                profit_guard_sl = self._round_price(entry_price * 1.02, filters['tickSize']) # Trava 2%
                            
                            # Escolhe o melhor SL: ou o Adaptativo (que segue o preço) ou o Profit Guard (que trava lucro)
                            candidate_sl = max(suggested_sl, profit_guard_sl)

                            # Proteção: Nunca coloca SL acima do preço atual - 0.5% (gap de segurança contra flash crash)
                            safe_max_sl = current_price * 0.995
                            final_target_sl = min(candidate_sl, safe_max_sl)
                            
                            # Se o novo alvo for superior ao SL atual na Binance, executa o ajuste
                            if final_target_sl > current_sl:
                                await self.client.futures_cancel_order(symbol=symbol, orderId=sl_order['orderId'])
                                await self.client.futures_create_order(
                                    symbol=symbol,
                                    side=SIDE_SELL,
                                    type=FUTURE_ORDER_TYPE_STOP_MARKET,
                                    stopPrice=final_target_sl,
                                    closePosition=True,
                                    newClientOrderId=f"sniper_sl_adaptive_{int(time.time())}"
                                )
                                log_type = "PROFIT GUARD" if final_target_sl == profit_guard_sl else "TRAILING ADAPTATIVO"
                                logger.info(f"📈 [{log_type}] {symbol} SL subiu para: {final_target_sl:.4f} (MFE: {current_mfe:.2f}%)")

                        # SPRINT 12.21: Swing Low Trailing (DNA do Sniper)
                        if self.sl_trailing_swing_low and engine:
                            d = engine.data.get(symbol, {})
                            swing_low = d.get(f"swing_low:{self.swing_low_tf}")
                            if swing_low and swing_low > 0 and swing_low < current_price:
                                base_sl_pct = self.sl_pct
                                swing_low_dist_pct = (entry_price - swing_low) / entry_price * 100.0

                                # Default SL percentual (antes de swing_low)
                                base_sl_price = self._round_price(
                                    entry_price * (1.0 - base_sl_pct),
                                    filters['tickSize'],
                                    up=False,
                                )

                                if swing_low_dist_pct >= 0.8:
                                    # swing_low pelo menos 0.8% abaixo da entrada: usar swing_low ajustado
                                    adjusted_sl = self._round_price(swing_low * 0.999, filters['tickSize'], up=False)
                                    if adjusted_sl > current_sl and adjusted_sl < current_price:
                                        await self.client.futures_cancel_order(symbol=symbol, orderId=sl_order['orderId'])
                                        await self.client.futures_create_order(
                                            symbol=symbol,
                                            side=SIDE_SELL,
                                            type=FUTURE_ORDER_TYPE_STOP_MARKET,
                                            stopPrice=adjusted_sl,
                                            closePosition=True,
                                            newClientOrderId=f"sniper_sl_swing_{int(time.time())}"
                                        )
                                        logger.info(
                                            f"📋 [TRAILING STOP] {symbol} SL movido para Swing Low ({self.swing_low_tf}): {adjusted_sl:.4f} (dist={swing_low_dist_pct:.2f}%)"
                                        )
                                else:
                                    # swing_low muito próximo (<0.8%): usa SL percentual padrão
                                    if current_sl > base_sl_price and current_sl < entry_price and base_sl_price < current_price:
                                        await self.client.futures_cancel_order(symbol=symbol, orderId=sl_order['orderId'])
                                        await self.client.futures_create_order(
                                            symbol=symbol,
                                            side=SIDE_SELL,
                                            type=FUTURE_ORDER_TYPE_STOP_MARKET,
                                            stopPrice=base_sl_price,
                                            closePosition=True,
                                            newClientOrderId=f"sniper_sl_default_{int(time.time())}"
                                        )
                                        logger.info(
                                            f"📋 [TRAILING STOP] {symbol} swing_low ignorado (<0.8%%) | SL padrão aplicado: {base_sl_price:.4f}"
                                        )

                    except Exception as e:
                        logger.warning(f"⚠️ Erro no trailing stop para {symbol}: {e}")

                await asyncio.sleep(current_wait)

            except Exception as e:
                logger.error(f"❌ Erro no trailing stop loop: {e}")
                await asyncio.sleep(base_interval)
