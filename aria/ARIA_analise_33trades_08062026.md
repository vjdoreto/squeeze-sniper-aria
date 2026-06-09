# ARIA — Análise Cruzada SS × Eassets · Sprint 3
**Para:** Brain + Doreto (alinhamento pré-Forge)
**De:** ARIA — Analista de Dados Eassets
**Data:** 08/06/2026 · 33 trades · 30.828 ghost signals · Eassets 10:42 UTC
**Status:** Tese com evidência — base para consenso antes do Forge

---

## Situação atual — números sem filtro

| Métrica | Valor | Meta LIVE |
|---|---|---|
| Win Rate | 33.3% (11W/22L) | ≥ 60% |
| Profit Factor | **0.488** | ≥ 1.5 |
| Avg Winner | +5.62% | — |
| Avg Loser | -5.76% | — |
| Max Drawdown estimado | alto | ≤ 12% |

**PF 0.488 significa: para cada $1 ganho, perdemos $2.06.** O sistema está destruindo capital. Não há dúvida sobre isso. A questão é o porquê — e os dados respondem.

---

## Descoberta Crítica 1 — max_hold está vivo e destruindo capital

**Este é o problema mais urgente da análise.**

O `max_hold` deveria ter sido eliminado no Sprint 1. Ele ainda está ativo e causando os piores trades da amostra:

| Ativo | PnL | MFE | O que aconteceu |
|---|---|---|---|
| IDUSDT | **-13.92%** | 2.31% | Entrou, subiu pouco, segurou até o máximo |
| PROVEUSDT | **-9.67%** | 2.53% | Idem |
| OGUSDT | -5.66% | 2.19% | Idem |
| EIGENUSDT | -6.58% | 1.31% | Idem |

Todos têm MFE positivo mas baixo — o trailing não se ativou, o mae_guard não disparou a tempo, e o `max_hold` segurou até a perda máxima. Sem esses 4 trades, o PF da amostra sobe significativamente.

**Pergunta direta ao Brain:** o `max_hold` está em `preferences.json` com qual valor? O `paper_tracker.py` tem o gate `mae_guard` + `squeeze_aborted` implementados do Sprint 1 — por que não dispararam antes do `max_hold`?

---

## Descoberta Crítica 2 — exp_btc_norm_1h revelou o oposto do esperado

**Este é o achado mais contra-intuitivo e mais importante da análise.**

| Grupo | norm_1h médio |
|---|---|
| Winners | **1.071** |
| Losers | **1.564** |

**Losers têm norm_1h MAIS ALTO que winners.** Isso contradiz diretamente a hipótese EA-06/EA-07 de que norm alto = força real = melhor trade.

### O que está acontecendo:

Os losers com norm alto são casos onde o ativo teve força relativa momentânea vs BTC (causando norm alto) mas sem sustentação — o squeeze nunca veio. Exemplos:
- MANTAUSDT: norm=2.572, squeeze_failed, MFE=0
- NILUSDT 2ª entrada: norm=2.368, squeeze_failed, MFE=0
- ARUSDT: norm=2.522, squeeze_failed, MFE=0

Os winners com norm negativo são os mais reveladores:
- **EDENUSDT: norm=-2.176, pnl=+9.14%** — ativo mais fraco vs BTC no 1h que virou winner
- **NILUSDT: norm=-1.771, pnl=+7.10%** — idem

**Conclusão: o `exp_btc_norm_1h` com buffer de 140s não mede força estrutural — mede momentum de curtíssimo prazo.** A correlação está invertida porque momentum pontual alto frequentemente precede correção.

**Recomendação ao Brain:** o gate EA-07 baseado em `exp_btc_norm_1h < -5` não deve ser ativado com a implementação atual. O campo precisa ser recalculado com klines reais de 1h antes de qualquer gate. A implementação atual com buffer de 140s tem comportamento diferente do previsto.

---

## Descoberta Crítica 3 — volume_quality discrimina winners de losers

**Esta é a descoberta mais acionável desta rodada.**

| Grupo | volume_quality médio |
|---|---|
| Winners | **0.535** |
| Losers | **1.502** |

**Losers têm volume_quality 3x maior que winners.** Volume quality alto = CVD alto relativo ao trades_1m = spike de CVD pontual sem sustentação de trades.

O caso extremo confirma: STGUSDT com vq=16.20 (maior da amostra) foi loss. CVD explodiu mas os trades não sustentaram — era um spike institucional de rebalanceamento, não acumulação real.

Os melhores winners têm vq moderado:
- BANKUSDT: vq=0.356, pnl=+22.05%
- EDENUSDT: vq=0.910, pnl=+9.14%
- PROVEUSDT winner: vq=0.158, pnl=+2.96%, MFE=19.52%

**Tese:** `volume_quality` ótimo está na faixa 0.05 a 1.5. Acima de 2.0 é spike — não squeeze.

**Sugestão EA-09 para o Brain:** gate em `volume_quality < 2.0` como filtro adicional. Teria bloqueado STGUSDT (vq=16.20) e possivelmente NILUSDT 2ª (vq=4.67) sem bloquear nenhum winner.

---

## Descoberta 4 — Ghost signals revelam o ouro que o SS nunca tocou

**30.828 ghost signals. O que estava lá:**

### ALLOUSDT — 1.009 near-misses, nunca entrou
Estado atual no Eassets: `expbtc1h=+108, ema=6/6, oi=47.76, rsi5=59.3`

O ALLOUSDT foi o ativo mais forte do painel durante o fim de semana inteiro. 1.009 vezes chegou perto de passar os gates — mas `cvd_negative_quarantine` e `lsr_trend_positive` bloquearam consistentemente.

O Eassets via: OI 47.76, EXP_BTC:1h +108, EMA 6/6. O SS via: CVD negativo e LSR subindo em janelas de 5m. São leituras de timeframes diferentes do mesmo ativo em momentos diferentes. O SS estava certo em cada bloqueio individual — mas perdeu o movimento macro.

**Esta é a limitação estrutural mais importante:** o SS toma decisões em janelas de 5m. O Eassets vê o contexto de 1h/4h. Um ativo pode ter CVD negativo em 80% das janelas de 5m mas ainda subir 50% no dia — porque o movimento macro de 1h é positivo.

### JTOUSDT — 483 near-misses, nunca entrou
Eassets agora: `expbtc1h=+19.9, ema=6/6, oi=3.59, rsi5=71.5`

### ZBTUSDT — 435 near-misses, nunca entrou
Eassets agora: `expbtc1h=+21.7, ema=6/0, oi=17.03, rsi5=76.1`

---

## Descoberta 5 — Cruzamento Eassets × Trades: padrão EMA:4h confirmado

Cruzando os ativos negociados com o estado atual no Eassets:

**Losers com EMA:4h=-6 (tendência macro bearish no swing):**
- VICUSDT: ema4h=-6 → LOSS -11.29%
- MANTAUSDT: ema4h=0 → LOSS -8.49%
- ARUSDT: ema4h=-6 → LOSS -2.30%
- NFPUSDT: ema4h=-6 → LOSS
- SPKUSDT: ema4h=-6 → LOSS
- PYTHUSDT: ema4h=-6 → LOSS
- GPSUSDT: ema4h=-4 → LOSS

**Winners com EMA:4h positivo:**
- BANKUSDT: ema4h=+4 → **WIN +22.05%**
- OPENUSDT: ema4h=+4 → **WIN +5.60%**

**O padrão sustenta EA-02:** `ema_trend:4h` no MetricStore discrimina bem. Os dois melhores winners têm EMA:4h positivo. A maioria dos losers tem EMA:4h negativo ou neutro.

---

## A tese central da ARIA — o gap estrutural do SS

O SS opera em janelas de 5m tomando decisões binárias (entrar ou não). O Eassets opera com contexto multi-TF contínuo. O gap não é de código — é de **arquitetura de decisão**.

**O que o SS não vê hoje:**
1. Momentum de 1h+ que sustenta um movimento além de 5m
2. Força relativa estrutural vs BTC (não pontual de 140s)
3. Qualidade do volume distinguindo spike de acumulação real

**O que o Eassets viu no fim de semana:**
- ALLOUSDT subindo com EXP_BTC:1h +108 enquanto o SS bloqueava 1.009 vezes por CVD negativo em janelas de 5m

**A fusão que proponho ao Brain:**

Não é implementar o Eassets no SS. É usar o contexto do Eassets como **filtro de ambiente** antes da decisão de 5m. Se o Eassets diz que o ativo tem EXP_BTC:1h > +30 e EMA:4h = +6, o SS deveria ter um limiar diferente para os gates de CVD e LSR — porque o contexto macro indica que pequenas negatividades de 5m são ruído, não sinal de reversão.

Isso é o **Multi Time Frame (MTF)** que o briefing menciona. E os dados desta análise sustentam essa direção.

---

## Sugestões consolidadas para o consenso

| Código | Sugestão | Evidência | Urgência |
|---|---|---|---|
| **URGENTE** | Verificar se max_hold ainda está ativo | 4 trades com max_hold = piores da amostra | Hoje |
| **EA-09** | Gate `volume_quality < 2.0` | W avg=0.535, L avg=1.502, STGUSDT vq=16.20 | Sprint 3 |
| **EA-07 REVISADO** | Suspender gate exp_btc_norm_1h até implementar klines 1h reais | norm_1h invertido: losers têm norm maior | Sprint 4 |
| **EA-02** | ema_trend:4h no MetricStore como filtro | BANKUSDT/OPENUSDT únicos winners com ema4h positivo | Sprint 4 |
| **MTF** | Contexto 1h como modificador de gate de 5m | Gap ALLOUSDT 1.009 near-misses | Sprint 5 |

---

## O que a ARIA precisa para a próxima análise

Para validar EA-09 e o max_hold:
- `paper_debug.jsonl` — eventos de mae_guard e sizing para entender por que max_hold disparou antes dos outros gates
- `preferences.json` atual — confirmar se max_hold está configurado e com qual timeout
- Próximos 15+ trades com `volume_quality` logado — para confirmar threshold de 2.0

---

*ARIA — Analista de Dados Eassets · 08/06/2026*
*Base para alinhamento Doreto × ARIA × Brain antes do Forge*
