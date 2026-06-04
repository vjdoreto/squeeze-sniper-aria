# 🔍 PLANO DE AÇÃO: Correção de Gaps de Dados (P0 - CRÍTICO)

## 📊 Diagnóstico do Problema

### Evidências Observadas (Screenshot Dashboard)

**Tabela "Sinais Fortes":**
| Símbolo | CVD Δ% | OI Δ% | LSR Δ% | exp vs BTC | TRADES(1m) | T.lvl | RSI 5m | Status |
|---------|--------|-------|--------|------------|------------|-------|--------|--------|
| HEI | +337.0% | +0.1% | +0.1% | +0.0550 | T:48 | **2×** | **RS:66.9** | ✅ Potencial |
| ALLO | +999.9% | +0.2% | -0.0% | +0.0286 | T:72 | **—** | **RS:53.6** | ✅ Potencial |
| 1000CAT | +999.9% | +0.4% | -0.0% | +0.0221 | T:0 | **—** | **—** | ✅ Potencial |
| 币安人生 | +72.2% | +0.0% | -0.0% | +0.0260 | T:44 | **—** | **—** | ✅ Potencial |
| DYM | +340.1% | +0.1% | -0.0% | +0.0221 | T:0 | **—** | **—** | ✅ Potencial |
| FORM | +999.9% | 0.0% | 0.0% | +0.0232 | T:4 | **1×** | **—** | — |
| MUBARAK | +368.8% | -0.1% | -0.3% | +0.0212 | T:8 | **—** | **—** | — |

**Tabela "Top Símbolos — CVD & % Growth":**
- **T.lvl**: 80% dos símbolos com `—` (sem dados)
- **RSI 5m**: 70% dos símbolos com `—` (sem dados)
- **LSR Δ%**: Muitos com `-0.0%` ou `—` (dados incompletos)
- **OI Δ%**: Alguns com `-0.0%` (suspeito de falha na API)

### Impacto no Sistema

1. **Signal Engine não pode avaliar squeeze** sem dados completos
2. **99.9% de bloqueios** porque métricas críticas estão `None`
3. **DNA quebrado**: `EXP_BTC > OI > HFT > LSR > RSI` não funciona se 60% dos dados estão ausentes
4. **Falsos positivos**: Símbolos marcados como "Potencial" mas sem RSI/T.lvl para confirmar

---

## 🎯 Causa Raiz Provável

### Hipótese 1: Polling de OI/LSR Incompleto (80% provável)

**Arquivo**: `src/data_engine.py`

**Problema**:
- OI/LSR são coletados via **REST API** a cada 8-10s
- Se a API falhar ou demorar, o símbolo fica sem dados até o próximo ciclo
- Não há **fallback** ou **cache** para dados ausentes

**Evidência**:
```python
# data_engine.py - Linha ~400
async def _poll_oi_lsr_batch(self, symbols: List[str]) -> None:
    tasks = [self._fetch_oi_lsr(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Se falhar, o símbolo fica sem OI/LSR até próximo ciclo
```

### Hipótese 2: RSI/T.lvl Não Calculados (60% provável)

**Arquivo**: `src/metric_engine.py`

**Problema**:
- RSI precisa de **14 períodos** de dados históricos
- T.lvl (Trailing Level) precisa de **swing_low** calculado
- Se o símbolo é novo ou teve gap de dados, RSI/T.lvl ficam `None`

**Evidência**:
```python
# metric_engine.py - Linha ~200
def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    if len(prices) < period:
        return None  # ← Retorna None se não tiver dados suficientes
```

### Hipótese 3: WebSocket Drops (40% provável)

**Arquivo**: `src/data_engine.py`

**Problema**:
- AggTrades vêm via **WebSocket**
- Se a conexão cair ou tiver lag, o símbolo fica sem CVD/Trades
- Não há **reconexão automática** robusta

---

## 🔧 Plano de Correção (Sprints P0 → P2)

### **P0 - CRÍTICO: Auditoria de Dados (Sprint 1 - 2h)**

#### Objetivo
Identificar **exatamente** quais métricas estão faltando e por quê.

#### Tarefas

1. **Adicionar logging de gaps de dados**
   ```python
   # src/data_engine.py
   def _log_data_gaps(self, symbol: str, metrics: Dict) -> None:
       gaps = []
       if metrics.get("oi") is None:
           gaps.append("OI")
       if metrics.get("lsr") is None:
           gaps.append("LSR")
       if metrics.get("rsi_5m") is None:
           gaps.append("RSI")
       if metrics.get("swing_low:5m") is None:
           gaps.append("T.lvl")
       
       if gaps:
           logger.warning(f"⚠️ GAPS DE DADOS {symbol}: {', '.join(gaps)}")
           self._append_debug({
               "ts": time.time(),
               "event": "data_gaps",
               "symbol": symbol,
               "missing": gaps
           })
   ```

2. **Criar endpoint de diagnóstico**
   ```python
   # src/web_dashboard.py
   @app.get("/api/data-health")
   async def get_data_health():
       """Retorna % de completude de dados por símbolo"""
       health = {}
       for sym in engine.store.symbols:
           metrics = engine.store.get(sym)
           complete = sum([
               metrics.get("oi") is not None,
               metrics.get("lsr") is not None,
               metrics.get("rsi_5m") is not None,
               metrics.get("swing_low:5m") is not None,
               metrics.get("cvd_1m") is not None
           ])
           health[sym] = {
               "completeness_pct": (complete / 5) * 100,
               "missing": [k for k in ["oi", "lsr", "rsi_5m", "swing_low", "cvd"] 
                          if metrics.get(k) is None]
           }
       return {"ok": True, "health": health}
   ```

3. **Adicionar painel "Data Health" no dashboard**
   - Mostrar % de completude por símbolo
   - Destacar símbolos com <80% de dados
   - Alertar se >30% dos símbolos tiverem gaps

#### Entregáveis
- `logs/data_gaps.jsonl` com registro de gaps
- Endpoint `/api/data-health` funcional
- Painel "Data Health" no dashboard

---

### **P1 - ALTA: Fallback e Cache (Sprint 2 - 4h)**

#### Objetivo
Garantir que **dados ausentes não bloqueiem sinais** usando fallback inteligente.

#### Tarefas

1. **Implementar cache de última métrica válida**
   ```python
   # src/metric_engine.py
   class MetricStore:
       def __init__(self):
           self._cache: Dict[str, Dict[str, Any]] = {}
           self._last_valid: Dict[str, Dict[str, Any]] = {}
       
       def set(self, symbol: str, key: str, value: Any) -> None:
           if value is not None:
               self._last_valid.setdefault(symbol, {})[key] = {
                   "value": value,
                   "ts": time.time()
               }
           self._cache.setdefault(symbol, {})[key] = value
       
       def get(self, symbol: str, key: str, max_age_seconds: int = 60) -> Any:
           current = self._cache.get(symbol, {}).get(key)
           if current is not None:
               return current
           
           # Fallback: usa último valor válido se <60s
           last = self._last_valid.get(symbol, {}).get(key)
           if last and (time.time() - last["ts"]) < max_age_seconds:
               logger.debug(f"📦 CACHE FALLBACK {symbol}.{key}: {last['value']} ({int(time.time() - last['ts'])}s ago)")
               return last["value"]
           
           return None
   ```

2. **Implementar retry para OI/LSR**
   ```python
   # src/data_engine.py
   async def _fetch_oi_lsr_with_retry(self, symbol: str, retries: int = 2) -> None:
       for attempt in range(retries + 1):
           try:
               oi = await self.client.futures_open_interest(symbol=symbol)
               lsr = await self.client.futures_global_long_short_ratio(symbol=symbol, period="5m")
               # Sucesso
               return
           except Exception as e:
               if attempt < retries:
                   await asyncio.sleep(0.5)
               else:
                   logger.error(f"❌ OI/LSR falhou após {retries+1} tentativas: {symbol}")
   ```

3. **Implementar cálculo de RSI com dados parciais**
   ```python
   # src/metric_engine.py
   def calculate_rsi_adaptive(prices: List[float], min_period: int = 7) -> Optional[float]:
       """Calcula RSI com período adaptativo (mínimo 7 em vez de 14)"""
       if len(prices) < min_period:
           return None
       
       period = min(14, len(prices))  # Usa 14 se possível, senão usa o que tiver
       # ... cálculo RSI
   ```

#### Entregáveis
- Cache de última métrica válida (60s)
- Retry automático para OI/LSR (2 tentativas)
- RSI adaptativo (mínimo 7 períodos)

---

### **P2 - MÉDIA: Reconexão WebSocket Robusta (Sprint 3 - 3h)**

#### Objetivo
Garantir que **WebSocket nunca fique offline** por mais de 10 segundos.

#### Tarefas

1. **Implementar heartbeat de WebSocket**
   ```python
   # src/data_engine.py
   async def _websocket_heartbeat(self) -> None:
       """Monitora saúde do WebSocket e reconecta se necessário"""
       while True:
           await asyncio.sleep(10)
           
           # Verifica se recebeu dados nos últimos 15s
           now = time.time()
           for sym in self.symbols:
               last_update = self.store.get_last_update(sym)
               if last_update and (now - last_update) > 15:
                   logger.warning(f"⚠️ WebSocket stale para {sym} ({int(now - last_update)}s)")
                   # Reconecta
                   await self._reconnect_websocket(sym)
   ```

2. **Adicionar métricas de latência**
   ```python
   # src/data_engine.py
   def _track_websocket_latency(self, symbol: str, event_time: int) -> None:
       latency_ms = (time.time() * 1000) - event_time
       if latency_ms > 1000:
           logger.warning(f"⚠️ WebSocket lag {symbol}: {int(latency_ms)}ms")
   ```

#### Entregáveis
- Heartbeat de WebSocket (10s)
- Reconexão automática se >15s sem dados
- Métricas de latência no dashboard

---

## 📈 Métricas de Sucesso

### Antes (Estado Atual)
- **Completude de dados**: ~40% (60% com gaps)
- **Sinais bloqueados**: 99.9%
- **Trades por hora**: 0-2

### Depois (Meta P0+P1)
- **Completude de dados**: >90% (cache + fallback)
- **Sinais bloqueados**: <60%
- **Trades por hora**: 20-40

### Depois (Meta P0+P1+P2)
- **Completude de dados**: >95% (WebSocket robusto)
- **Sinais bloqueados**: <50%
- **Trades por hora**: 40-60

---

## 🚀 Implementação Imediata (Próximos Passos)

1. **Agora**: Implementar logging de gaps (P0.1)
2. **Hoje**: Criar endpoint `/api/data-health` (P0.2)
3. **Amanhã**: Implementar cache de fallback (P1.1)
4. **Esta semana**: Retry OI/LSR + RSI adaptativo (P1.2 + P1.3)

---

## 💡 Conclusão

Você estava **100% certo**: o problema não são os thresholds, é a **qualidade dos dados**. Não adianta relaxar filtros se 60% das métricas estão `None`. 

O bot está tentando detectar squeezes com **dados incompletos**, como tentar dirigir com os olhos vendados.

**Prioridade absoluta**: Implementar P0 (auditoria) e P1 (fallback) antes de ajustar mais thresholds.

---

**Quer que eu implemente P0.1 (logging de gaps) agora?**