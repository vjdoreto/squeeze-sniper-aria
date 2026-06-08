import asyncio
import time
import logging
import math
import os
import re
import random
from typing import Any, Dict, List, Optional, Set, cast
from binance import AsyncClient, BinanceSocketManager
from dotenv import load_dotenv
from src.persistence import DailySnapshotLogger
from src.metric_engine import MetricStore

load_dotenv()

logger = logging.getLogger("DataEngine")
logger.setLevel(logging.DEBUG)

class DataEngine:
    """
    Motor de dados focado em Rastro Institucional.
    Monitora: AggTrades (CVD), Open Interest, Long/Short Ratio.
    """
    def __init__(
        self,
        symbols: List[str],
        top_n: int = 100,
        exchange_info: Optional[Dict] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        oi_poll_seconds: float = 8.0,
        skip_ticker_filter: bool = False,
        skip_bootstrap_prices: bool = False,
        volume_24h_refresh_seconds: float = 600.0,
    ):
        self.top_n = top_n
        self.symbols = [s.upper() for s in symbols]
        self._api_key = api_key or os.getenv("API_KEY")
        self._api_secret = api_secret or os.getenv("API_SECRET")
        self.oi_poll_seconds = oi_poll_seconds
        self._exchange_info = exchange_info
        self.skip_ticker_filter = skip_ticker_filter
        self.skip_bootstrap_prices = skip_bootstrap_prices
        self.volume_24h_refresh_seconds = volume_24h_refresh_seconds
        self._last_volume_24h_refresh: float = 0.0
        self.oi_concurrency = 12
        self.client: Optional[AsyncClient] = None
        self._api_sem: Optional[asyncio.Semaphore] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self.store: Optional[MetricStore] = None
        self.data: Dict[str, Dict] = {}
        self.running = True
        self._history_logger = DailySnapshotLogger()
        self._symbol_info: Dict[str, Dict] = {}
        self._last_lsr_fetch: Dict[str, float] = {}
        # Diagnóstico: quantos ciclos seguidos sem LSR bruto (lsr None) para cada símbolo
        self._lsr_none_cycles: Dict[str, int] = {}
        self._lsr_miss_count: Dict[str, int] = {}

        # SPRINT 5.9: Timers para reduzir carga de REST secundário
        self._last_funding_fetch: Dict[str, float] = {}
        self._last_depth_fetch: Dict[str, float] = {}

        # Antibans: pausa temporária de REST quando Binance retorna -1003
        self._rest_ban_until_ts: float = 0.0
        # Throttling REST (evita tempestade de requests e ban)
        self.oi_rest_interval_seconds: float = max(20.0, self.oi_poll_seconds * 3.0)   # OI menos frequente
        self.lsr_rest_interval_seconds: float = max(40.0, self.oi_poll_seconds * 5.0)  # LSR menos frequente
        # CORREÇÃO P0.1: LSR Proxy Agressivo (180s → 30s) para reduzir gaps de dados
        self.lsr_proxy_interval_dorment: float = 30.0                                 # Proxy agressivo (era 180s)
        # CORREÇÃO P1.4: Order Book Adaptativo (60s → 30s) para melhor responsividade
        self.depth_rest_interval_seconds: float = 30.0                                # Mais responsivo (era 60s)
        self._last_rest_ban_log_ts: float = 0.0
        self._rest_ban_log_throttle_seconds: float = 30.0
        # Para proxy LSR via futures_klines (também REST)
        self._last_lsr_proxy_fetch: Dict[str, float] = {}
        # Para OI (REST) por símbolo
        self._last_oi_fetch: Dict[str, float] = {}
        # SPRINT 6.10: Conjunto de símbolos prioritários para LSR oficial
        self._top_n_symbols: Set[str] = set()

        # SPRINT 11.9: Varredura Rotacional para Radar Global (Performance Extrema)
        self._rotational_index: int = 0
        self._batch_size_non_priority: int = 30

        self.last_data_ts: float = time.time() # SPRINT 11.32: Health Check

    def _ws_backoff(self, attempt: int) -> float:
        """
        Backoff exponencial com jitter para reconexão WS (anti-thundering herd).
        attempt=1 -> ~1s (com jitter); caps em 60s.
        """
        if attempt <= 0:
            attempt = 1
        base = 1.0
        max_delay = 60.0
        delay = min(max_delay, base * (2 ** (attempt - 1)))
        jitter = random.uniform(0, delay * 0.2)
        return delay + jitter

    def _rest_ban_active(self) -> bool:
        return time.time() < self._rest_ban_until_ts

    def is_healthy(self) -> bool:
        """SPRINT 11.32: Verifica se recebemos dados de mercado nos últimos 10s."""
        # Se o gap de dados for maior que 10s, consideramos conexão instável.
        return (time.time() - self.last_data_ts) < 10.0

    def _maybe_set_rest_ban_from_exception(self, exc: Exception) -> None:
        # Binance: "Way too many requests; IP(...) banned until <ms>. ..."
        msg = str(exc)
        m = re.search(r"banned until (\d+)", msg)
        if not m:
            return
        try:
            banned_until_ms = int(m.group(1))
            new_until = (banned_until_ms / 1000.0) + 5.0
            self._rest_ban_until_ts = max(self._rest_ban_until_ts, new_until)

            now = time.time()
            # Throttle do log: em ban storm, muitos requests falham e disparam spam.
            if (now - self._last_rest_ban_log_ts) >= self._rest_ban_log_throttle_seconds:
                self._last_rest_ban_log_ts = now
                logger.warning(
                    "⛔ REST ban detectado — pausa até %.0f (epoch)",
                    self._rest_ban_until_ts,
                )
        except Exception:
            return

    async def start(self):
        self.client = await AsyncClient.create(
            api_key=self._api_key,
            api_secret=self._api_secret,
        )
        # BinanceSocketManager repassa **ws_kwargs para websockets.connect().
        # SPRINT 9.5: estabilizar Kline WS batch (reduzir reconexões e gaps de dados)
        self.bsm = BinanceSocketManager(self.client)
        self.bsm.ws_kwargs = {
            "ping_interval": 20,
            "ping_timeout": 10,
            "open_timeout": 180.0,  # era 120.0
        }
        self._api_sem = asyncio.Semaphore(self.oi_concurrency)

        # Type guards para Pylance (runtime já garante essas inicializações)
        assert self.client is not None
        assert self.bsm is not None
        assert self._api_sem is not None

        # Filter top symbols by volume
        if not self.skip_ticker_filter:
            await self._filter_top_symbols()
        else:
            logger.warning("⏭️ skip_ticker_filter=True — não chama futures_ticker() para filtrar top symbols.")
            # Mantém self.symbols como veio do caller (já deve conter macros essenciais)
        self._init_data()
        if not self.skip_bootstrap_prices:
            await self._bootstrap_prices()
        else:
            logger.warning("⏭️ skip_bootstrap_prices=True — não chama futures_ticker() para bootstrap prices.")
        
        tasks = [
            self._fetch_initial_klines(),
            self._listen_agg_trades(),
            self._listen_klines(),
            self._listen_liquidations(),
            self._poll_market_data(),
            self._record_snapshots(),
            self._periodic_reset_1m()
        ]
        
        logger.info(f"🚀 Motor de Dados iniciado para {len(self.symbols)} símbolos (top {self.top_n}).")
        await asyncio.gather(*tasks)

    async def _filter_top_symbols(self):
        """Filter symbols by 24h volume - only top N."""
        original_symbols = self.symbols.copy()
        client = self.client
        assert client is not None
        try:
            # DNA Sniper: Cast para silenciar Pyright (RHS é List[Dict] quando symbol=None)
            tickers = cast(List[Dict[str, Any]], await client.futures_ticker())
            if tickers:
                first_ticker: Dict[str, Any] = tickers[0]
                logger.info(f"Ticker keys: {list(first_ticker.keys())[:5]}...")
            valid_set = set(original_symbols)
            filtered_tickers: List[Dict[str, Any]] = [t for t in tickers if t.get('symbol') in valid_set]
            sorted_tickers = sorted(filtered_tickers, key=lambda x: float(x.get('quoteVolume') or x.get('volume') or 0), reverse=True)
            
            # SPRINT 6.10: Não truncamos mais a lista. Monitoramos TODOS os ativos (520+).
            # A ordenação por volume serve agora apenas para priorização de dados REST.
            self.symbols = [t['symbol'] for t in sorted_tickers]
            
            # Remove possíveis duplicatas se macros já estiverem no top_n
            self.symbols = list(dict.fromkeys(self.symbols))
            
            # Identifica quais são os símbolos do Top N para priorização de LSR oficial
            self._top_n_symbols = set(self.symbols[:self.top_n])

            logger.info(f"🔭 RADAR GLOBAL ATIVO: Monitorando {len(self.symbols)} símbolos.")
        except Exception as e:
            self._maybe_set_rest_ban_from_exception(e)
            logger.error(f"Erro ao filtrar símbolos: {e}. Usando fallback.")
            self.symbols = original_symbols[:self.top_n] if original_symbols else ["BTCUSDT", "ETHUSDT", "BTCDOMUSDT"]

    def _init_data(self):
        """Initialize data structures using MetricStore."""
        self.store = MetricStore(self.symbols)
        assert self.store is not None

        # Extrair e injetar filtros de step/tick
        if self._exchange_info:
            for s_info in self._exchange_info.get("symbols", []):
                sym = s_info["symbol"]
                if sym in self.data:
                    for f in s_info.get("filters", []):
                        if f["filterType"] == "LOT_SIZE":
                            self.data[sym]["step_size"] = f["stepSize"]
                        elif f["filterType"] == "PRICE_FILTER":
                            self.data[sym]["tick_size"] = f["tickSize"]

        if self.store.load_state():
            self.store.init_symbols(self.symbols)
        self.data = self.store.data

    async def _fetch_initial_klines(self):
        assert self.store is not None
        assert self.client is not None
        assert self._api_sem is not None

        store = self.store
        client = self.client
        sem = self._api_sem

        def needs_tf(sym: str, tf: str) -> bool:
            buf_len = len(store._klines.get(sym, {}).get(tf, []))
            rsi_key = f"rsi:{tf}"
            rsi_val = store.data.get(sym, {}).get(rsi_key)
            # Recalcula se o buffer estiver insuficiente para EMA-100 OU se o RSI ainda estiver None
            return buf_len < 110 or rsi_val is None

        # SPRINT 11.4: Prioriza klines apenas para Top N e Macros no boot.
        # O resto aquece via WebSocket para evitar IP Ban em Radar Global (500+ ativos).
        # CORREÇÃO P0.2: RSI Bootstrap Expandido (Top 20 → Top 50) para reduzir gaps de RSI
        priority_targets = set(self.symbols[:50]) | {"BTCUSDT", "ETHUSDT", "BTCDOMUSDT"}
        missing = [s for s in self.symbols if s in priority_targets and (needs_tf(s, "5m") or needs_tf(s, "15m") or needs_tf(s, "1h"))]

        if not missing:
            logger.info("✅ Klines já aquecidas via cache.")
            return

        logger.info("⏳ Baixando klines iniciais (%s símbolos)...", len(missing))
        async def fetch_symbol(symbol: str):
            async with sem:
                try:
                    k_5m = await client.futures_klines(symbol=symbol, interval='5m', limit=110)
                    k_15m = await client.futures_klines(symbol=symbol, interval='15m', limit=110) # type: ignore
                    k_1h = await client.futures_klines(symbol=symbol, interval='1h', limit=110) # type: ignore
                    if k_5m: store.init_klines(symbol, "5m", [float(x[4]) for x in k_5m], [float(x[5]) for x in k_5m])
                    if k_15m: store.init_klines(symbol, "15m", [float(x[4]) for x in k_15m], [float(x[5]) for x in k_15m])
                    if k_1h: store.init_klines(symbol, "1h", [float(x[4]) for x in k_1h], [float(x[5]) for x in k_1h])
                except Exception as e:
                    logger.debug("Erro klines %s: %s", symbol, e)

        await asyncio.gather(*(fetch_symbol(s) for s in missing))
        logger.info("✅ Klines iniciais completas.")

    async def _periodic_reset_1m(self):
        """Centraliza o reset de métricas de 1m para evitar conflitos entre tarefas de lote."""
        while self.running:
            await asyncio.sleep(60)
            if self.store:
                self.store.reset_1m_volume()

    async def _bootstrap_prices(self) -> None:
        """
        Bootstrap de price via REST para evitar 'price=0' até o AggTrades WS aquecer.
        Isso é especialmente importante para BTCDOMUSDT.
        """
        client = self.client
        if client is None:
            return
        try:
            tickers = await client.futures_ticker()
            if not tickers:
                return

            by_symbol = {t.get("symbol"): t for t in tickers if t.get("symbol")}
            for s in self.symbols:
                t = by_symbol.get(s)
                if not t:
                    continue
                raw = t.get("lastPrice") or t.get("last") or t.get("price")
                if raw is None:
                    continue
                price = float(raw)
                if price > 0 and s in self.data:
                    self.data[s]["price"] = price
                
                # CORREÇÃO v4.2.3: Calcular price_change_24h desde o reset (21:00 BRT)
                # ao invés de usar o valor da Binance (que é desde 00:00 UTC)
                if s in self.data:
                    price_at_reset = self.data[s].get("price_at_reset", 0)
                    if price_at_reset > 0 and price > 0:
                        self.data[s]["price_change_24h"] = ((price - price_at_reset) / price_at_reset) * 100
                    else:
                        # Fallback: usa valor da Binance se não tiver price_at_reset
                        raw_pc = t.get("priceChangePercent")
                        if raw_pc is not None:
                            self.data[s]["price_change_24h"] = float(raw_pc)
                
                # SPRINT 4: Popula Volume 24h inicial
                raw_vol = t.get("quoteVolume") or t.get("volume")
                if raw_vol is not None and s in self.data:
                    self.data[s]["volume_24h"] = float(raw_vol)
        except Exception as e:
            logger.warning("Bootstrap prices falhou: %s", e)

    async def _listen_klines(self):
        """Monitora Klines para atualizar RSI via WS."""
        assert self.bsm is not None
        assert self.store is not None
        bsm = self.bsm
        store = self.store
        
        # Binance Futures combined streams: limite de 200 streams por conexão.
        # 60 símbolos × 3 timeframes = 180 streams — abaixo do limite com margem.
        kline_chunk_size = 60
        symbol_chunks = [
            self.symbols[i : i + kline_chunk_size]
            for i in range(0, len(self.symbols), kline_chunk_size)
        ]
        
        async def _listen_batch(symbols_batch):
            attempt = 0
            while self.running:
                streams = []
                for s in symbols_batch:
                    streams.append(f"{s.lower()}@kline_5m")
                    streams.append(f"{s.lower()}@kline_15m")
                    streams.append(f"{s.lower()}@kline_1h")
                try:
                    async with bsm.multiplex_socket(streams) as stream:
                        attempt = 0
                        logger.info("Kline WS Lote Conectado (%s streams).", len(streams))
                        while self.running:
                            try:
                                msg = await stream.recv()
                            except asyncio.CancelledError:
                                return
                            if not msg or "data" not in msg:
                                continue
                            data = msg["data"]
                            if data.get("e") != "kline":
                                continue
                            
                            symbol = data["s"]
                            k = data["k"]
                            interval = k["i"]
                            close = float(k["c"])
                            volume = float(k["v"])
                            is_final = k["x"]
                            
                            store.update_kline(symbol, interval, close, volume, is_final)
                except asyncio.CancelledError:
                    return
                except Exception as e:
                    if not self.running:
                        break
                    attempt += 1
                    delay = self._ws_backoff(attempt)
                    logger.warning("Kline WS Batch erro: %s — reconectando em %.1fs", e, delay)
                    await asyncio.sleep(delay)

        for chunk in symbol_chunks:
            asyncio.create_task(_listen_batch(chunk))
            # SPRINT 6.18/6.26: Stagger delay aumentado para 5s para evitar timeout SSL
            await asyncio.sleep(5.0)

    async def _listen_liquidations(self):
        """Monitora stream !forceOrder@arr para detectar liquidações de short."""
        assert self.bsm is not None
        assert self.store is not None
        bsm = self.bsm
        store = self.store

        # Stream global único — entrega todas as liquidações do mercado.
        # Anterior: centenas de streams symbol@forceOrder via multiplex falhavam silenciosamente.
        streams = ["!forceOrder@arr"]

        logger.info("Liquidation WebSocket: Iniciando stream global !forceOrder@arr")

        attempt = 0
        while self.running:
            try:
                async with bsm.multiplex_socket(streams) as stream:
                    attempt = 0
                    logger.info("Liquidation WebSocket: Conectado (!forceOrder@arr)")
                    while self.running:
                        msg = await stream.recv()
                        if not msg or "data" not in msg:
                            continue
                        payload = msg["data"]
                        # DIAG F-12: log payload bruto para confirmar formato real do stream.
                        # Logar apenas os primeiros 3 eventos por sessão para não spam.
                        if not hasattr(self, "_liq_diag_count"):
                            self._liq_diag_count = 0
                        if self._liq_diag_count < 3:
                            logger.info("DIAG F-12 payload bruto (#%d): %s", self._liq_diag_count + 1, payload)
                            self._liq_diag_count += 1
                        # !forceOrder@arr entrega lista; fallback para dict (symbol@forceOrder legado)
                        events = payload if isinstance(payload, list) else [payload]
                        for event in events:
                            o = event.get("o") or event
                            sym = o.get("s")
                            side = o.get("S")
                            try:
                                # F-12: usa ap (avg price) * z (fill qty) para notional real.
                                # p pode ser 0 em ordens de mercado — causava notional=0 silencioso.
                                avg_price = float(o.get("ap") or o.get("p") or 0)
                                fill_qty  = float(o.get("z")  or o.get("q") or 0)
                                notional  = avg_price * fill_qty
                            except (KeyError, ValueError, TypeError):
                                continue
                            if sym and side:
                                store.update_liquidation(sym, side, notional)
                                logger.info("Liquidation raw: %s side=%s notional=%.2f (ap=%s z=%s)",
                                            sym, side, notional, o.get("ap"), o.get("z"))
            except Exception as e:
                attempt += 1
                logger.error("Liquidation WebSocket: Erro (tentativa %d): %s", attempt, e)
                await asyncio.sleep(self._ws_backoff(attempt))
        
        logger.info("Liquidation WebSocket: Encerrado")

    async def _listen_agg_trades(self):
        """Monitora AggTrades; reconecta se o WebSocket cair."""
        assert self.client is not None
        assert self.bsm is not None
        assert self.store is not None
        bsm = self.bsm
        store = self.store

        # P0-1: Reduzir para 1 conexão única (150 símbolos cabem confortavelmente)
        streams = [f"{s.lower()}@aggTrade" for s in self.symbols]
        
        attempt = 0
        while self.running:
            try:
                async with bsm.multiplex_socket(streams) as stream:
                    attempt = 0
                    while self.running:
                        msg = await stream.recv()
                        if not msg or "data" not in msg: continue
                        d = msg["data"]
                        store.update_trade(d["s"], float(d["p"]), (-float(d["q"]) if d["m"] else float(d["q"])))
                        self.last_data_ts = time.time() # Alimenta o Health Check
            except Exception:
                attempt += 1
                await asyncio.sleep(self._ws_backoff(attempt))
        
        logger.info("AggTrade WebSocket: 1 conexão para %d símbolos", len(self.symbols))

    async def _poll_market_data(self):
        """OI/LSR em lotes — não dispara 50 HTTP em paralelo (travava o loop no Windows)."""
        try:
            await self._poll_market_data_loop()
        except asyncio.CancelledError:
            return

    async def _poll_market_data_loop(self):
        while self.running:
            t0_start = time.time()
            
            # Narrowing local do client para satisfazer o Pylance (reportOptionalMemberAccess)
            client_local = self.client
            if client_local is None:
                await asyncio.sleep(1)
                continue

            now = time.time()
            
            # SPRINT 11.9: Priorização VIP + Radar Rotativo
            priority_syms = []
            cold_syms = []

            # Atualiza Volume 24h apenas 1x a cada 10 min (Consolidado)
            if (now - self._last_volume_24h_refresh) >= self.volume_24h_refresh_seconds:
                try:
                    tickers = await client_local.futures_ticker()
                    by_symbol = {t.get("symbol"): t for t in tickers if t.get("symbol")}
                    for s in self.symbols:
                        if s in by_symbol and s in self.data:
                            t = by_symbol[s]
                            v = t.get("quoteVolume") or t.get("volume")
                            if v: self.data[s]["volume_24h"] = float(v)
                            
                            # CORREÇÃO v4.2.3: Calcular price_change_24h desde o reset (21:00 BRT)
                            price_at_reset = self.data[s].get("price_at_reset", 0)
                            current_price = self.data[s].get("price", 0)
                            if price_at_reset > 0 and current_price > 0:
                                self.data[s]["price_change_24h"] = ((current_price - price_at_reset) / price_at_reset) * 100
                            else:
                                # Fallback: usa valor da Binance se não tiver price_at_reset
                                p = t.get("priceChangePercent")
                                if p: self.data[s]["price_change_24h"] = float(p)
                    self._last_volume_24h_refresh = now
                except Exception: pass

            for s in self.symbols:
                d = self.data.get(s, {})
                # CRITÉRIO VIP: Top 50, Moedas com Ignição ou Score alto
                is_prio = (
                    s in self._top_n_symbols 
                    or abs(d.get("exp:5m") or 0) > 0.01
                    or (d.get("score") or 0) >= 60
                )
                if is_prio: priority_syms.append(s)
                else: cold_syms.append(s)

            # Seleciona fatia rotativa das moedas "frias"
            rotational_batch = []
            if cold_syms:
                start = self._rotational_index % len(cold_syms)
                rotational_batch = cold_syms[start : start + self._batch_size_non_priority]
                self._rotational_index = (start + self._batch_size_non_priority) % len(cold_syms)

            # Alvos deste ciclo: Todos os VIPs + fatia do Radar Global
            target_symbols = priority_syms + rotational_batch

            # Se REST estiver banido, evita criar tasks que certamente vão falhar/retornar False.
            if self._rest_ban_active():
                await asyncio.sleep(5)
                continue

            tasks = [self._fetch_single_market_data(symbol) for symbol in target_symbols]
            results_all = await asyncio.gather(*tasks, return_exceptions=True)
            ok_count = sum(1 for r in results_all if r is True)
            elapsed_total = time.time() - t0_start
            logger.info(
                "OI/LSR Ciclo: %d prioritários + %d rotativos | Sucesso: %d | %.1fs",
                len(priority_syms), len(rotational_batch), ok_count, elapsed_total,
            )
            try:
                await asyncio.sleep(max(1.0, self.oi_poll_seconds - elapsed_total))
            except asyncio.CancelledError:
                return

    async def _fetch_single_market_data(self, symbol: str) -> bool:
        if symbol not in self.data:
            return False

        # Se IP estiver banido, não faz mais chamadas REST agora.
        if self._rest_ban_active():
            return False

        assert self.client is not None
        assert self.store is not None
        assert self._api_sem is not None

        client = self.client
        store = self.store
        sem = self._api_sem

        async with sem:
            try:
                now = time.time()
                # SPRINT 11.4: Prioridade Dinâmica (Definida no início para evitar NameError)
                # SPRINT 11.10: Diferenciação entre Prioridade (Top 50) e Ignição (Moeda Quente)
                d_sym = self.data[symbol]
                is_ignited = abs(d_sym.get("exp:5m") or 0) > 0.02 or d_sym.get("liq_cascade", False)

                # SPRINT 11.14: Feedback visual de 'Bot Vivo' para o operador
                if is_ignited and not d_sym.get("_ignited_logged", False):
                    logger.info("⚡ STATUS: %s em IGNIÇÃO (Polling de Alta Frequência Ativado)", symbol)
                    d_sym["_ignited_logged"] = True
                elif not is_ignited:
                    d_sym["_ignited_logged"] = False

                is_priority = (
                    symbol in self._top_n_symbols 
                    or is_ignited
                    or (d_sym.get("score") or 0) >= 60
                )

                # OI e LSR devem ser independentes para garantir persistência
                oi_val = self.data[symbol].get("oi", 0.0)
                lsr_val = self.data[symbol].get("lsr")
                lsr_updated = False

                # Se o banimento foi ativado por uma task anterior neste mesmo ciclo
                if self._rest_ban_active():
                    return False

                try:
                    # OI REST gate por símbolo (evita ban por tempestade)
                    last_oi = self._last_oi_fetch.get(symbol, 0.0)
                    # SPRINT 11.5: OI é vital para o rastro. Moedas em radar global atualizam a cada 60s.
                    # SPRINT 11.10: Se a moeda está em IGNIÇÃO, o intervalo cai para quase zero (frequência total)
                    if is_ignited:
                        target_oi_interval = 2.0
                    else:
                        target_oi_interval = self.oi_rest_interval_seconds if is_priority else 60.0

                    if (now - last_oi) >= target_oi_interval and not self._rest_ban_active():
                        # SPRINT 12.92: P1.2 - Retry logic com Backoff Progressivo (Até 3 tentativas)
                        for attempt in range(3): 
                            try:
                                oi_data = await client.futures_open_interest(symbol=symbol)
                                oi_val = float(oi_data.get("openInterest", 0.0))
                                self._last_oi_fetch[symbol] = now
                                break
                            except Exception as e:
                                self._maybe_set_rest_ban_from_exception(e)
                                if self._rest_ban_active() or attempt == 2: raise
                                await asyncio.sleep(0.5 * (attempt + 1)) 
                except Exception as e:
                    self._maybe_set_rest_ban_from_exception(e)
                    logger.debug(f"OI fetch falhou para {symbol}: {e}")

                if self._rest_ban_active():
                    return False

                # CORREÇÃO P1.3: Funding Democratizado - Coleta para TODOS os símbolos
                # Funding Rate: cooldown diferenciado (1min prio, 5min resto)
                funding_interval = 60 if is_priority else 300  # 1min (prio) vs 5min (resto)
                if now - self._last_funding_fetch.get(symbol, 0) > funding_interval:
                    try:
                        funding_data = await client.futures_funding_rate(symbol=symbol, limit=1)
                        if funding_data:
                            funding_rate = float(funding_data[-1].get("fundingRate", 0))
                            self.data[symbol]["funding_rate"] = funding_rate
                            self._last_funding_fetch[symbol] = now
                    except Exception as e:
                        self._maybe_set_rest_ban_from_exception(e)
                        logger.debug(f"Funding fetch falhou para {symbol}: {e}")

                if self._rest_ban_active():
                    return False

                try:
                    # Global LSR REST gate por símbolo (evita ban por tempestade)
                    last_lsr = self._last_lsr_fetch.get(symbol, 0.0)
                    # SPRINT 11.10: Ignição ignora o cooldown longo do LSR
                    if is_ignited:
                        target_lsr_interval = 15.0
                    else:
                        target_lsr_interval = self.lsr_rest_interval_seconds

                    do_official_lsr = is_priority and (now - last_lsr) >= target_lsr_interval and not self._rest_ban_active()

                    if do_official_lsr:
                        # SPRINT 12.92: P1.2 - Retry logic para LSR Oficial
                        for attempt in range(3):
                            try:
                                lsr_data = await client.futures_global_longshort_ratio(
                                    symbol=symbol, period="5m", limit=5
                                )
                                if lsr_data and len(lsr_data) > 0:
                                    last = lsr_data[-1] or {}
                                    candidate = last.get("longShortRatio", None)
                                    if candidate is not None:
                                        lsr_val = float(candidate)
                                        lsr_updated = True
                                        self._last_lsr_fetch[symbol] = now
                                        self._lsr_miss_count[symbol] = 0
                                        self.data[symbol]["lsr_is_proxy"] = False
                                        break
                            except Exception as e:
                                self._maybe_set_rest_ban_from_exception(e)
                                if self._rest_ban_active() or attempt == 2: raise
                                await asyncio.sleep(0.5 * (attempt + 1))

                    # --- Fallback: LSR Proxy via Taker Volume ---
                    if do_official_lsr and not lsr_updated:
                        self._lsr_none_cycles[symbol] = self._lsr_none_cycles.get(symbol, 0) + 1
                        cycles = self._lsr_none_cycles[symbol]
                        if cycles >= 4 and cycles % 4 == 0:
                            logger.warning(
                                "📋 LSR diagnostic: %s sem dados oficiais. Usando Proxy de Volume.",
                                symbol,
                                cycles,
                            )
                        self._lsr_miss_count[symbol] = self._lsr_miss_count.get(symbol, 0) + 1
                    elif lsr_updated or not is_priority:
                        self._lsr_none_cycles[symbol] = 0
                        self._lsr_miss_count[symbol] = 0

                    # CORREÇÃO P0.1: LSR Proxy Agressivo - Ativa imediatamente para não-prioritários
                    # Se não for prioridade, usa SEMPRE o proxy (mais confiável que API oficial)
                    if not is_priority:
                        # Moedas não-prioritárias usam proxy com cooldown de 30s
                        last_proxy = self._last_lsr_proxy_fetch.get(symbol, 0.0)
                        if (now - last_proxy) >= self.lsr_proxy_interval_dorment and not self._rest_ban_active():
                            try:
                                klines = await client.futures_klines(symbol=symbol, interval='5m', limit=3)
                                self._last_lsr_proxy_fetch[symbol] = now
                                if klines:
                                    total_vol = sum(float(k[5]) for k in klines)
                                    buy_vol = sum(float(k[9]) for k in klines)
                                    if total_vol > 0:
                                        taker_ratio = buy_vol / total_vol
                                        lsr_val = taker_ratio * 2.0
                                        lsr_updated = True
                                        self.data[symbol]["lsr_is_proxy"] = True
                            except Exception:
                                pass
                    # Prioritários usam proxy após 2 falhas consecutivas do oficial
                    elif self._lsr_miss_count.get(symbol, 0) >= 2:
                        last_proxy = self._last_lsr_proxy_fetch.get(symbol, 0.0)
                        target_proxy_interval = self.lsr_rest_interval_seconds
                        if (now - last_proxy) >= target_proxy_interval and not self._rest_ban_active():
                            try:
                                klines = await client.futures_klines(symbol=symbol, interval='5m', limit=3)
                                self._last_lsr_proxy_fetch[symbol] = now
                                if klines:
                                    total_vol = sum(float(k[5]) for k in klines)
                                    buy_vol = sum(float(k[9]) for k in klines)
                                    if total_vol > 0:
                                        taker_ratio = buy_vol / total_vol
                                        lsr_val = taker_ratio * 2.0
                                        lsr_updated = True
                                        self.data[symbol]["lsr_is_proxy"] = True
                            except Exception:
                                pass

                        if self._rest_ban_active():
                            return False
                    else:
                        self._lsr_none_cycles[symbol] = 0
                except Exception as e:
                    self._maybe_set_rest_ban_from_exception(e)
                    logger.debug(f"LSR fetch falhou para {symbol}: {e}")

                # Order Book: poll menos frequente para reduzir REST (evita ban)
                # SPRINT 11.4: Gate de prioridade. Radar Global não precisa de OB para ativos dormentes.
                if is_priority and now - self._last_depth_fetch.get(symbol, 0) > self.depth_rest_interval_seconds:
                    try:
                        depth = await client.futures_order_book(symbol=symbol, limit=10)
                        if depth and depth.get("bids") and depth.get("asks"):
                            best_bid = float(depth["bids"][0][0])
                            best_ask = float(depth["asks"][0][0])
                            if best_bid > 0:
                                self.data[symbol]["bid_ask_spread"] = (best_ask - best_bid) / best_bid * 100

                        bid_vol = sum(float(b[1]) for b in depth.get("bids", []))
                        ask_vol = sum(float(a[1]) for a in depth.get("asks", []))
                        if ask_vol > 0:
                            self.data[symbol]["ob_imbalance"] = bid_vol / ask_vol
                        else:
                            self.data[symbol]["ob_imbalance"] = 1.0
                        self._last_depth_fetch[symbol] = now
                    except Exception as e:
                        self._maybe_set_rest_ban_from_exception(e)
                        logger.debug(f"Depth fetch falhou para {symbol}: {e}")

                store.update_oi_lsr(symbol, oi_val, lsr_val)
                return True
            except Exception as e:
                logger.debug(f"Erro no ciclo de polling para {symbol}: {e}")
                return False

    async def _record_snapshots(self):
        """Grava snapshots periódicos e cuida do state cache."""
        assert self.store is not None
        store = self.store
        try:
            last_save = time.time()
            while self.running:
                store.record_snapshot()
                
                # Persistência em CSV para histórico de longo prazo (DNA Squeeze)
                ts = time.time()

                # Captura um snapshot dos dados atuais para evitar conflitos de thread
                # e garantir que o log seja fiel ao momento exato do rastro.
                snapshot_data = {sym: d.copy() for sym, d in self.data.items()}
                
                # Offload da gravação para uma thread separada para não travar o loop de trading
                log_coro = asyncio.to_thread(self._history_logger.log_snapshots, ts, self.symbols.copy(), snapshot_data)
                asyncio.create_task(log_coro)

                if time.time() - last_save > 60:
                    store.save_state()
                    last_save = time.time()
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            return

    async def stop(self) -> None:
        """
        Shutdown gracioso do DataEngine.
        AUDITORIA 2026-05-31: Corrige memory leak de sessões aiohttp não fechadas.
        """
        self.running = False
        
        # Salva estado do MetricStore
        if self.store:
            self.store.save_state()
        
        # Fecha cliente Binance (sessão aiohttp interna)
        if self.client:
            try:
                await self.client.close_connection()
                logger.info("AsyncClient fechado com sucesso")
            except Exception as e:
                logger.warning(f"Erro ao fechar AsyncClient: {e}")
        
        # Aguarda um momento para garantir que todas as conexões sejam fechadas
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    engine = DataEngine(["BTCUSDT", "ETHUSDT"], top_n=10)
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        asyncio.run(engine.stop())
