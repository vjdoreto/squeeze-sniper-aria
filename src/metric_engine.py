import time
import logging
import os
import json
from pathlib import Path
from collections import deque
from typing import Deque, Dict, List, Any, Optional, Sequence, Union

logger = logging.getLogger("MetricStore")

# P0.1: Path para logging de gaps de dados
_DATA_GAPS_LOG = Path("logs/data_gaps.jsonl")
_DATA_GAPS_LOG.parent.mkdir(parents=True, exist_ok=True)

class MetricStore:
    """
    Motor central de armazenamento e cálculo de métricas.
    Segue o schema do eassets (ex: 'price', 'oi_trend:5m').
    """
    def __init__(self, symbols: List[str]):
        self.symbols: List[str] = []
        self.data: Dict[str, Dict[str, Any]] = {}
        # lsr pode ser None (quando o dado ainda não foi coletado)
        self._history: Dict[str, List[Dict[str, Optional[float]]]] = {}
        self._klines: Dict[str, Dict[str, List[float]]] = {}
        self._kline_volumes: Dict[str, Dict[str, List[float]]] = {} # Novo: Armazena volumes das klines
        self._last_update_ts: Dict[str, Dict[str, float]] = {} # P1.1: Frescor dos dados (Anti-Stale)
        # Baseline histórica de trades (20 ciclos) para spike detection
        self._trades_baseline: Dict[str, List[float]] = {}
        # Se o cache carregou com history vazio e a gente bootstrapeou,
        # evitamos "trends = 0" até ter amostras reais o suficiente.
        self._warmup_samples: Dict[str, int] = {}
        self._min_warmup = 2 # Mínimo de amostras para trend começar a aparecer (20s)
        self._kline_limit = 110 # Buffer para EMA-100
        # Rolling buffer de exp_btc:5m por símbolo para Z-score ARIA (window=14)
        self._exp_btc_buf: Dict[str, Deque[float]] = {}
        self.init_symbols(symbols)

    def reset_daily_history(self) -> None:
        """
        Limpa histórico de slopes às 00h UTC (21h BRT).
        Previne que referências de preço do dia anterior contaminem os cálculos.
        """
        cleared = 0
        for symbol in list(self.data.keys()):
            # Limpar ring buffer de snapshots (fonte dos slopes)
            if symbol in self._history:
                self._history[symbol] = []
                cleared += 1

            d = self.data.get(symbol, {})
            
            # CORREÇÃO v4.2.3: Salva preço atual como referência do dia (21:00 BRT)
            # Isso permite calcular variação desde o reset, não desde 00:00 UTC da Binance
            current_price = d.get("price", 0.0)
            if current_price > 0:
                d["price_at_reset"] = current_price

            # Zerar métricas derivadas de histórico
            for key in [
                "exp:1m","exp:5m","exp:1h","exp_btc:5m","exp_btc_norm_1h",
                "oi_trend:1m","oi_trend:5m","oi_trend:1h",
                "lsr_trend:1m","lsr_trend:5m","lsr_trend:1h",
                "oi_accel:5m","oi_change_pct:5m","lsr_change_pct:5m",
                "cvd_change_pct:5m","price_change:5m","price_change:15m",
                "price_change:1h","price_change_24h",
            ]:
                d[key] = 0.0

            # Resetar sparklines (arrays visuais)
            d["cvd_hist"] = []
            d["oi_hist"]  = []
            self._warmup_samples[symbol] = 0

        logger.info("🔄 Reset diário: %d símbolos limpos (00h UTC / 21h BRT)", cleared)

    def init_symbols(self, symbols: List[str]):
        """Inicializa ou atualiza a lista de símbolos (útil ao filtrar top_n)."""
        self.symbols = symbols
        
        # Manter o histórico de todos os símbolos que já vimos!
        # Não remover dados de símbolos que saem do top N, pois eles podem voltar!
        for s in symbols:
            self._last_update_ts.setdefault(s, {})
            if s not in self.data:
                # Novo símbolo: inicializar do zero
                self.data[s] = {
                    "price": 0.0,
                    "price_change_24h": 0.0, # SPRINT 6.28: Variação diária (reset 21:00 BRT)
                    "volume_24h": 0.0,
                    "oi": 0.0,
                    "lsr": None,
                    "lsr_is_proxy": False,
                    "funding_rate": 0.0,
                    "volume_delta_1min": 0.0,
                    "volume_delta_1min_stable": 0.0,
                    "liq_short_1m": 0.0,
                    "liq_short_1m_stable": 0.0,
                    "liq_short_prev": 0.0,
                    "liq_cascade": False,
                    "volume_3h_avg": 0.0, # SPRINT 6.1: Média de volume das últimas 3h
                    "step_size": "0.00000001", # SPRINT 12: Fallback ultra-fino para evitar saltos
                    "tick_size": "0.00000001",
                    "vol_3h_warmup": False, # Warmup para o Gating Vol-Adaptive
                    "bid_ask_spread": 0.0,
                    "trades_second": 0.0,
                    "trades_count_10s": 0.0,
                    "last_trades_10s": 0.0,
                    "trades_count_1min": 0.0,
                    "trades_count_1min_stable": 0.0,
                    "trades_level": 0,
                    "trades_minute:5m": 0.0,
                    "exp:5m": 0.0,
                    "exp:1m": 0.0,
                    "exp:1h": 0.0,
                    "exp_btc:5m": 0.0,
                    "exp_btc_norm_1h": 0.0,
                    "oi_trend:5m": 0.0,
                    "oi_trend:1m": 0.0,
                    "lsr_trend:5m": 0.0,
                    "lsr_trend:1m": 0.0,
                    "oi_accel:5m": 0.0,
                    "price_change:5m": 0.0,
                    "price_change:15m": 0.0,
                    "price_change:1h": 0.0,
                    "rsi:5m": 50.0,
                    "rsi:15m": 50.0,
                    "rsi:1h": 50.0,
                    "ema_trend:5m": 0,
                    "ema_trend:15m": 0,
                    "ema_trend:1h": 0,
                    "ema_trend:4h": None,  # F-18: None = sem dados ainda (< 50 candles)
                    "range_level:5m": 0,
                    "range_level:15m": 0,
                    "range_level:1h": 0,
                    "swing_low:5m": 0.0,
                    "swing_low:15m": 0.0,
                    "swing_low:1h": 0.0,
                    "ob_imbalance": 1.0,
                    "cvd_cumulative": 0.0,
                    "cvd_hist": [],
                    "liq_short_hist": [], # Novo: Histórico de liquidações para gráfico
                    "oi_hist": [],
                    # Percentuais de crescimento (2-amostra): compara agora vs 5 min atrás
                    "cvd_change_pct:5m": 0.0,
                    "oi_change_pct:5m": 0.0,
                    "lsr_change_pct:5m": 0.0,
                }
                # History fake para novos símbolos (evita ativo morto por 5 min)
                if s not in self._history or not self._history[s]:
                    now = time.time()
                    self._history[s] = [
                        {"price": 0.0, "oi": 0.0, "lsr": None, "cvd": 0.0, "timestamp": now - 2.0},
                        {"price": 0.0, "oi": 0.0, "lsr": None, "cvd": 0.0, "timestamp": now},
                    ]
                    self._warmup_samples[s] = max(self._warmup_samples.get(s, 0), self._min_warmup)
                self._klines[s] = {"5m": [], "15m": [], "1h": [], "4h": []}
                self._kline_volumes[s] = {"5m": [], "15m": [], "1h": [], "4h": []}
            else:
                # Símbolo já existe: apenas garantir que tem todas as chaves
                if "trades_count_1min" not in self.data[s]:
                    self.data[s]["trades_count_1min"] = 0.0
                if "trades_count_10s" not in self.data[s]:
                    self.data[s]["trades_count_10s"] = 0.0
                if "last_trades_10s" not in self.data[s]:
                    self.data[s]["last_trades_10s"] = 0.0
                if "volume_delta_1min_stable" not in self.data[s]:
                    self.data[s]["volume_delta_1min_stable"] = 0.0
                if "liq_short_1m_stable" not in self.data[s]:
                    self.data[s]["liq_short_1m_stable"] = 0.0
                if "trades_count_1min_stable" not in self.data[s]:
                    self.data[s]["trades_count_1min_stable"] = 0.0
                if "cvd_hist" not in self.data[s]:
                    self.data[s]["cvd_hist"] = []
                if "oi_hist" not in self.data[s]:
                    self.data[s]["oi_hist"] = []
                if "liq_short_hist" not in self.data[s]:
                    self.data[s]["liq_short_hist"] = []
                if "liq_short_1m" not in self.data[s]:
                    self.data[s]["liq_short_1m"] = 0.0
                existing_kl = getattr(self, "_klines", {}).get(s) or {"5m": [], "1h": []}
                if "15m" not in existing_kl:
                    existing_kl["15m"] = []
                if "4h" not in existing_kl:  # F-18
                    existing_kl["4h"] = []
                if "ema_trend:4h" not in self.data[s]:  # F-18
                    self.data[s]["ema_trend:4h"] = None
                if "volume_3h_avg" not in self.data[s]:
                    self.data[s]["volume_3h_avg"] = 0.0
                if "vol_3h_warmup" not in self.data[s]:
                    self.data[s]["vol_3h_warmup"] = False
                self._klines[s] = existing_kl

    def save_state(self, path: str = "logs/metric_state.json"):
        import json
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            state = {
                "data": self.data,
                # SPRINT 11.50: Persistência profunda do rastro institucional
                "history": {
                    sym: h[-60:] for sym, h in self._history.items()
                },
                "klines": {
                    sym: {tf: buf[-self._kline_limit:] for tf, buf in tfs.items()}
                    for sym, tfs in self._klines.items()
                },
                "kline_volumes": self._kline_volumes, # Salva volumes
                "warmup_samples": self._warmup_samples,
                "timestamp": time.time()
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error("Erro ao salvar estado: %s", e)

    def load_state(self, path: str = "logs/metric_state.json", max_age_seconds: int = 86400) -> bool:
        import json
        import os
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            
            if time.time() - state.get("timestamp", 0) > max_age_seconds:
                logger.info("🗑️ Cache das métricas muito antigo, ignorando.")
                return False
                
            self.data = state.get("data", {})
            self._history = state.get("history", {})
            # Carrega volumes/klines do cache (podem vir incompletos em versões antigas)
            self._kline_volumes = state.get("kline_volumes", {}) or {}
            self._klines = state.get("klines", {}) or {}
            self._warmup_samples = state.get("warmup_samples", {}) or {}

            # Garantir integridade estrutural para evitar KeyError em update_kline()
            # (principalmente quando o cache foi gerado antes de _kline_volumes existir)
            timeframes = ["5m", "15m", "1h", "4h"]  # F-18: 4h adicionado
            for sym in self.symbols:
                if sym not in self._klines or not isinstance(self._klines.get(sym), dict):
                    self._klines[sym] = {tf: [] for tf in timeframes}
                else:
                    for tf in timeframes:
                        if tf not in self._klines[sym] or self._klines[sym][tf] is None:
                            self._klines[sym][tf] = []

                if sym not in self._kline_volumes or not isinstance(self._kline_volumes.get(sym), dict):
                    self._kline_volumes[sym] = {tf: [] for tf in timeframes}
                else:
                    for tf in timeframes:
                        if tf not in self._kline_volumes[sym] or self._kline_volumes[sym][tf] is None:
                            self._kline_volumes[sym][tf] = []

                # Alinhar tamanhos entre _klines e _kline_volumes para evitar IndexError em update_kline()
                for tf in timeframes:
                    buf = self._klines.get(sym, {}).get(tf, []) or []
                    vol = self._kline_volumes.get(sym, {}).get(tf, []) or []

                    if buf and not vol:
                        self._kline_volumes[sym][tf] = [0.0 for _ in range(len(buf))]
                        continue

                    if len(buf) != len(vol):
                        if len(vol) > len(buf):
                            self._kline_volumes[sym][tf] = vol[-len(buf):]
                        else:
                            pad_val = vol[-1] if vol else 0.0
                            self._kline_volumes[sym][tf] = vol + [pad_val for _ in range(len(buf) - len(vol))]

            # Garantia de integridade: se as chaves de tendência sumiram, reinicializar
            for sym in self.data:
                d = self.data[sym]
                for key in ["oi_trend:5m", "lsr_trend:5m", "exp:5m", "exp_btc:5m"]:
                    if key not in d:
                        d[key] = 0.0

            # Garantir chaves de warmup para símbolos conhecidos
            for sym in self.symbols:
                if sym not in self._warmup_samples:
                    self._warmup_samples[sym] = 0

                # DNA Sniper: Garante que LSR seja None se ausente (evita trend killer 0.0)
                ds_load = self.data.get(sym)
                if ds_load is not None and (ds_load.get("lsr") == 0 or ds_load.get("lsr") == 0.0):
                    ds_load["lsr"] = None

            # Garantia de histórico mínimo:
            # algumas métricas (oi_trend/lsr_trend) dependem de amostras do history.
            # Se o cache veio sem history para um símbolo (ex: BTCDOM),
            # preenche com snapshots a partir do estado atual para evitar null prolongado.
            now = time.time()
            for sym in self.symbols:
                if sym not in self.data:
                    continue
                if "vol_3h_warmup" not in self.data[sym]:
                    self.data[sym]["vol_3h_warmup"] = False
                hist = self._history.get(sym) or []
                d = self.data.get(sym, {})
                if not hist:
                    oi = d.get("oi")
                    lsr = d.get("lsr")
                    price = d.get("price")
                    # Preenche apenas se houver ao menos OI/LSR
                    if oi is not None or lsr is not None:
                        oi_f = float(oi) if oi is not None else 0.0
                        lsr_f = lsr if lsr is not None else None
                        price_f = float(price) if price is not None else 0.0
                        self._history[sym] = [
                            {"price": price_f, "oi": oi_f, "lsr": lsr_f, "timestamp": now - 1.0},
                            {"price": price_f, "oi": oi_f, "lsr": lsr_f, "timestamp": now},
                        ]
                        # Não sobrescrever warmup persistido (teste espera persistência fiel).
                        # Se veio 0/ausente, aí sim forçamos mínimo.
                        self._warmup_samples[sym] = max(self._warmup_samples.get(sym, 0), self._min_warmup)

            # Recalcular RSI/EMAs após cache quente — campos podem estar None se o cache
            # foi salvo antes do primeiro kline final (ex: rsi:1h = None por até 60min).
            for sym in self.symbols:
                if sym not in self._klines:
                    continue
                for tf, buf in self._klines[sym].items():
                    if len(buf) >= 5:
                        self._update_indicators(sym, tf)

            logger.info(
                "🔥 Boot quente! Cache carregado (idade: %.0fs)",
                time.time() - state.get("timestamp", 0),
            )
            return True
        except Exception as e:
            logger.warning("Cache corrompido, iniciando limpo: %s", e)
            return False

    def init_klines(self, symbol: str, timeframe: str, closes: List[float], volumes: List[float]):
        """Inicializa buffer de klines e volumes, e calcula RSI inicial."""
        if symbol in self._klines and timeframe in self._klines[symbol]:
            self._klines[symbol][timeframe] = closes[-self._kline_limit:]
            self._kline_volumes[symbol][timeframe] = volumes[-self._kline_limit:]
            self._update_indicators(symbol, timeframe)

    def update_kline(self, symbol: str, timeframe: str, close: float, volume: float, is_final: bool):
        """Atualiza a kline mais recente ou adiciona nova se final, incluindo volume."""
        if symbol not in self._klines or timeframe not in self._klines[symbol]:
            return

        buffer = self._klines[symbol][timeframe]
        vol_buffer = self._kline_volumes[symbol][timeframe]

        # Garantir consistência de tamanhos antes de qualquer assignment [-1]
        if len(buffer) != len(vol_buffer):
            if len(buffer) == 0 and len(vol_buffer) > 0:
                del vol_buffer[:]
            elif len(vol_buffer) == 0 and len(buffer) > 0:
                vol_buffer.extend([0.0 for _ in range(len(buffer))])
            else:
                if len(vol_buffer) < len(buffer):
                    pad_val = vol_buffer[-1] if len(vol_buffer) > 0 else 0.0
                    vol_buffer.extend([pad_val for _ in range(len(buffer) - len(vol_buffer))])
                else:
                    del vol_buffer[len(buffer):]

        # Se ainda estiver vazio, inicializa ambos
        if not buffer:
            buffer.append(close)
            vol_buffer.append(volume)
            self._update_indicators(symbol, timeframe)
            return

        if is_final:
            # Atualiza candle corrente e cria o próximo candle em ambos os buffers
            buffer[-1] = close
            vol_buffer[-1] = volume
            buffer.append(close)
            vol_buffer.append(volume)
        else:
            # Atualiza candle corrente (ainda não finalizado)
            buffer[-1] = close
            vol_buffer[-1] = volume

        if len(buffer) > self._kline_limit:
            buffer.pop(0)
            vol_buffer.pop(0)

        self._update_indicators(symbol, timeframe)

    def _update_indicators(self, symbol: str, timeframe: str):
        """Calcula RSI, EMAs e Range Level para atingir paridade eassets."""
        closes = self._klines[symbol][timeframe]
        if len(closes) < 2:
            return

        # CORREÇÃO P0.2: RSI Adaptativo Agressivo (8 → 5 candles mínimo)
        # Reduz tempo de "cegueira" de 40min → 25min (5 candles de 5m)
        min_rsi_samples = 5  # Mínimo reduzido para acelerar warmup
        if len(closes) >= min_rsi_samples:
            actual_window = min(28, len(closes))
            val = self._calc_rsi(closes[-actual_window:])
            # Garante que o valor seja float ou None, nunca um objeto
            self.data[symbol][f"rsi:{timeframe}"] = float(val) if val is not None else None
            # Marca RSI como "em warmup" se < 8 candles (para auditoria futura)
            self.data[symbol][f"rsi:{timeframe}_warmup"] = len(closes) < 8
        else:
            self.data[symbol][f"rsi:{timeframe}"] = None
            self.data[symbol][f"rsi:{timeframe}_warmup"] = True

        # 2. EMAs e EMA Trend (-6 a +6)
        # Mínimo 50 candles para 4h (vs 100 antes) — símbolos que não receberam
        # todos os klines no boot conseguem calcular após ~8 dias de buffer parcial.
        if len(closes) >= 50:
            price = closes[-1]
            e10 = self._calc_ema(closes, 10)
            e20 = self._calc_ema(closes, 20)
            e50 = self._calc_ema(closes, 50)
            e100 = self._calc_ema(closes, 100)

            # Narrowing explícito para satisfazer o Pylance (reportOperatorIssue)
            if (
                e10 is not None 
                and e20 is not None 
                and e50 is not None 
                and e100 is not None
            ):
                v_e10: float = e10
                v_e20: float = e20
                v_e50: float = e50
                v_e100: float = e100
                score = 0
                score += 1 if price > v_e10 else -1
                score += 1 if v_e10 > v_e20 else -1
                score += 1 if v_e20 > v_e50 else -1
                score += 1 if v_e50 > v_e100 else -1
                score += 1 if price > v_e50 else -1
                score += 1 if price > v_e100 else -1
                self.data[symbol][f"ema_trend:{timeframe}"] = score

        # 3. Range Level (0 a 5) - Força de acumulação baseada em 20 candles
        if len(closes) >= 20:
            recent = closes[-20:]
            low, high = min(recent), max(recent)
            if low > 0:
                r_pct = (high - low) / low * 100
                level = 0
                if r_pct < 1.0: level = 5
                elif r_pct < 1.5: level = 4
                elif r_pct < 2.0: level = 3
                elif r_pct < 3.0: level = 2
                elif r_pct < 5.0: level = 1
                self.data[symbol][f"range_level:{timeframe}"] = level
        
        # 4. Swing Low (Mínimo dos últimos 20 candles - Sprint 6.1)
        # SPRINT 12.19: CORREÇÃO CRÍTICA - Validação de swing_low para evitar SL perigoso
        if len(closes) >= 20:
            swing_low = min(closes[-20:])
            # Validação: swing_low não pode estar muito próximo do preço atual
            # Se estiver a menos de 1% do preço atual, ignora swing_low
            current_price = closes[-1]
            if swing_low > current_price * 0.99:
                # Swing low muito próximo, usa cálculo percentual padrão
                self.data[symbol][f"swing_low:{timeframe}"] = 0.0
            else:
                self.data[symbol][f"swing_low:{timeframe}"] = swing_low

        # SPRINT 6.1: Volume médio das últimas 3h
        if timeframe == "1h" and self._kline_volumes[symbol]["1h"]:
            vols = self._kline_volumes[symbol]["1h"]
            self.data[symbol]["volume_3h_avg"] = sum(vols[-3:]) / len(vols[-3:])
            self.data[symbol]["vol_3h_warmup"] = len(vols) >= 3

    def _calc_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        if len(closes) < 2:
            return None
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0, diff))
            losses.append(max(0, -diff))
            
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _calc_ema(self, closes: List[float], period: int) -> Optional[float]:
        if len(closes) < period:
            return None
        # Inicializa a primeira EMA com a média aritmética (SMA)
        ema = sum(closes[:period]) / period
        multiplier = 2 / (period + 1)
        for i in range(period, len(closes)):
            ema = (closes[i] - ema) * multiplier + ema
        return ema

    def update_trade(self, symbol: str, price: float, delta_volume: float):
        if symbol in self.data:
            # SPRINT 11.26: Anti-Contamination Price Guard
            # Ignora saltos > 10% em um único aggTrade (impossível em mercados líquidos)
            prev_price = self.data[symbol].get("price", 0.0)
            if prev_price > 0 and delta_volume > 0: # Apenas valida se houver trade real
                change = abs(price - prev_price) / prev_price
                if change > 0.08: # Reduzido para 8% para ser mais agressivo contra spikes 
                    logger.warning("⚠️ Preço ANÔMALO ignorado em %s: %.4f (anterior: %.4f)", symbol, price, prev_price)
                    return

            self.data[symbol]["price"] = price
            self.data[symbol]["volume_delta_1min"] += delta_volume
            self.data[symbol]["cvd_cumulative"] = self.data[symbol].get("cvd_cumulative", 0.0) + delta_volume
            self.data[symbol]["trades_count_10s"] = self.data[symbol].get("trades_count_10s", 0.0) + 1.0
            # AggTrade chega 1 evento por trade → conta trades por janela de 1 minuto (reset a cada 60s)
            self.data[symbol]["trades_count_1min"] = self.data[symbol].get("trades_count_1min", 0.0) + 1.0

    def reset_1m_volume(self):
        for s in self.symbols:
            if s in self.data:
                # SPRINT 6.9: Armazena versão estável para exibição e scoring antes de zerar
                self.data[s]["volume_delta_1min_stable"] = self.data[s]["volume_delta_1min"]
                liq_val = self.data[s]["liq_short_1m"]
                self.data[s]["liq_short_1m_stable"] = liq_val
                if liq_val > 0:
                    logger.info("F-12 liq_stable: %s liq_short_1m_stable=%.2f", s, liq_val)
                self.data[s]["trades_count_1min_stable"] = self.data[s]["trades_count_1min"]
                
                self.data[s]["volume_delta_1min"] = 0.0
                self.data[s]["liq_short_1m"] = 0.0
                self.data[s]["trades_count_1min"] = 0.0

    def reset_session_state(self) -> None:
        """
        Reseta o "rastro" (trends/growth) para iniciar uma coleta limpa.
        Importante: limpa memória (não só JSON em disco).
        """
        for s in self.symbols:
            d = self.data.get(s)
            if not d:
                continue

            # reseta contador de warmup também
            self._warmup_samples[s] = 0

            # zera deltas de 1m
            d["volume_delta_1min"] = 0.0
            d["liq_short_1m"] = 0.0
            d["trades_count_10s"] = 0.0
            d["last_trades_10s"] = 0.0
            d["trades_count_1min"] = 0.0

            # zera indicadores dependentes de history
            d["exp:5m"] = 0.0
            d["exp_btc:5m"] = 0.0
            d["oi_trend:5m"] = 0.0
            d["lsr_trend:5m"] = 0.0
            d["price_change:5m"] = 0.0
            d["price_change:15m"] = 0.0
            d["price_change:1h"] = 0.0

            d["cvd_change_pct:5m"] = 0.0
            d["oi_change_pct:5m"] = 0.0
            d["lsr_change_pct:5m"] = 0.0

            # zera valores "de rastro" baseados em OI/LSR para não reaproveitar dados antigos
            d["oi"] = 0.0
            d["lsr"] = 0.0

            # limpa history para recomputar trends a partir de "agora"
            self._history[s] = []

    def audit_data_gaps(self, symbol: str) -> Dict[str, Any]:
        """
        P0.1: Audita gaps de dados para um símbolo específico.
        Retorna dicionário com métricas ausentes e % de completude.
        """
        if symbol not in self.data:
            return {"completeness_pct": 0.0, "missing": ["ALL"], "status": "not_tracked"}
        
        now = time.time()
        metrics = self.data[symbol]
        ts_data = self._last_update_ts.get(symbol, {})

        # DNA Sniper P1.1: Dado é considerado ausente se tiver mais de 60s (Stale)
        def is_stale(key: str) -> bool:
            if key not in ["oi", "lsr"]: return False # Klines/RSI geridos pelo buffer kline
            last_ts = ts_data.get(key, 0)
            return (now - last_ts) > 60.0

        critical_metrics = {
            "oi": metrics.get("oi") if not is_stale("oi") else None,
            "lsr": metrics.get("lsr") if not is_stale("lsr") else None,
            "rsi_5m": metrics.get("rsi:5m"),
            "swing_low_5m": metrics.get("swing_low:5m"),
            "cvd_1m": metrics.get("volume_delta_1min_stable"),
            "exp_5m": metrics.get("exp:5m"),
            "oi_trend_5m": metrics.get("oi_trend:5m"),
            "lsr_trend_5m": metrics.get("lsr_trend:5m"),
        }
        
        missing = []
        for key, value in critical_metrics.items():
            if value is None or (isinstance(value, (int, float)) and value == 0.0 and key in ["oi", "lsr"]):
                missing.append(key)
        
        completeness_pct = ((len(critical_metrics) - len(missing)) / len(critical_metrics)) * 100
        
        return {
            "symbol": symbol,
            "completeness_pct": round(completeness_pct, 1),
            "missing": missing,
            "status": "healthy" if completeness_pct >= 80 else "degraded" if completeness_pct >= 50 else "critical"
        }
    
    def log_data_gaps(self, symbol: str) -> None:
        """
        P0.1: Registra gaps de dados em logs/data_gaps.jsonl para auditoria.
        Chamado periodicamente pelo main loop.
        """
        audit = self.audit_data_gaps(symbol)
        
        if audit["missing"]:
            try:
                with _DATA_GAPS_LOG.open("a", encoding="utf-8") as f:
                    record = {
                        "ts": time.time(),
                        "event": "data_gaps",
                        **audit
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
                # Log warning se completude < 80%
                if audit["completeness_pct"] < 80:
                    logger.warning(
                        "⚠️ GAPS DE DADOS %s: %.1f%% completo | Faltando: %s",
                        symbol,
                        audit["completeness_pct"],
                        ", ".join(audit["missing"])
                    )
            except Exception as e:
                logger.error("Erro ao gravar data_gaps.jsonl: %s", e)
    
    def get_data_health_summary(self) -> Dict[str, Any]:
        """
        P0.1: Retorna resumo de saúde de dados para todos os símbolos.
        Usado pelo endpoint /api/data-health do dashboard.
        """
        health = {}
        total_completeness = 0.0
        critical_count = 0
        degraded_count = 0
        
        for sym in self.symbols:
            audit = self.audit_data_gaps(sym)
            health[sym] = audit
            total_completeness += audit["completeness_pct"]
            
            if audit["status"] == "critical":
                critical_count += 1
            elif audit["status"] == "degraded":
                degraded_count += 1
        
        avg_completeness = total_completeness / len(self.symbols) if self.symbols else 0.0
        
        return {
            "avg_completeness_pct": round(avg_completeness, 1),
            "total_symbols": len(self.symbols),
            "critical_count": critical_count,
            "degraded_count": degraded_count,
            "healthy_count": len(self.symbols) - critical_count - degraded_count,
            "symbols": health
        }

    def update_oi_lsr(self, symbol: str, oi: float, lsr: Optional[float]):
        if symbol in self.data:
            # SPRINT 12.87: Metric Gap Guard - Mantém último valor válido se a API falhar
            self.data[symbol]["oi"] = oi
            self._last_update_ts[symbol]["oi"] = time.time()
            if lsr is not None and lsr > 0:
                self.data[symbol]["lsr"] = lsr
                self._last_update_ts[symbol]["lsr"] = time.time()

    def update_liquidation(self, symbol: str, side: str, notional: float):
        """Rastreia liquidações de SHORT (lado BUY) para boost no fit_score."""
        if symbol in self.data:
            # No Futures, quando um SHORT é liquidado, a exchange executa uma compra (BUY) forçada.
            if side.upper() == "BUY":
                prev = self.data[symbol].get("liq_short_1m", 0.0)
                self.data[symbol]["liq_short_1m"] = prev + notional
                logger.info("F-12 liq_accum: %s +%.2f → total=%.2f", symbol, notional, prev + notional)

    def record_snapshot(self):
        """Grava snapshot atual para histórico e recalcula trends/buffers.
        Itera sobre todos os símbolos em self.data (não apenas top_n) para garantir persistência.
        """
        ts = time.time()
        # Itera sobre todos os símbolos que temos no estado, garantindo que o rastro persista
        for symbol in list(self.data.keys()):
            d_snap = self.data.get(symbol)
            if d_snap is None:
                continue

            snap = {
                "price": d_snap["price"],
                "oi": d_snap["oi"],
                "lsr": d_snap.get("lsr"),
                "cvd": d_snap.get("cvd_cumulative", 0.0) or 0.0,
                "liq_short_1m": d_snap.get("liq_short_1m", 0.0) or 0,
                "ob_imbalance": d_snap.get("ob_imbalance", 1.0) or 1.0,
                "trades_count_10s": d_snap.get("trades_count_10s", 0.0) or 0,
                "trades_count_1min": d_snap.get("trades_count_1min", 0) or 0,
                "timestamp": ts,
            }
            if symbol not in self._history:
                self._history[symbol] = []
            
            hist = self._history[symbol]
            hist.append(snap)

            # --- DNA Squeeze: Liquidation Cascade Detector ---
            liq_curr = d_snap.get("liq_short_1m", 0.0) or 0.0
            liq_prev = d_snap.get("liq_short_prev", 0.0) or 0.0
            # F-16: threshold proporcional ao OI do ativo (Brain×Forge 08/06/2026).
            # Threshold fixo de $500 era arbitrário — $500K para altcoins de $3-5M OI
            # é matematicamente impossível; $500 capturava ruído sem discriminar cascata real.
            # max(oi_usd * 0.02, 10_000): 2% do OI ou mínimo $10k, proporcional ao ativo.
            _oi_usd = (d_snap.get("oi") or 0.0) * (d_snap.get("price") or 0.0)
            _liq_threshold = max(_oi_usd * 0.02, 10_000.0)
            d_snap["liq_cascade"] = liq_curr > (liq_prev * 1.8) and liq_curr > _liq_threshold
            d_snap["liq_short_prev"] = liq_curr

            # Mantém até ~1 hora de snapshots (se gravado a cada 10s = 360 itens)
            if len(hist) > 360:
                hist.pop(0)

            # CORREÇÃO P2.5: Trades Count - Buffer de Exibição (persiste por 10s)
            current_trades = int(d_snap.get("trades_count_10s", 0))
            d_snap["last_trades_10s"] = current_trades
            # Campo de exibição que persiste até próximo snapshot (elimina "buracos" visuais)
            d_snap["trades_count_10s_display"] = max(
                current_trades,
                d_snap.get("trades_count_10s_display", 0)
            )
            d_snap["trades_count_10s"] = 0.0  # Reset do acumulador
            d_snap["trades_second"] = current_trades / 10.0

            # Sprint 4D: Dados para Sparklines
            d_snap["cvd_hist"] = [h.get("cvd", 0) for h in hist[-10:]]
            d_snap["liq_short_hist"] = [h.get("liq_short_1m", 0) for h in hist[-10:]] # Novo: Histórico de liquidações
            d_snap["oi_hist"] = [h.get("oi", 0) for h in hist[-10:]]

            # SPRINT 7.6: trades_level (baseline histórica)
            # Detecta spike de atividade comparado com os últimos 20 snapshots
            buf = self._trades_baseline.setdefault(symbol, [])
            current_t = d_snap.get("trades_count_1min", 0)
            buf.append(float(current_t))
            if len(buf) > 20:
                buf.pop(0)

            avg_t = sum(buf) / len(buf) if buf else 1
            ratio = current_t / avg_t if avg_t > 0 else 1.0
            d_snap["trades_level"] = min(4, int(ratio))

            # SPRINT 7.6/4.4: trades_minute (norm. por TF 5m)
            # snapshots assumidos a cada 10s ⇒ últimos 5m = 30 snapshots
            # trades_count_10s já é o total de trades no intervalo de 10s desse snapshot.
            last_5m = hist[-30:]
            t10_sum = sum(float(h.get("trades_count_10s", 0.0) or 0.0) for h in last_5m) if last_5m else 0.0
            d_snap["trades_minute:5m"] = round(t10_sum / 5.0, 1) if len(last_5m) >= 2 else 0.0

            # Só incrementa o warmup quando temos "atividade real" (preço válido)
            # e quando qualquer rastro relevante muda (OI, LSR ou preço).
            if len(hist) >= 2:
                prev = hist[-2]
                if snap["price"] > 0 and (
                    snap["oi"] != prev["oi"]
                    or snap["lsr"] != prev["lsr"]
                    or snap["price"] != prev["price"]
                ):
                    self._warmup_samples[symbol] = self._warmup_samples.get(symbol, 0) + 1
            else:
                self._warmup_samples[symbol] = 1 if snap["price"] > 0 else 0

            # Cálculo de trends baseados em snapshots recentes
            if self._warmup_samples.get(symbol, 0) >= self._min_warmup or len(hist) >= self._min_warmup:
                # Passamos d_snap explicitamente para evitar closures de tipo ambíguo no Pylance
                def compute_tf_slopes(target_d: Dict[str, Any], window_size: int, suffix: str):
                    chunk = hist[-window_size:]
                    if len(chunk) < 2:
                        target_d[f"exp:{suffix}"] = 0.0
                        target_d[f"oi_trend:{suffix}"] = 0.0
                        target_d[f"lsr_trend:{suffix}"] = 0.0
                        return

                    # Extração segura de séries temporais (filtra zeros não inicializados)
                    oi_series = [s.get("oi") for s in chunk if (s.get("oi") or 0.0) > 0.0]
                    target_d[f"oi_trend:{suffix}"] = self._calc_exp_slope(oi_series) or 0.0

                    lsr_series_raw = [s.get("lsr") if s.get("lsr") is not None else 0.0 for s in chunk]
                    non_zero_lsr = [v for v in lsr_series_raw if v != 0.0]
                    target_d[f"lsr_trend:{suffix}"] = self._calc_exp_slope(non_zero_lsr) if len(non_zero_lsr) >= 2 else 0.0

                    price_series = [s.get("price") for s in chunk if (s.get("price") or 0) > 0]
                    target_d[f"exp:{suffix}"] = self._calc_exp_slope(price_series) if len(price_series) >= 2 else 0.0

                compute_tf_slopes(d_snap, 6, "1m")
                compute_tf_slopes(d_snap, 30, "5m")
                compute_tf_slopes(d_snap, 360, "1h")

                # OI Accel (DNA Sniper): Diferença entre 1m e 5m (filtra zeros não inicializados)
                oi_series = [s["oi"] for s in hist[-30:] if (s.get("oi") or 0.0) > 0.0]
                if len(oi_series) >= 6:
                    short_oi_series = oi_series[-5:]
                    short_slope = self._calc_exp_slope(short_oi_series) or 0
                    long_slope = d_snap.get("oi_trend:5m") or 0
                    d_snap["oi_accel:5m"] = short_slope - long_slope

            if (d_snap.get("price") or 0) > 0:
                d_snap["price_change:5m"] = self._calc_price_change_with_fallback(
                    symbol, hist, ts, 300, "5m", 1
                )
                d_snap["price_change:15m"] = self._calc_price_change_with_fallback(
                    symbol, hist, ts, 900, "5m", 3
                )
                d_snap["price_change:1h"] = self._calc_price_change_with_fallback(
                    symbol, hist, ts, 3600, "1h", 1
                )

        # === Relative Strength vs BTC (exp_btc) ===
        btc_hist = self._history.get("BTCUSDT") or []
        btc_prices_raw = [s.get("price") for s in btc_hist[-30:]] if len(btc_hist) >= 2 else []

        for symbol in self.symbols:
            d_ext = self.data.get(symbol)
            if not d_ext: continue
            alt_hist = self._history.get(symbol) or []
            if len(alt_hist) < 2 or len(btc_prices_raw) < 2:
                d_ext["exp_btc:5m"] = 0.0
                continue

            recent_count = min(len(alt_hist), len(btc_prices_raw), 30)
            alt_prices_raw = [snap.get("price") for snap in alt_hist[-recent_count:]]
            btc_aligned_raw = btc_prices_raw[-recent_count:]

            ratio_series = []
            valid_ratio = True
            for a_v, b_v in zip(alt_prices_raw, btc_aligned_raw):
                if a_v is not None and b_v is not None and float(b_v) != 0:
                    ratio_series.append(float(a_v) / float(b_v))
                else:
                    valid_ratio = False; break
            d_ext["exp_btc:5m"] = self._calc_exp_slope(ratio_series) if valid_ratio and len(ratio_series) >= 2 else 0.0
            # Z-score rolling ARIA (window=14): normaliza exp_btc:5m no contexto histórico recente
            exp_btc_val = d_ext["exp_btc:5m"]
            buf = self._exp_btc_buf.setdefault(symbol, deque(maxlen=14))
            buf.append(exp_btc_val)
            if len(buf) >= 3:
                vals = list(buf)
                mean_v = sum(vals) / len(vals)
                variance = sum((v - mean_v) ** 2 for v in vals) / len(vals)
                std_v = variance ** 0.5
                d_ext["exp_btc_norm_1h"] = round((exp_btc_val - mean_v) / std_v, 4) if std_v > 1e-9 else 0.0
            else:
                d_ext["exp_btc_norm_1h"] = 0.0

        # === Delta % Metrics (CVD, OI, LSR) ===
        for symbol in self.symbols:
            d_ext = self.data.get(symbol)
            if not d_ext: continue
            hist = self._history.get(symbol) or []
            if len(hist) < 2:
                d_ext["cvd_change_pct:5m"] = 0.0
                d_ext["oi_change_pct:5m"] = 0.0
                d_ext["lsr_change_pct:5m"] = 0.0
                continue

            now = ts
            target_ago = now - 300.0  # 5 minutos atrás
            
            best_ago = None
            for snap in reversed(hist):
                s_ts = snap.get("timestamp")
                if s_ts is not None and s_ts <= target_ago:
                    best_ago = snap; break
            
            best_ago = best_ago or hist[0]
            current_snap = hist[-1]

            def calc_pct(now_val, ago_val):
                if now_val is None or ago_val is None or float(ago_val) == 0: return 0.0
                
                # Evitar explosão matemática perto de zero para o CVD (e outros)
                base = abs(float(ago_val))
                diff = float(now_val) - float(ago_val)
                # Adiciona um piso pequeno para o denominador, mitigando crescimentos irreais como +60000%
                # Assumindo que se a base for menor que 10, o % perde sentido direcional sólido
                if base < 10.0:
                    base = 10.0
                
                chg = (diff / base) * 100.0
                return max(-999.9, min(999.9, chg))

            d_ext["cvd_change_pct:5m"] = calc_pct(current_snap.get("cvd"), best_ago.get("cvd")) or 0.0
            d_ext["oi_change_pct:5m"] = calc_pct(current_snap.get("oi"), best_ago.get("oi")) or 0.0
            d_ext["lsr_change_pct:5m"] = calc_pct(current_snap.get("lsr"), best_ago.get("lsr")) or 0.0

    def _calc_price_change_with_fallback(self, symbol: str, hist: List[Dict], current_ts: float, seconds: int, kline_tf: str, kline_offset: int) -> Optional[float]:
        if hist and len(hist) > 0:
            first_ts = hist[0].get("timestamp", 0)
            if (current_ts - first_ts) >= seconds:
                return self._calc_price_change(hist, current_ts, seconds)
        
        if not hist: return None
        curr_snap = hist[-1]
        curr_price = curr_snap.get("price")
        if curr_price is None or float(curr_price) <= 0: return None

        klines = self._klines.get(symbol, {}).get(kline_tf, [])
        target_idx = -(kline_offset + 1)
        if len(klines) >= abs(target_idx):
            old_price = klines[target_idx]
            if old_price > 0:
                return (float(curr_price) / old_price - 1.0) * 100.0
        return None

    def _calc_price_change(self, hist: List[Dict], current_ts: float, seconds: int) -> Optional[float]:
        if not hist: return None
        curr_snap = hist[-1]
        curr_price = curr_snap.get("price")
        if curr_price is None or float(curr_price) <= 0: return None

        target_ts = current_ts - seconds
        best_price = None
        for s in reversed(hist):
            s_ts = s.get("timestamp")
            if s_ts is not None and s_ts <= target_ts:
                best_price = s.get("price")
                break

        if best_price is None and len(hist) > 0:
            oldest = hist[0]
            o_ts = oldest.get("timestamp", 0)
            if current_ts - o_ts > (seconds * 0.5):
                best_price = oldest.get("price")

        if best_price is not None and float(best_price) > 0:
            return ((float(curr_price) - float(best_price)) / float(best_price)) * 100.0
        return None

    def _calc_exp_slope(self, values: Sequence[Optional[float]]) -> float:
        # Filtrar valores None e 0.0 (uninitialized) para evitar quebra de normalização
        valid_values = [v for v in values if v is not None and v != 0.0]
        if len(valid_values) < 2:
            return 0.0
        n = len(valid_values)
        
        # Se todos os valores forem iguais, a inclinação é zero.
        if all(v == valid_values[0] for v in valid_values):
            return 0.0

        x = list(range(n))
        
        # Normalizar os valores para gerar uma inclinação percentual (%)
        base_val = valid_values[0]
        if base_val and base_val != 0:
            y = [((v - base_val) / base_val) * 100.0 for v in valid_values]
        else:
            y = [float(v) for v in valid_values]
            
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        denom = n * sum_xx - sum_x * sum_x
        if denom == 0:
            return 0.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        # y já está em unidades percentuais, o slope é a taxa de variação por snapshot
        return slope
