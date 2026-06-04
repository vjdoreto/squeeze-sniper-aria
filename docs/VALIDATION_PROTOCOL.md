# Protocolo de Validação Quantitativa (PVQ) — SqueezeSniper V4

Este protocolo define os passos lógicos para a calibração do bot, garantindo que ajustes nos filtros sejam baseados exclusivamente em evidências estatísticas, eliminando o viés emocional.

## 1. Ciclo de Vida da Calibração (O Loop de Dados)
1. **Coleta Pura (Paper):** Operar em modo conservador por um período mínimo (ex: 48h ou 20 trades).
2. **Auditoria de Qualidade:** Executar `python audit_quality.py` para analisar a eficiência dos sinais.
3. **Análise de "Ghost Signals":** Verificar em `logs/signal_refusals.jsonl` o que foi barrado e por quê.
4. **Auditoria de Desfecho:** Executar `python audit_ghost_outcomes.py` para conferir se as moedas barradas subiram ou caíram.
5. **Validação de Lógica:** Rodar `python analyze_logic_validation.py` para checar se o DNA (OI/LSR/EXP) precedeu o movimento.
6. **Hipótese de Ajuste:** Formular mudança baseada na eficiência dos bloqueios.
6. **Calibração:** Aplicar no `preferences.json` e reiniciar o ciclo.

## 2. Indicadores Chave de Performance (KPIs) para Ajuste

| Métrica | Alvo | Ação se abaixo do alvo |
|---------|------|------------------------|
| **Win Rate** | > 55% | Aumentar restrição de LSR ou Fit Score |
| **MFE Médio** | > 1.5% | O sinal é bom, mas o TP ou Trailing está mal ajustado |
| **MAE Médio** | < 1.0% | Se alto, a entrada está sendo "atropelada" (entrada tardia) |
| **Eficiência de Captura** | > 30% | Se o bot ignora 90% dos sinais fortes, relaxar P1 (OI/CVD) |

## 3. O Filtro de "Ouro" (A Divergência Institucional)
Antes de relaxar qualquer filtro, os dados devem confirmar:
- O preço subiu (`EXP > 0`) **ENQUANTO** o `LSR` caía?
- O `OI` subiu durante a ignição?
- Se a resposta for NÃO para um trade perdedor, o filtro deve ser **mais restritivo**, não menos.

## 4. Auditoria de "Dinheiro Fake" (Alucinações)
Sempre que um trade apresentar PnL > 50% em ativos estáveis ou valores absurdos:
1. Verificar `logs/paper_debug.jsonl` em busca de saltos de preço (Tick Guard).
2. Rodar o script `purge_contaminated_trade.py` para limpar a amostra.
3. **Nunca** considerar outliers positivos absurdos na média de performance para fins de calibração.

## 5. Scripts de Apoio Obrigatórios

### A. Auditoria de Refusals (O que perdemos?)
```powershell
python audit_quality.py
```
*Olhar especificamente a seção "Top refusal reasons". Se 'entrada_tardia' for o maior motivo, estamos chegando depois da festa.*

### B. Validação de Rastro (A matemática estava certa?)
```powershell
python analyze_logic_validation.py
```
*Valida se o rastro institucional (CVD/OI) realmente precedeu a subida de preço.*

### C. Auditoria Profunda (Tiers de Score)
```powershell
python deep_performance_audit.py
```
*Diz exatamente qual faixa de Score (ex: 70-85 ou 85-100) é a mais lucrativa hoje.*

---
### D. Auditoria de Desfecho (O Filtro foi correto?)
```powershell
python audit_ghost_outcomes.py
```
*Verifica se o bot bloqueou um perdedor (Correto) ou ignorou um vencedor (Falso Negativo).*

**Regra de Ouro:** Só alteramos um parâmetro se o `audit_ghost_outcomes.py` mostrar que o motivo de recusa está barrando mais de 50% de sinais que seriam vencedores.

*Documento de Governança V1.0*