# Auditoria P0 — Correções Aplicadas (Parcialmente com Bugs)

**Data**: 2026-05-30  
**Auditor**: Bob (Engenheiro Sênior Python/Trading Systems)  
**Escopo**: Verificação das correções P0 descritas em `docs/Engenheiro e DNA do Sniper.md`

---

## ✅ CORREÇÕES APLICADAS CORRETAMENTE

### 1. **Helpers de Modo em `config.py`** ✅
- `get_mode_node()`, `get_mode_signal()`, `get_mode_execution()` implementados corretamente
- Isolamento de configuração por modo (paper/live) funcional
- Fallback para nó raiz quando modo específico não existe

### 2. **`_apply_runtime_mode()` em `main.py`** ✅
- Função centralizada para troca de modo implementada (linha 1272)
- Sincroniza `state.trading_mode`, `sniper.trading_mode` e `signal_engine`
- Aplica configurações específicas de cada modo (paper vs live)
- Persiste modo em preferences quando `persist=True`
- **CRÍTICO**: `state.bind_sniper(sniper)` chamado na linha 1293 ✅

### 3. **Boot Seguro em PAPER** ✅
- Linha 1691: `state.trading_mode = "paper"` forçado no boot
- Linha 1748: `Sniper` criado com `trading_mode="paper"`
- Bloco de reativação automática de LIVE removido (comentário linha 1740)
- Warmup de 300s ativado no boot (linha 1704)

### 4. **`BotState.bind_sniper()`** ✅
- Método existe em `bot_state.py` (linhas 152-154)
- Chamado em `_apply_runtime_mode()` linha 1293

---

## ❌ BUGS CRÍTICOS ENCONTRADOS

### **BUG #1: IDs HTML Inconsistentes no Dashboard LIVE** 🔴 P0

**Localização**: `src/web_dashboard.py` linhas 2292-2293

**Problema**:
```javascript
// JavaScript tenta ler:
const usdtAmount = parseFloat(document.getElementById('liveUsdtInput').value) || 12;
const riskPct = parseFloat(document.getElementById('liveRiskInput').value) || 5;

// Mas o HTML define:
<input id="liveInitialCapitalInput" ... />  // linha 470
<input id="liveRiskPctInput" ... />         // linha 474
```

**Impacto**:
- Botão "Atualizar Live" não funciona
- Configurações LIVE não são persistidas
- Usuário altera valores mas nada acontece

**Correção Necessária**:
```javascript
// Linha 2292-2293 deve ser:
const usdtAmount = parseFloat(document.getElementById('liveInitialCapitalInput').value) || 12;
const riskPct = parseFloat(document.getElementById('liveRiskPctInput').value) || 5;
```

---

### **BUG #2: Indentação Quebrada em `_apply_runtime_mode()`** 🔴 P0

**Localização**: `main.py` linhas 1287-1336

**Problema**:
```python
def _apply_runtime_mode(...):
    mode = str(mode).strip().lower()
    if mode not in {"paper", "live"}:
        return {"ok": False, "error": "invalid mode"}

     prefs = load_preferences(prefs_path)  # ❌ Indentação errada (5 espaços)
     mode_node = get_mode_node(prefs, mode)
     # ... resto do bloco com indentação errada
```

**Impacto**:
- Código não executa (IndentationError em Python)
- Troca de modo quebrada
- Bot não consegue alternar entre PAPER e LIVE

**Correção Necessária**:
Remover 1 espaço de todas as linhas 1287-1336 para alinhar com o padrão de 4 espaços.

---

### **BUG #3: Falta Chamada de `_apply_runtime_mode()` no Boot** 🟡 P1

**Localização**: `main.py` após linha 1748

**Problema**:
- `Sniper` é criado com valores de `cfg` (linha 1743-1750)
- `state.trading_mode = "paper"` é setado (linha 1691)
- **MAS** `_apply_runtime_mode()` não é chamado para sincronizar tudo

**Impacto**:
- Sniper pode nascer com configurações de LIVE se `preferences.json` tiver `trading_mode: "live"`
- Split-brain parcial: state diz PAPER, mas sniper pode ter params de LIVE

**Correção Necessária**:
```python
# Após linha 1750, adicionar:
state.bind_sniper(sniper)
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
```

---

### **BUG #4: Endpoint `/api/live-advanced-config` Não Encontrado** 🟡 P1

**Problema**:
- Documento menciona endpoint para reidratar configs avançadas LIVE
- Não encontrado em `web_dashboard.py` nos trechos lidos
- Pode estar faltando ou em outra parte do arquivo

**Impacto**:
- Dashboard não consegue carregar SL/TP/trailing/kelly do LIVE
- Usuário vê valores padrão ao invés dos salvos

**Ação Necessária**:
Verificar se endpoint existe e se lê de `prefs["live"]["execution"]` e `prefs["live"]["signal"]`.

---

## 🟢 PONTOS POSITIVOS

1. **Arquitetura de Isolamento**: Helpers de modo bem desenhados
2. **Boot Seguro**: Protocolo de segurança implementado (sempre PAPER)
3. **Warmup Gate**: 300s de warmup ativo no boot
4. **Compound Tracking**: Estado de compound sincronizado entre sniper e state
5. **Logging Detalhado**: `_apply_runtime_mode()` loga todas as mudanças

---

## 📋 CHECKLIST DE CORREÇÃO P0

- [ ] **BUG #1**: Corrigir IDs HTML no event listener do botão "Atualizar Live"
- [ ] **BUG #2**: Corrigir indentação em `_apply_runtime_mode()`
- [ ] **BUG #3**: Adicionar chamada de `_apply_runtime_mode()` após criar Sniper no boot
- [ ] **BUG #4**: Verificar/implementar endpoint `/api/live-advanced-config`
- [ ] Testar troca PAPER → LIVE via dashboard
- [ ] Testar persistência de configurações LIVE
- [ ] Validar que boot sempre inicia em PAPER independente de preferences.json

---

## 🔍 PRÓXIMOS PASSOS

1. **Corrigir bugs P0** (acima)
2. **Auditar paridade paper_tracker vs live_tracker**:
   - Correlation guard
   - Partial breakeven
   - Trailing real
   - Close confirmation
   - Debug JSONL
3. **Atualizar documentação**:
   - GOVERNANCE.md
   - ARCHITECTURE.md
   - README.md

---

## 💡 RECOMENDAÇÕES ADICIONAIS

### Performance
- Dashboard recalcula score a cada 1s no loop crítico (linha 346 main.py)
- Considerar cache de 2-3s para scores quando não há sinais ativos

### Governança
- LiveTracker mais simples que PaperTracker (falta governança)
- Portar features do paper para live: correlation guard, partial TP, trailing

### Telemetria
- Fragmentação de JSONL entre tracker e monitor (linha 944 main.py)
- Unificar persistência LIVE no LiveTracker

---

**Status Final**: ⚠️ **CORREÇÕES APLICADAS PARCIALMENTE COM BUGS CRÍTICOS**

**Recomendação**: 🔴 **NÃO RODAR LIVE ATÉ CORRIGIR BUGS #1, #2 e #3**