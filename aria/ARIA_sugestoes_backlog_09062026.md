# ARIA — Sugestões ao Backlog Estratégico
**Para:** Brain + Doreto
**De:** ARIA — Analista de Dados Eassets
**Data:** 09/06/2026
**Status:** Novos itens + atualizações para revisão do Brain

---

## NOVOS ITENS

---

**B-46 — EA-02: ema_trend:4h no MetricStore via klines reais**
Status: Sprint 4 · pré-requisito crítico de múltiplos itens
Origem: ARIA · evidência acumulada de 3 sessões · 09/06/2026

O `ema_trend:4h` é mencionado como pré-requisito em B-36, B-38 e B-40 mas não tem item próprio no backlog. É a peça que desbloqueia a maior parte do Sprint 4.

Dependências diretas:
- B-36 (EA-07 com klines reais) — o campo correto para exp_btc_norm_1h depende do contexto de 1h real, que por sua vez depende do 4h estar calibrado
- B-38 (MTF como modificador de gates) — impossível sem ema_trend:4h populado
- B-40 (gate ema_4h_bearish) — implementado com buffer de polling, deve migrar para klines reais quando EA-02 estiver pronto

Evidência que sustenta prioridade Sprint 4:
3 sessões consecutivas com EMA:4h discriminando winners de losers. Winners EMA:4h médio = -2.0, Losers EMA:4h médio = -5.0. BANANAS31 (+17%) com EMA:4h=0. BBUSDT (-15.92%) com EMA:4h=-6. WAXPUSDT (-16.93%) com EMA:4h=-6 em todos os TFs.

Implementação sugerida:
- Forge adiciona klines 4h no boot (já existe padrão com klines 1h e 5m)
- `metric_engine.py` calcula `ema_trend:4h` no mesmo padrão do 1h e 5m
- WebSocket `kline_4h` já implementado (B-40) — só falta o cálculo no MetricStore

Próximo passo: quando Sprint 4 iniciar, este é o primeiro item. Brain verifica se klines 4h já estão parcialmente no SymbolStore antes de especificar para o Forge.

---

**B-47 — Seleção dos 100 ativos prioritários — critérios e gap vs Eassets**
Status: Hipótese · Sprint 4 · análise antes de implementação
Origem: ARIA · observação de ALLOUSDT/ROBOUSDT nos ghosts · 09/06/2026

O SS seleciona ~100 ativos prioritários para monitoramento intensivo. O Eassets cobre 530+. A sobreposição não é 100% — e o critério de seleção dos 100 pode estar excluindo sistematicamente ativos com momentum forte que o Eassets identifica mas o SS nunca monitora.

Evidência que levanta a hipótese:
- ALLOUSDT: bloqueado 1.009 vezes em refusals — estava nos 100 ativos monitorados? Se não estava, nunca poderia ter entrado independente das condições.
- ROBOUSDT: EMA 6/6/6, OI forte, EXP_BTC:1h=+7.6 — 20 near-misses. Estava no universo?
- MOVEUSDT: EXP_BTC:1h=+40.0, 154 ghost signals — estava sendo monitorado?

O problema estrutural:
Se o critério de seleção dos 100 favorece ativos com histórico de atividade no SS (volume, OI histórico, trades passados), pode criar um viés de seleção que exclui ativos novos ou em fase de acumulação — exatamente os que o Eassets identifica como melhores candidatos antes da explosão.

Como validar:
1. Forge expõe a lista atual dos 100 ativos prioritários (ou o critério de seleção)
2. ARIA cruza com o JSON completo do Eassets (530+ ativos) — identifica os ativos de alto score DNA que NÃO estão nos 100
3. Se houver gap significativo (ativos com DNA score >= 70 fora dos 100), revisar critério

Próximo passo: Brain pede ao Forge a lista atual dos 100 prioritários e o critério de seleção. ARIA faz o cruzamento com o próximo JSON do Eassets e reporta o gap.

---

## ATUALIZAÇÕES DE ITENS EXISTENTES

---

**B-21 — CVD alto como possível sinal de exaustão**
Status anterior: Hipótese com evidência parcial · aguarda 30+ trades
**Status atualizado: CONFIRMADO via B-37 · encerrar loop · 09/06/2026**

Com 42+ trades acumulados, o padrão se confirmou de forma consistente:
- Winners média volume_quality = 0.535
- Losers média volume_quality = 1.502 (3x maior)
- Caso extremo: STGUSDT vq=16.20 (CVD explosivo sem sustentação) — loser

A implementação desta hipótese é o gate B-37/F-15 (volume_quality < 2.0) — já implementado em Sprint 3. B-21 está resolvido via B-37. Não criar gate adicional de CVD — o volume_quality já captura este comportamento de forma mais precisa (normaliza CVD pelo número de trades, distinguindo spike de pressão sustentada).

Ação sugerida: marcar B-21 como "Confirmado e resolvido via B-37. Não implementar gate adicional de CVD bruto."

---

**B-34 — LSR bypass quando OI forte + liquidações confirmadas**
Status anterior: Hipótese · aguarda evidência nos refusals
**Status atualizado: Aguarda primeiros trades com liq_short_1m real · F-12 resolvido 09/06/2026**

Com F-12 resolvido (causa raiz: WebSocket no endpoint errado), o campo `liq_short_1m` vai chegar com valores reais pela primeira vez. B-34 depende de `liq_short_1m > 0` para ser testado — sem esse campo funcionando, era impossível validar a hipótese.

Próximo passo atualizado: nas próximas sessões com liq_short_1m real, Brain filtra os refusals de `lsr_trend_positive` onde `oi_change_pct > 25%` E `liq_short_1m > 0`. ARIA cruza com o Eassets para ver se esses ativos bloqueados tinham estado macro favorável. Se padrão confirmar, vira task com evidência real.

---

**B-20 — Queda de atividade do Sniper ao longo do tempo**
Status anterior: Hipótese observacional · aguarda dados com timestamp
**Status atualizado: Em observação ativa · RSI 45 implementado · 09/06/2026**

A sessão de 09/06 deu evidência para a Hipótese B (bloqueio silencioso):
- 2760 refusals em ~4 horas
- 84% concentrado em 5 motivos
- `rsi_lt_min_rsi_5m` com threshold 60 gerou 510 bloqueios (18.5%) — ativos em zona de acumulação RSI 45-60 sendo recusados sistematicamente
- `cvd_negative_quarantine` 727 bloqueios — parte pode ser ruído de 5m sem contexto de 1h

Com `min_rsi_5m` ajustado para 45 (commit desta sessão), a próxima sessão longa deve mostrar redução significativa no `rsi_lt_min_rsi_5m`.

Próximo passo atualizado: na próxima sessão com 4+ horas de dados, comparar distribuição de refusals pré (threshold 60) vs pós (threshold 45). Se `rsi_lt_min_rsi_5m` cair de 18.5% para < 8%, o ajuste foi efetivo. ARIA traz o comparativo na próxima análise.

---

*ARIA — 09/06/2026*
*Sugestões baseadas em evidência das sessões de análise. Brain valida antes de incorporar ao backlog oficial.*
