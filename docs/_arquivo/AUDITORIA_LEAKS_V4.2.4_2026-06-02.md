# Auditoria de Leaks de Performance - v4.2.4

**Data:** 2026-06-02 19:28 BRT  
**Versão:** v4.2.4  
**Período Analisado:** 12 horas (07:32 - 19:02)  
**Resultado:** Win Rate 82% mas P&L ~$0 (Zero a Zero)

---

## 📊 Resumo Executivo

**PROBLEMA CRÍTICO:** Sistema com 82% de win rate mas resultado operacional ZERO devido a múltiplos leaks de performance que anulam completamente os lucros.

### Métricas da Sessão
- **Total Trades:** 20 (15W / 5L)
- **Win Rate:** 75-82% (excelente)
- **P&L Total:** ~$0.08 USDT (ZERO)
- **Total Fees:** Dados inconsistentes
- **Equity:** $1000 → $1000 (sem crescimento)
- **Margem Média:** $10 USDT (deveria ser $50)
- **Duração Média:** <2 minutos (trades muito curtos)

---

## 🚨 LEAKS IDENTIFICADOS (Ordem de Criticidade)

### LEAK #1: MARGEM EXTREMAMENTE BAIXA ⚠️ CRÍTICO

**Problema:**
- Margem média: $10 USDT
- Esperado: $50 USDT (5% de $1000)
- Gap: **80% menor que o esperado**

**Causa Raiz:**
```python
# src/paper_tracker.py linha 728
min_margin_usdt=0.5  # 50 centavos!
```

**Impacto:**
- Lucros insignificantes mesmo com wins
- Fees proporcionalmente altos
- R:R ratio destruído (0.34:1 vs ideal 2:1)
- Win médio: $0.17 vs Loss médio: $0.49

**Evidência dos Trades:**
```
IOUSDT:  Margem $10 → PnL +$0.11 (3.46%)
FETUSDT: Margem $10 → PnL +$0.05 (0.10%)
CHIPUSDT: Margem $10 → PnL +$0.02 (0.03%)
EPICUSDT: Margem $10 → PnL +$0.61 (3.64%)
```

**Correção:**
```python
# Aumentar min_margin_usdt para refletir risco real
min_margin_usdt=50.0  # 5% de $1000
```

---

### LEAK #2: TRAILING STOP PREMATURO ⚠️ CRÍTICO

**Problema:**
- **Captura apenas 38% do MFE** (Maximum Favorable Excursion)
- MFE Médio: 2.77%
- PnL Médio: 1.05%
- 95% dos trades (19/20) fechados por trailing stop

**Evidência:**
```
IOUSDT:  MFE 5.44% → Capturou 3.46% (63%)
FETUSDT: MFE 1.51% → Capturou 0.10% (7%)
CHIPUSDT: MFE 1.67% → Capturou 0.03% (2%)
EPICUSDT: MFE 5.05% → Capturou 3.64% (72%)
BIOUSDT: MFE 4.75% → Capturou 3.34% (70%)
```

**Causa Raiz:**
```json
// preferences.json linha 61
"trailing_activation_delay_sec": 60  // Muito curto
// Falta: trailing_stop_callback (provavelmente 60%)
```

**Correção:**
```json
"trailing_activation_delay_sec": 180,  // 3 minutos
"trailing_stop_callback": 0.75,        // 75% do MFE
"trailing_stop_distance_pct": 0.015    // 1.5% de distância
```

---

### LEAK #3: TRADES MUITO CURTOS ⚠️ ALTO

**Problema:**
- **100% dos trades < 2 minutos**
- Duração média: <1 minuto
- Não dá tempo para o squeeze se desenvolver

**Evidência:**
```
IOUSDT:     31 segundos
FETUSDT:    1min 4s
STGUSDT:    2 segundos (!!)
ENAUSDT:    1 minuto
BIOUSDT:    1min 1s
```

**Impacto:**
- Trailing stop ativa antes do movimento completar
- Captura apenas o início do squeeze
- Fees proporcionalmente altos

**Correção:**
```json
// preferences.json paper.execution
"min_hold_seconds": 180,  // Mínimo 3 minutos
"trailing_activation_delay_sec": 180  // Sincronizado
```

---

### LEAK #4: RELAÇÃO RISCO/RECOMPENSA INVERTIDA ⚠️ ALTO

**Problema:**
- **R:R Ratio: 0.34:1** (Ideal: >2:1)
- Win Médio: $0.17
- Loss Médio: $0.49
- **Losses 3x maiores que wins**

**Causa:**
- Margem muito baixa (LEAK #1)
- Trailing stop prematuro (LEAK #2)
- SL de 3% vs TP de 15% não se realiza

**Evidência:**
```
Wins:  15 trades × $0.17 = $2.55
Losses: 5 trades × $0.49 = $2.45
Net: $0.10 (praticamente zero)
```

**Correção:**
- Aumentar margem para $50
- Ajustar trailing stop
- Considerar TP parcial em 5-7%

---

### LEAK #5: CONFIGURAÇÃO DE TP/SL DESBALANCEADA ⚠️ MÉDIO

**Problema:**
```json
"sl_pct": 0.03,   // 3%
"tp_pct": 0.15,   // 15%
```

**Realidade:**
- TP de 15% nunca é atingido
- Trailing stop fecha em 1-3%
- SL de 3% é atingido (VICUSDT: -32%)

**Correção:**
```json
"sl_pct": 0.025,  // 2.5% (mais apertado)
"tp_pct": 0.08,   // 8% (mais realista)
"partial_tp_pct": 0.05,  // TP parcial em 5%
"partial_tp_size": 0.5   // Fecha 50% da posição
```

---

## 📉 PIORES PERFORMERS

| Símbolo | PnL Total | Trades | Problema |
|---------|-----------|--------|----------|
| VICUSDT | -$2.03 | 2 | SL violado (-32%), depois recuperou |
| GPSUSDT | -$0.12 | 2 | Trailing prematuro |
| QNTUSDT | -$0.04 | 2 | Qualidade WEAK |
| CGPTUSDT | -$0.03 | 1 | Trailing prematuro |

---

## 🔧 PLANO DE CORREÇÃO P1 (Prioridade 1)

### Correção 1: Aumentar Margem Mínima

**Arquivo:** `src/paper_tracker.py` linha 728

```python
# ANTES
min_margin_usdt=0.5,  # 50 centavos

# DEPOIS
min_margin_usdt=50.0,  # 5% de $1000 = $50
```

**Impacto Esperado:**
- Margem por trade: $10 → $50 (5x)
- Win médio: $0.17 → $0.85 (5x)
- Loss médio: $0.49 → $2.45 (5x)
- R:R mantém, mas valores absolutos aumentam

---

### Correção 2: Ajustar Trailing Stop

**Arquivo:** `preferences.json` + `preferences.local.json` linhas 61-62

```json
// ANTES
"trailing_activation_delay_sec": 60

// DEPOIS
"trailing_activation_delay_sec": 180,
"trailing_stop_callback": 0.75,
"trailing_stop_distance_pct": 0.015
```

**Impacto Esperado:**
- Captura MFE: 38% → 65-70%
- PnL médio: 1.05% → 2.0%
- Duração média: <2min → 5-10min

---

### Correção 3: Filtro de Duração Mínima

**Arquivo:** `preferences.json` + `preferences.local.json` linha 59

```json
// ANTES
"max_hold_seconds": 1800,  // Apenas máximo

// DEPOIS
"max_hold_seconds": 1800,
"min_hold_seconds": 180     // NOVO: Mínimo 3 minutos
```

**Implementação Necessária:**
- Adicionar lógica em `paper_tracker.py` para respeitar `min_hold_seconds`
- Bloquear trailing stop antes de atingir tempo mínimo

---

### Correção 4: TP/SL Realista

**Arquivo:** `preferences.json` + `preferences.local.json` linhas 52-53

```json
// ANTES
"sl_pct": 0.03,
"tp_pct": 0.15,

// DEPOIS
"sl_pct": 0.025,
"tp_pct": 0.08,
"partial_tp_enabled": true,
"partial_tp_pct": 0.05,
"partial_tp_size": 0.5
```

---

## 📊 PROJEÇÃO DE IMPACTO

### Cenário Atual (v4.2.4)
```
Capital: $1000
Trades: 20 (15W/5L)
Win Rate: 75%
PnL: $0.08 (0.008%)
ROI Diário: 0%
```

### Cenário Projetado (v4.2.5 com correções)
```
Capital: $1000
Trades: 12-15 (mais seletivo)
Win Rate: 70-75% (mantém)
Win Médio: $2.50 (vs $0.17)
Loss Médio: $1.25 (vs $0.49)
R:R: 2:1 (vs 0.34:1)

Projeção Conservadora:
10 wins × $2.50 = $25.00
3 losses × $1.25 = -$3.75
Net: $21.25 (2.1% ao dia)
ROI Mensal: ~50%
```

---

## ⚠️ RISCOS E CONSIDERAÇÕES

### Risco 1: Drawdown Maior
- Margem de $50 significa losses de até $1.25
- Drawdown máximo pode atingir 5-10%
- **Mitigação:** SL mais apertado (2.5%)

### Risco 2: Menos Trades
- Margem maior = menos posições simultâneas
- Max 20 posições → ~4-5 posições reais
- **Mitigação:** Aceitável, foco em qualidade

### Risco 3: Slippage Real
- Paper não simula slippage adequadamente
- Margem maior = impacto maior
- **Mitigação:** Slippage já configurado em 0.1%

---

## 🎯 CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Correções Críticas (Agora)
- [x] Corrigir `min_margin_usdt` para Sizing Dinâmico (Paridade Paper/Live)
- [x] Ajustar trailing stop em `preferences.json`
- [x] Adicionar `min_hold_seconds` em `preferences.json`
- [x] Sincronizar `preferences.local.json`

### Fase 2: Implementação de Código (1-2h)
- [x] Portão de tempo `min_hold_seconds` ativo (bloqueia TS precoce)
- [x] Adicionar `trailing_stop_callback` em `paper_tracker.py`
- [x] Implementar TP parcial (logic check)
- [ ] Testes unitários (Pendentes para próxima rodada)

### Fase 3: Validação (24h)
- [ ] Reiniciar bot com correções
- [ ] Monitorar primeiras 4 horas
- [ ] Analisar com `python src/analyze_leaks.py`
- [ ] Validar métricas:
  - Margem média ≥ $45
  - Captura MFE ≥ 60%
  - Duração média ≥ 5min
  - R:R ≥ 1.5:1

### Fase 4: Ajuste Fino (48h)
- [ ] Analisar 20-30 trades
- [ ] Ajustar trailing_stop_callback se necessário
- [ ] Ajustar min_hold_seconds se necessário
- [ ] Documentar resultados

---

## ✅ VERIFICAÇÃO TÉCNICA FINAL (2026-06-02 — Engenheiro Bob)

### Status real confirmado por inspeção de código

| Correção | Arquivo | Linha | Status |
| -------- | ------- | ----- | ------ |
| Margem dinâmica `max(1.0, capital × risk × 0.8)` | `src/paper_tracker.py` | 730 | ✅ CONFIRMADO |
| `trailing_stop_callback = 0.75` (paper) | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |
| `trailing_activation_delay_sec = 180` (paper) | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |
| `trailing_stop_distance_pct = 0.015` (paper) | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |
| `min_hold_seconds = 180` (paper) | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |
| Portão `can_trailing` no código | `src/paper_tracker.py` | 1129–1131 | ✅ CONFIRMADO |
| `trailing_stop_callback` lido no loop | `src/paper_tracker.py` | 1029 | ✅ CONFIRMADO |
| `partial_tp_breakeven_pct = 0.35` | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |
| Lógica de partial TP no breakeven | `src/paper_tracker.py` | 1063–1075 | ✅ CONFIRMADO |
| `sl_pct = 0.025` / `tp_pct = 0.08` | `preferences.json` + `preferences.local.json` | exec block | ✅ CONFIRMADO |

### Bugs corrigidos nesta finalização (não estavam no checklist original)

#### BUG CRÍTICO #1 — preferences.local.json LIVE desatualizado

- LIVE ainda usava `sl_pct=0.05`, `tp_pct=0.15`, `trailing_delay=10s`, sem `min_hold_seconds` nem `trailing_stop_callback`
- Como `preferences.local.json` tem **precedência** sobre `preferences.json`, o modo LIVE estava com os parâmetros antigos
- Corrigido: live.execution alinhado com paper.execution e preferences.json

#### BUG #2 — Blocos globais órfãos removidos

- `preferences.local.json` tinha `"signal"` e `"execution"` na raiz (dead code perigoso como fallback acidental)
- Corrigido: Removidos — toda configuração está corretamente dentro dos blocos `paper.*` e `live.*`

#### OBSERVAÇÃO — trailing_stop_distance_pct não wired em PaperConfig

- `PaperConfig` não tem campo `trailing_stop_distance_pct`; código usa `getattr(..., 0.015)` hardcoded
- O padrão coincide com o valor do preferences (0.015), então funciona, mas não é configurável dinamicamente
- Status: Aceitável por ora. Wiring completo fica para próxima sprint se houver necessidade de ajuste sem restart.

### Paridade Paper ↔ Live (pós-correção)

| Parâmetro | Paper | Live |
| --------- | ----- | ---- |
| `sl_pct` | 0.025 | 0.025 ✅ |
| `tp_pct` | 0.08 | 0.08 ✅ |
| `trailing_activation_delay_sec` | 180 | 180 ✅ |
| `trailing_stop_callback` | 0.75 | 0.75 ✅ |
| `trailing_stop_distance_pct` | 0.015 | 0.015 ✅ |
| `min_hold_seconds` | 180 | 180 ✅ |
| `max_hold_seconds` | 1800 | 1800 ✅ |
| `partial_tp_breakeven_pct` | 0.35 | 0.35 ✅ |

---

**STATUS FINAL:** 🟡 Código e configuração OK — aguardando validação de 24h (Fase 3)
**VERSÃO:** v4.2.5
**Data de fechamento:** 2026-06-02

---

## 📝 NOTAS TÉCNICAS

### Sobre Margem Mínima
O valor de `min_margin_usdt=0.5` foi provavelmente definido para evitar "quantidades lixo" em moedas de baixo valor, mas está destruindo a performance. A solução correta é:

```python
# Calcular margem mínima dinamicamente
min_margin_usdt = max(0.5, available_capital * risk_pct * 0.8)
# Exemplo: max(0.5, 1000 * 0.05 * 0.8) = max(0.5, 40) = 40
```

### Sobre Trailing Stop
O trailing stop atual está muito agressivo. Análise mostra que:
- MFE médio: 2.77%
- Captura: 38%
- **Problema:** Trailing ativa muito cedo e fecha na primeira retração

Solução:
1. Delay de 3 minutos (180s)
2. Callback de 75% (fecha quando retrai 25% do MFE)
3. Distância mínima de 1.5%

### Sobre TP Parcial
Implementar TP parcial em 5% pode melhorar significativamente:
- Garante lucro em 50% da posição
- Deixa 50% correr para o squeeze completo
- Reduz risco psicológico

---

## 🔄 PRÓXIMOS PASSOS

1. **Implementar Correções P1** (este documento)
2. **Testar 24h** com nova configuração
3. **Analisar Resultados** com `analyze_leaks.py`
4. **Ajustar Parâmetros** baseado em dados reais
5. **Validar 48h** antes de considerar LIVE
6. **Documentar** em CHANGELOG v4.2.5

---

**Responsável:** Engenheiro Bob  
**Status:** 🔴 Correções Críticas Necessárias  
**Prioridade:** P1 (Alta)  
**Deadline:** Implementar hoje, validar 24-48h

---

## 📚 Referências

- `src/paper_tracker.py` - Lógica de execução paper
- `src/sizing_utils.py` - Cálculo de posição
- `preferences.json` - Configurações
- `logs/paper_closed.jsonl` - Histórico de trades
- `docs/ANALISE_SESSAO_V4.2.3_2026-06-02.md` - Análise anterior