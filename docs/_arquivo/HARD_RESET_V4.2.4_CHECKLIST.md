# Hard Reset v4.2.4 - Checklist de Validação Limpa

**Data:** 2026-06-02  
**Versão:** v4.2.4  
**Objetivo:** Iniciar validação de 24-48h com amostra limpa após correções P0

---

## ✅ Pré-Requisitos (COMPLETO)

### 1. Backup Realizado
- [x] Backup criado em: `backups/v4.2.4_pre-validation_2026-06-02_07-24-57`
- [x] Logs preservados para análise posterior

### 2. Correções P0 Implementadas
- [x] Blacklist PARTIUSDT (preferences.json + preferences.local.json)
- [x] Score mínimo = 90 (preferences.json + preferences.local.json)
- [x] Stop loss = 3% (preferences.json + preferences.local.json)
- [x] Timeout = 30 minutos (preferences.json + preferences.local.json)
- [x] Bug fix em signal_engine.py (linha 772)
- [x] Bug fix em config.py (linha 187)

### 3. Logs Limpos
- [x] Arquivos .jsonl removidos
- [x] Arquivos .log removidos
- [x] paper_opportunities.json removido
- [x] Estados preservados (metric_state.json, risk_state.json, throttle_state.json)

---

## 🔄 Procedimento de Hard Reset

### Passo 1: Parar Processos Ativos
```powershell
# Identificar processos Python
Get-Process python | Select-Object Id, ProcessName, StartTime

# Parar processos (IDs: 7084, 12524)
Stop-Process -Id 7084 -Force
Stop-Process -Id 12524 -Force

# Confirmar que pararam
Get-Process python -ErrorAction SilentlyContinue
```

### Passo 2: Limpar Lock Files
```powershell
Remove-Item -Path "logs/instance_lock_*.pid" -Force -ErrorAction SilentlyContinue
```

### Passo 3: Resetar Estados (Opcional - Apenas se necessário)
```powershell
# CUIDADO: Isso reseta métricas e throttling
# Remove-Item -Path "logs/metric_state.json" -Force -ErrorAction SilentlyContinue
# Remove-Item -Path "logs/risk_state.json" -Force -ErrorAction SilentlyContinue
# Remove-Item -Path "logs/throttle_state.json" -Force -ErrorAction SilentlyContinue
```

### Passo 4: Iniciar Bot
```powershell
python main.py
```

---

## 📊 Monitoramento Pós-Reinício

### Primeiras 4 Horas

**Verificações Imediatas (15 minutos):**
```powershell
# Verificar se bot iniciou corretamente
Get-Content logs/runtime_main_debug.jsonl -Tail 20

# Verificar se PARTI está bloqueado
Get-Content logs/signal_refusals.jsonl | Select-String "PARTI"

# Verificar filtro de score
Get-Content logs/signal_refusals.jsonl | Select-String "score_below_min"
```

**Análise Rápida (1 hora):**
```powershell
python src/analyze_session_quick.py
```

**Métricas Esperadas (4 horas):**
- [ ] Nenhum trade com PARTIUSDT
- [ ] Todos os sinais com score ≥ 90
- [ ] Nenhum trade > 30 minutos
- [ ] Nenhum loss > -3%
- [ ] Taxa de sinais reduzida (esperado: ~50% menos sinais)
- [ ] Win rate mantido ou melhorado

### Validação 24 Horas

**Análise Profunda:**
```powershell
python src/audit_deep_dive.py
python src/audit_intelligence_advanced.py
```

**Métricas de Sucesso:**
- [ ] Win rate ≥ 65%
- [ ] P&L positivo
- [ ] Captura MFE ≥ 60%
- [ ] Drawdown máximo < 5%
- [ ] Nenhum trade catastrófico (loss > -10%)

### Validação 48 Horas

**Decisão LIVE:**
- [ ] Todas as métricas de 24h confirmadas
- [ ] Comportamento estável e previsível
- [ ] Sem bugs ou crashes
- [ ] Dashboard responsivo
- [ ] Telegram funcionando

---

## 🚨 Troubleshooting

### Bot não inicia
```powershell
# Verificar logs de erro
Get-Content logs/error.log -Tail 50

# Verificar se porta está em uso
netstat -ano | findstr "8050"
```

### Sinais não aparecem
```powershell
# Verificar refusals
Get-Content logs/signal_refusals.jsonl -Tail 50

# Verificar se DataEngine está coletando dados
Get-Content logs/pipeline_debug.jsonl -Tail 20
```

### Dashboard não carrega
```powershell
# Verificar logs do dashboard
Get-Content logs/dashboard_diagnostics.log -Tail 50

# Reiniciar apenas o dashboard (se necessário)
# Ctrl+C no terminal e python main.py novamente
```

---

## 📝 Notas Importantes

1. **Não modificar preferences.json durante validação** - Aguardar 24-48h
2. **Monitorar Telegram** - Alertas críticos serão enviados
3. **Documentar anomalias** - Qualquer comportamento inesperado
4. **Backup automático** - Sistema cria snapshots a cada hora em `logs/history/`

---

## ✅ Checklist Final Pré-LIVE

Após 48h de validação bem-sucedida:

- [ ] Todas as métricas de sucesso atingidas
- [ ] Nenhum bug crítico identificado
- [ ] Sistema estável por 48h contínuas
- [ ] Documentação atualizada
- [ ] Backup completo realizado
- [ ] Configurações LIVE revisadas
- [ ] Capital mínimo definido para teste LIVE
- [ ] Plano de contingência documentado

**Próximo Passo:** Transição gradual para modo LIVE com capital reduzido (10-20% do total)

---

**Responsável:** Engenheiro Bob  
**Status:** ✅ Pronto para Hard Reset  
**Última Atualização:** 2026-06-02 07:25 BRT