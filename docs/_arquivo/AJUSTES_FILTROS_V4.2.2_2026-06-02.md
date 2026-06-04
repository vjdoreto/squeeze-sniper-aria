# Ajustes de Filtros e DNA PTP - v4.2.2

**Data**: 2026-06-02  
**Versão**: 4.2.2  
**Tipo**: Otimização de Filtros + Correção de Trailing Stop

---

## 🎯 Objetivo

Reduzir taxa de bloqueio de sinais de 99.9% para ~70-80% através de ajustes nos filtros, e garantir que o trailing stop de 60s seja respeitado.

---

## 📊 Análise dos Logs PRÉ-AJUSTE

### **Sessão de 15 minutos (00:19 - 00:36)**

**Estatísticas**:
- Total de sinais avaliados: ~15.508
- Sinais bloqueados: ~15.507 (99.9%)
- Trades executados: 1 (RENDERUSDT)
- Win rate: 100% (1/1)
- ROI médio: +2.09%

**Top 5 Motivos de Bloqueio**:
1. `cvd_negative_quarantine`: 4.628 (29.8%) ✅ CORRETO
2. `lsr_trend_positive`: 4.019 (25.9%) ✅ CORRETO
3. `rsi_lt_min_rsi_5m`: 3.770 (24.3%) ⚠️ MUITO RESTRITIVO
4. `oi_change_lt_min`: 2.012 (13.0%) ⚠️ MUITO RESTRITIVO
5. `lsr_change_not_negative`: 304 (2.0%) ✅ CORRETO

**Problema Identificado no Trade RENDERUSDT**:
```
Entrada: 2.1760 USDT (00:31:11)
MFE: +4.57% (pico em 2.2754)
Saída: 2.1840 USDT (00:31:28) - 17 segundos
ROI: +2.09%
Captura do MFE: 45.7%

PROBLEMA: DNA PTP travou SL em +1% ANTES do delay de 60s
```

---

## 🔧 Ajustes Implementados

### **1. Filtros de Sinal (preferences.local.json)**

#### **Paper Mode**:
```json
"signal": {
    "min_exp": 0.025,              // ANTES: 0.04 (-37.5%)
    "min_oi_change_pct": 0.0075,   // ANTES: 0.25 (-97%)
    "min_rsi_5m": 58.0,            // ANTES: 65.0 (-10.8%)
    // Demais parâmetros mantidos
}
```

**Justificativa**:

| Parâmetro | Antes | Depois | Motivo |
|-----------|-------|--------|--------|
| `min_exp` | 0.04 (4%) | 0.025 (2.5%) | Elite Ghosts com score 100 tinham exp=0.032 |
| `min_oi_change_pct` | 0.25 (25%) | 0.0075 (0.75%) | OI raramente cresce 25% em 5min |
| `min_rsi_5m` | 65 | 58 | RSI 50 é neutro, 65 é sobrecomprado |

**Impacto Esperado**:
- Redução de bloqueios por `rsi_lt_min_rsi_5m`: -60%
- Redução de bloqueios por `oi_change_lt_min`: -80%
- Taxa de bloqueio total: 99.9% → 70-80%
- Sinais por dia: 1-2 → 5-10

---

### **2. DNA PTP Desabilitado (src/paper_tracker.py)**

**Código Comentado** (linhas 1078-1095):
```python
# AUDITORIA BRUTAL 2026-06-02: DNA PTP DESABILITADO TEMPORARIAMENTE
# Motivo: Interfere com trailing delay de 60s (fecha trades em 17s)
# TODO: Reabilitar após validar trailing stop puro
```

**Problema**:
- DNA PTP trava SL em +1% quando atinge 33% do TP
- Ignora o delay de 60s do trailing stop
- Fecha trades prematuramente (17s vs 60s esperado)

**Solução**:
- Desabilitar DNA PTP temporariamente
- Testar trailing stop puro por 24-48h
- Validar captura do MFE
- Reabilitar DNA PTP com lógica ajustada

**Trailing Stop Atual** (ATIVO):
```python
# Delay de 60s (linha 1011)
trailing_delay_passed = duration_sec >= 60

# Trailing baseado em 60% do MFE (linha 1027)
trailing_distance_pct = mfe_distance_pct * 0.6

# Stop mínimo em +1.5% (linha 1031)
min_trailing_sl = entry_price * 1.015
```

---

## 📈 Projeções de Impacto

### **Antes dos Ajustes**:
```
Sinais/dia: 1-2
Taxa de bloqueio: 99.9%
Captura do MFE: 45.7%
Duração média: 17s (prematura)
```

### **Depois dos Ajustes (Esperado)**:
```
Sinais/dia: 5-10 (+400%)
Taxa de bloqueio: 70-80% (-20%)
Captura do MFE: 60-70% (+50%)
Duração média: 90-120s (respeitando delay)
```

### **Métricas de Validação** (24-48h):
```
✅ Mínimo 20-30 trades coletados
✅ Avg Win > +3% (antes era +2%)
✅ Captura do MFE > 60% (antes era 45%)
✅ Duração média > 60s (antes era 17s)
✅ Win rate mantido > 60%
```

---

## 🔍 Elite Ghosts Desbloqueados

Com os novos filtros, os seguintes sinais de alta qualidade devem PASSAR:

### **1. WLDUSDT (Score 100)**
```
ANTES: Bloqueado por exp=0.0322 < 0.04
DEPOIS: PASSA (exp=0.0322 > 0.025) ✅
```

### **2. RENDERUSDT (Score 98)**
```
ANTES: Bloqueado por lsr_trend_too_weak
DEPOIS: Passou e gerou trade (+2.09%)
AGORA: Deve capturar +4-5% com trailing otimizado ✅
```

### **3. ZECUSDT (Score 95)**
```
ANTES: Bloqueado por lsr_trend_too_weak
DEPOIS: Pode passar com filtros relaxados ⚠️
```

### **4. RIFUSDT (Score 90)**
```
ANTES: Bloqueado por final_gate_fail
DEPOIS: Pode passar com OI relaxado ⚠️
```

---

## 🚨 Riscos e Mitigações

### **Risco 1: Aumento de False Positives**
```
Risco: Filtros mais relaxados podem gerar mais losers
Mitigação: 
- CVD Quarantine continua ativo (bloqueia 30%)
- LSR Trend Positive continua ativo (bloqueia 26%)
- Trailing stop otimizado protege capital
```

### **Risco 2: Overtrading**
```
Risco: 5-10 sinais/dia podem saturar capital
Mitigação:
- Max 20 posições simultâneas (Paper)
- Cooldown de 180s por símbolo
- Risk management de 5% por trade
```

### **Risco 3: Trailing Stop Muito Largo**
```
Risco: 60% do MFE pode deixar muito lucro na mesa
Mitigação:
- Testar por 24-48h
- Ajustar para 70% se necessário
- Profit Guard em +10% continua ativo
```

---

## 📋 Checklist de Validação

### **Fase 1: Primeiras 4 horas**
- [ ] Bot rodando sem crashes
- [ ] Sinais sendo gerados (>2 por hora)
- [ ] Trades respeitando delay de 60s
- [ ] MFE sendo capturado (>60%)

### **Fase 2: 24 horas**
- [ ] Mínimo 10-15 trades coletados
- [ ] Win rate > 60%
- [ ] Avg Win > +3%
- [ ] Duração média > 60s

### **Fase 3: 48 horas**
- [ ] Mínimo 20-30 trades coletados
- [ ] Comparar com baseline anterior
- [ ] Analisar ghost outcomes
- [ ] Decidir ajustes finais

---

## 🎯 Comandos de Teste

```bash
# 1. Iniciar bot com novos filtros
python main.py

# 2. Monitorar em tempo real
# Dashboard: http://localhost:8765

# 3. Após 4 horas, analisar ghost signals
python src/audit_ghost_outcomes.py

# 4. Após 24h, analisar trades fechados
python src/analyze_closed_trades.py

# 5. Após 48h, auditoria profunda
python src/audit_deep_dive.py
python src/audit_intelligence_advanced.py
```

---

## 📊 Comparação de Parâmetros

| Parâmetro | v4.2.1 | v4.2.2 | Variação |
|-----------|--------|--------|----------|
| `min_exp` | 0.04 | 0.025 | -37.5% |
| `min_oi_change_pct` | 0.25 | 0.0075 | -97.0% |
| `min_rsi_5m` | 65.0 | 58.0 | -10.8% |
| `trailing_delay` | 60s | 60s | 0% |
| `trailing_mfe_pct` | 60% | 60% | 0% |
| `min_trailing_sl` | 1.5% | 1.5% | 0% |
| **DNA PTP** | ✅ Ativo | ❌ Desabilitado | - |

---

## 🔄 Próximos Passos

### **Se Win Rate > 60% após 48h**:
1. ✅ Manter filtros atuais
2. ✅ Reabilitar DNA PTP com delay respeitado
3. ✅ Testar por mais 7 dias
4. ✅ Considerar transição para LIVE

### **Se Win Rate < 50% após 48h**:
1. ⚠️ Reverter `min_exp` para 0.03
2. ⚠️ Reverter `min_oi_change_pct` para 0.01
3. ⚠️ Manter `min_rsi_5m` em 58
4. ⚠️ Testar por mais 48h

### **Se Captura MFE < 50% após 48h**:
1. ⚠️ Aumentar trailing para 70% do MFE
2. ⚠️ Reduzir delay para 45s
3. ⚠️ Testar por mais 48h

---

## 📝 Notas Técnicas

### **Paridade Paper ↔ Live**:
```
✅ Trailing stop: Paridade garantida
✅ Filtros de sinal: Paper mais agressivo que Live
⚠️ DNA PTP: Desabilitado apenas no Paper
```

### **Arquivos Modificados**:
```
1. preferences.local.json (linhas 32-46)
   - min_exp: 0.04 → 0.025
   - min_oi_change_pct: 0.25 → 0.0075
   - min_rsi_5m: 65.0 → 58.0

2. src/paper_tracker.py (linhas 1078-1095)
   - DNA PTP comentado temporariamente
```

### **Logs de Monitoramento**:
```
- logs/signals.jsonl (sinais aceitos)
- logs/signal_refusals.jsonl (sinais bloqueados)
- logs/paper_closed.jsonl (trades fechados)
- logs/paper_opportunities.json (trades abertos)
```

---

## ✅ Resumo Executivo

**Mudanças Implementadas**:
1. ✅ Filtros relaxados (-37% a -97%)
2. ✅ DNA PTP desabilitado temporariamente
3. ✅ Trailing stop mantido (60s, 60% MFE)

**Impacto Esperado**:
- Sinais/dia: 1-2 → 5-10 (+400%)
- Taxa de bloqueio: 99.9% → 70-80% (-20%)
- Captura do MFE: 45% → 60-70% (+50%)
- Duração média: 17s → 90-120s (+500%)

**Próxima Ação**:
- Rodar bot por 24-48h
- Coletar mínimo 20-30 trades
- Analisar métricas de performance
- Decidir ajustes finais

---

**VERSÃO**: 4.2.2  
**STATUS**: ✅ Implementado  
**TESTE**: 🔄 Aguardando validação (24-48h)