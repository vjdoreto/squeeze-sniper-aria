# Plano de Implementação Completo — SqueezeSniper V4

**Data**: 2026-05-30  
**Objetivo**: Implementar paridade paper/live + otimizações + documentação  
**DNA Preservado**: EXP_BTC > OI > HFT > LSR > RSI > CVD > OrderBook

---

## 🎯 FASE 1: PARIDADE PAPER_TRACKER vs LIVE_TRACKER

### 1.1 Correlation Guard (DNA Sniper)
**Arquivo**: `src/live_tracker.py`  
**Status**: ❌ FALTANDO  
**Implementação**:
```python
# Grupos de correlação (já existe em paper_tracker.py linha 22-26)
CORR_GROUPS = {
    "L1": ["SOLUSDT", "AVAXUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT"],
    "DeFi": ["AAVEUSDT", "UNIUSDT", "CRVUSDT"],
    "Meme": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT"],
}

def _check_correlation_guard(self, symbol: str) -> bool:
    """Evita abrir múltiplas posições no mesmo grupo de correlação."""
    for group_name, symbols in CORR_GROUPS.items():
        if symbol in symbols:
            for open_sym in self._open.keys():
                if open_sym in symbols and open_sym != symbol:
                    logger.warning(
                        "🛡️ Correlation guard: %s bloqueado (já existe %s no grupo %s)",
                        symbol, open_sym, group_name
                    )
                    return False
    return True
```

### 1.2 Partial Breakeven (DNA Sniper)
**Arquivo**: `src/live_tracker.py`  
**Status**: ✅ FLAGS EXISTEM (linha 185-186) mas lógica de execução FALTANDO  
**Implementação**: Adicionar método `_handle_partial_breakeven()` similar ao paper_tracker

### 1.3 Trailing Real (DNA Sniper)
**Arquivo**: `src/live_tracker.py`  
**Status**: ❌ FALTANDO  
**Implementação**: Portar lógica de `sl_trailing_swing_low` do paper_tracker

### 1.4 Close Confirmation (DNA Sniper)
**Arquivo**: `src/live_tracker.py`  
**Status**: ❌ FALTANDO  
**Implementação**: Adicionar validação de fechamento com confirmação de preço

### 1.5 Debug JSONL Unificado
**Arquivo**: `src/live_tracker.py`  
**Status**: ❌ FALTANDO  
**Implementação**: Adicionar `_append_debug()` similar ao paper_tracker (linha 281-288)

---

## 🚀 FASE 2: OTIMIZAÇÕES DE PERFORMANCE

### 2.1 Cache de Scores (2-3s)
**Arquivo**: `main.py` linha 346  
**Status**: ❌ FALTANDO  
**Problema**: Recalcula score a cada 1s no loop crítico  
**Solução**:
```python
# Adicionar cache com timestamp
_score_cache = {}
_score_cache_ttl = 2.0  # segundos

def _get_cached_score(symbol: str, data: dict) -> float:
    now = time.time()
    cache_key = symbol
    if cache_key in _score_cache:
        cached_score, cached_ts = _score_cache[cache_key]
        if (now - cached_ts) < _score_cache_ttl:
            return cached_score
    
    score = calculate_fit_score(data)
    _score_cache[cache_key] = (score, now)
    return score
```

### 2.2 Otimizar Recalculo de Dashboard
**Arquivo**: `main.py` linha 334-350  
**Status**: ❌ PRECISA OTIMIZAÇÃO  
**Problema**: Copia dicionários, ordena múltiplas vezes  
**Solução**: Unificar em um único loop, evitar cópias desnecessárias

---

## 📚 FASE 3: DOCUMENTAÇÃO

### 3.1 Atualizar GOVERNANCE.md
**Conteúdo a adicionar**:
- Protocolo de boot seguro (SEMPRE PAPER)
- Validação LIVE (warmup + saldo)
- Correlation guard
- Partial breakeven
- Trailing stop
- Max hold time

### 3.2 Atualizar ARCHITECTURE.md
**Conteúdo a adicionar**:
- Diagrama de isolamento paper/live
- Fluxo de `_apply_runtime_mode()`
- Cache de scores
- Persistência unificada

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Paridade Paper/Live
- [ ] Correlation guard em live_tracker
- [ ] Partial breakeven em live_tracker
- [ ] Trailing real em live_tracker
- [ ] Close confirmation em live_tracker
- [ ] Debug JSONL em live_tracker

### Performance
- [ ] Cache de scores (2-3s TTL)
- [ ] Otimizar loop de dashboard
- [ ] Reduzir cópias de dicionários

### Documentação
- [ ] Atualizar GOVERNANCE.md
- [ ] Atualizar ARCHITECTURE.md
- [ ] Criar CHANGELOG.md com mudanças

---

## 🛡️ DNA DO SNIPER (IMUTÁVEL)

**Hierarquia de Sinais**:
1. EXP_BTC (força relativa ao BTC)
2. OI (Open Interest subindo)
3. HFT Trades (volume de trades)
4. LSR (Long/Short Ratio caindo)
5. RSI (alto = combustível, não bloqueio)
6. CVD (Cumulative Volume Delta)
7. OrderBook + Liquidity Cascades

**Regras Imutáveis**:
- ✅ LONG only
- ❌ PROIBIDO: Hedge, modo cruzado, stop abaixo de liquidação
- ✅ Warmup 300s obrigatório
- ✅ Correlation guard ativo
- ✅ Partial breakeven em lucro
- ✅ Trailing stop por swing low

---

## 📊 PRIORIZAÇÃO

**P0 (Crítico)**: Correlation guard, Debug JSONL  
**P1 (Alto)**: Partial breakeven, Trailing real, Cache de scores  
**P2 (Médio)**: Close confirmation, Otimização de dashboard  
**P3 (Baixo)**: Documentação completa

---

**Próximo Passo**: Implementar correlation guard e debug JSONL no live_tracker