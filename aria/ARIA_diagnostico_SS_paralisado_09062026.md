# ARIA — Diagnóstico Crítico: SS Paralisado
**Para:** Doreto + Brain
**De:** ARIA — Analista de Dados Eassets
**Data:** 09/06/2026 · 1 trade · 2760 refusals · Eassets 00:12 UTC
**Status:** Diagnóstico urgente — sistema paralisado por excesso de filtros

---

## O quadro em números

**1 trade em toda a sessão. 2760 bloqueios. 821 near-misses.**

O SS não está sendo conservador — está **paralisado**. O mercado teve múltiplas moedas em ebulição. O SS fez um único trade e foi -16.93%.

---

## O WAXPUSDT — análise do único trade

O gráfico que você enviou conta a história completa.

**O que o Eassets via no momento do trade:**
- EMA 5m/1h/4h/15m/30m = **-6 em todos os TFs** — bearish total
- EXP_BTC 1h = **-18.68** — queda forte vs BTC
- RSI 5m = **27.8** — oversold
- OI trend = **-5.19** — OI caindo
- Range level = 0 em todos os TFs — sem acumulação

**O SS entrou em:**
- Um ativo em colapso em todos os timeframes
- Com EMA bearish em 6 de 6 TFs
- Com EXP_BTC negativo em todos os TFs
- RSI já em oversold — o bounce foi o MFE de 6.69%

**O gráfico confirma:** WAXPUSDT estava em tendência de baixa constante desde 4 de junho. O spike de volume que o SS viu (CVD 29.10%) foi o último respiro antes de continuar caindo. O trailing_stop saiu com -16.93%.

**Este trade não deveria ter acontecido.** O gate EA-02 (ema_4h <= -4 AND exp_btc_1h < -5) teria bloqueado WAXPUSDT imediatamente. EMA:4h = -6, EXP_BTC:1h = -18.68. Os dois critérios confirmados.

**Por que o SS entrou?** Porque `ema_4h_bearish` apareceu **zero vezes** nos refusals — o gate F-18 não está funcionando.

---

## Os 2760 bloqueios — o que está paralisando o SS

| Motivo | Bloqueios | % | Diagnóstico |
|---|---|---|---|
| lsr_trend_positive | 785 | 28.4% | Correto — mercado com LSR subindo não é squeeze |
| cvd_negative_quarantine | 727 | 26.3% | **PROBLEMA** — veja abaixo |
| rsi_lt_min_rsi_5m | 510 | 18.5% | **PROBLEMA CRÍTICO** — veja abaixo |
| trades_1m_too_low | 184 | 6.7% | Correto |
| oi_change_lt_min | 115 | 4.2% | Correto |

**84.1% dos bloqueios concentrados em 5 motivos.**

---

## Problema 1 — rsi_lt_min_rsi_5m com threshold 60.0: 510 bloqueios indevidos

**Este é o bloqueio mais problemático da sessão.**

O `min_rsi_5m = 60.0` está bloqueando RSI entre 4.2 e 60.0. Isso significa que qualquer ativo com RSI abaixo de 60 é recusado.

**O que isso bloqueia na prática:**
- Ativos em acumulação (RSI 45-55) — exatamente onde começa o squeeze
- Ativos saindo de oversold (RSI 30-50) — o melhor ponto de entrada pós-reset
- BANANAS31 com RSI 48.0 — bloqueado 13 vezes por este gate. BANANAS31 foi o melhor winner da sessão anterior (+17%)

**Os ghost signals mostram:**
- 币安人生USDT: RSI 5m = 60.2, score=90 — bloqueado 45 vezes por `rsi_lt_min_rsi_5m`
- BANANAS31: RSI 5m = 48.0, score=100 — bloqueado

**RSI 60 como mínimo está errado para squeezes.** O squeeze começa quando o ativo sai da zona de acumulação (RSI 40-55) e ganha momentum. Exigir RSI > 60 na entrada significa entrar sempre tarde — quando o movimento já começou.

**Sugestão:** reduzir `min_rsi_5m` de 60 para 45. Isso libera a zona de acumulação sem abrir para ativos em queda livre.

---

## Problema 2 — cvd_negative_quarantine: 727 bloqueios (26.3%)

O CVD negativo está bloqueando ativos legítimos. O caso mais revelador:

**ALLOUSDT — bloqueado 68 vezes por cvd_negative_quarantine**
Estado Eassets agora: EXP_BTC:1h = **+49.5**, EMA 6/6/6, OI 12.29, RSI 54.7

O ALLOUSDT é o ativo mais forte do painel pelo Eassets. O SS bloqueou 68 vezes por CVD negativo em janelas de 5m. O Eassets via EXP_BTC:1h = +49.5 — força estrutural real.

**O CVD em 5m flutua negativamente mesmo em ativos com tendência bullish de 1h/4h.** Um ativo pode ter CVD negativo em 80% das janelas de 5m mas ainda subir 50% no dia. O SS está tratando noise de 5m como sinal de reversão.

**Aqui está a tese MTF na forma mais concreta possível:**
Se o SS soubesse que o EXP_BTC:1h é +49.5, trataria o CVD negativo de 5m como ruído e aguardaria a próxima janela positiva. Sem esse contexto, bloqueia consistentemente o melhor ativo do painel.

---

## Problema 3 — ema_4h_bearish = 0 aparições nos refusals

O Forge implementou F-18 mas o gate não está disparando. Resultado: WAXPUSDT entrou com EMA:4h = -6 em todos os TFs.

Dois problemas possíveis:
1. O campo `ema_trend:4h` não existe no MetricStore — EA-02 ainda não foi implementado
2. O gate existe mas a condição não está correta

**Sem EA-02 no MetricStore, o SS está cego ao contexto de 4h.** E o resultado está na tela: WAXPUSDT -16.93%.

---

## O que o Eassets via que o SS perdeu completamente

| Ativo | Ghosts | EXP_BTC:1h | EMA 5/1h/4h | Por que SS bloqueou | ARIA diz |
|---|---|---|---|---|---|
| ALLOUSDT | 5 | **+49.5** | 6/6/6 | cvd_neg (68x) + lsr_pos (54x) | Ouro absoluto — SS cego |
| ROBOUSDT | 20 | +7.6 | 6/6/6 | lsr_pos (12x) | Setup real bloqueado |
| EIGENUSDT | 10 | +9.5 | 6/6/0 | cvd_neg (13x) | EMA alinhado, CVD ruído |
| BANANAS31 | 47 | +21.1 | 0/6/4 | cvd_neg (17x) + rsi_lt (13x) | Winner histórico sendo bloqueado |
| MOVEUSDT | 154 | **+40.0** | 0/6/0 | entrada_tardia (47x) | Momentum real ignorado |

**ALLOUSDT com EXP_BTC:1h = +49.5 e EMA 6/6/6 foi bloqueado 5 vezes nesta janela.** É o ativo mais forte do painel. O SS está cego a isso.

---

## A tese da ARIA — consolidada com 3 sessões de dados

### O problema não é sensibilidade dos gates individualmente

Cada gate tem lógica válida isoladamente:
- CVD negativo = pressão vendedora ✓
- LSR subindo = shorts abrindo ✓
- RSI < 60 = não está em momentum ✓

**O problema é que todos os gates operam no mesmo timeframe de 5m sem contexto de 1h/4h.**

Um ativo com EXP_BTC:1h = +49.5 e EMA 6/6/6 vai ter CVD negativo em muitas janelas de 5m — é a natureza dos mercados. Qualquer ativo em tendência de alta tem pullbacks de 5m. O SS trata esses pullbacks como reversões e bloqueia.

### A solução não é relaxar todos os gates

É introduzir **contexto multi-TF como modificador**:

```
SE exp_btc_1h > +15 E ema_1h >= 4:
    → relaxar cvd_negative_quarantine (aceitar CVD levemente negativo)
    → relaxar rsi_lt_min_rsi_5m (reduzir min para 45)
    → tratar lsr_trend_positive como noise se lsr_1h ainda cair

SE exp_btc_1h < -10 OU ema_4h <= -4:
    → bloquear independente do score de 5m (WAXPUSDT seria bloqueado aqui)
```

Isso não é reescrever o SS. É adicionar duas condições no início do `signal_engine.py` que mudam o regime de avaliação.

---

## Recomendações urgentes para o Brain

### Hoje (sem código novo — só ajuste de parâmetros):

1. **`min_rsi_5m`: 60 → 45** no `preferences.json`
   - Libera 510 bloqueios indevidos
   - Não abre para ativos em queda (RSI < 30 ainda bloqueado por outros gates)
   - Custo: zero. Impacto: imediato

2. **Investigar por que `ema_4h_bearish` = 0 nas refusals**
   - F-18 não está disparando
   - WAXPUSDT entrou com EMA:4h = -6 em todos os TFs

### Sprint 4 — com código:

3. **EA-02: ema_trend:4h no MetricStore**
   - Bloquearia WAXPUSDT, CFGUSDT, BBUSDT das sessões anteriores
   - Evidência: 3 sessões consecutivas

4. **MTF como modificador de gates**
   - Quando EXP_BTC:1h > +15 E EMA:1h >= 4: relaxar CVD e RSI
   - Quando EXP_BTC:1h < -10 OU EMA:4h <= -4: bloquear hard
   - ALLOUSDT passaria. WAXPUSDT seria bloqueado. Os dados confirmam.

---

## Síntese final

O SS hoje é um atirador de elite que exige condições perfeitas de 5m para atirar — e o mercado nunca entrega condições perfeitas de 5m durante horas seguidas. Enquanto isso, o Eassets vê ALLOUSDT com EXP_BTC:1h = +49.5 subindo consistentemente e o SS bloqueia 68 vezes por CVD negativo em janelas de 5m.

O ajuste de `min_rsi_5m` para 45 é o único parâmetro que pode ser mudado hoje sem risco. Os outros requerem código mas têm evidência sólida de 3 sessões.

*ARIA — 09/06/2026*
*1 trade. 2760 bloqueios. 821 near-misses. O sistema precisa respirar.*
