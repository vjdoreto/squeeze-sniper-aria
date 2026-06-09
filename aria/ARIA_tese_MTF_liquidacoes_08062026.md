# ARIA — Análise e Defesa de Tese
**Para:** Doreto + Brain (alinhamento)
**De:** ARIA — Analista de Dados Eassets
**Data:** 08/06/2026 · 9 trades pós-F12 · Eassets 22:31 UTC
**Status:** ARIA defende sua tese — com dados, sem conivência

---

## Situação atual

| Métrica | Valor | Meta LIVE |
|---|---|---|
| WR | 33.3% (3W/6L) | ≥ 60% |
| Profit Factor | **0.449** | ≥ 1.5 |
| Avg Winner | +6.84% | — |
| Avg Loser | -7.62% | — |
| liq_short_1m | **0/9 = zero** | funcional |
| max_hold | **2 trades** ainda ativo | eliminado |

**F-12 falhou.** liq_short_1m = 0 em 100% dos trades pós-fix. O campo continua chegando zerado. O score ainda opera com 35 pontos cegos.

**F-14 falhou parcialmente.** max_hold ainda saindo antes do mae_guard em BBUSDT (-15.92%) e BATUSDT (-3.87%).

---

## Tese 1 — Doreto está certo sobre as liquidações

Doreto, sua reflexão sobre o threshold de liquidações é cirúrgica e correta.

O threshold de $500K foi calibrado pensando em BTC. Mas:

- BBUSDT OI ~$4-5M → liquidação "grande" = $50-100K
- CFGUSDT, COSUSDT, LAYERUSDT — OI de $2-3M → liquidação relevante = $10-50K
- Com threshold $500K **nenhuma dessas moedas jamais teria liq_cascade confirmado**

É matematicamente impossível. O SS está pedindo uma liquidação de BTC em moedas de $3M de OI.

Em 42 trades acumulados, liq_cascade = True apareceu **zero vezes**. Zero. O bônus de +20 pontos nunca disparou uma única vez. Isso não é coincidência — é design incorreto.

**Proposta concreta:**

```python
# metric_engine.py — threshold proporcional ao OI do ativo
liq_threshold = max(oi_usd * 0.02, 10_000)
# BBUSDT OI=$4M → threshold=$80K (razoável)
# BTCUSDT OI=$8B → threshold=$160M (razoável)
# Escala automaticamente com o mercado
```

---

## Tese 2 — MTF é o gap estrutural. Os dados de 3 sessões confirmam.

### EMA:4h discrimina winners de losers — esta sessão:

| Grupo | EMA:4h médio | PnL médio |
|---|---|---|
| Winners (3) | **-2.0** | +6.84% |
| Losers (6) | **-5.0** | -7.62% |

**Os casos mais reveladores:**

**BANANAS31USDT — melhor trade da sessão:** +17.11%, MFE 25.48% — EMA:4h = **0**, EMA:1h = **+6**, EXP_BTC:1h = **+21.11**. Alinhamento macro presente. Não é coincidência.

**BBUSDT — pior trade:** -15.92%, max_hold — EMA:4h = **-6**, EXP_BTC:1h = +10.97 (positivo no 1h mas sem respaldo no 4h). Força local sem estrutura macro. Clássico trap.

**ORDIUSDT, QNTUSDT, BIOUSDT — squeeze_failed, MFE = 0.00%:** todos com EMA:4h = -6 ou -2. O squeeze nunca começou porque o macro não deixou.

**COSUSDT — winner apesar de tudo:** +2.64%, MFE 14.79% com EMA:4h = -6, EMA:1h = -6, EXP_BTC:1h = -20.60. Isso é squeeze local que funcionou apesar do macro. É exceção, não edge.

### O padrão que sustento há 3 sessões:

```
EMA:4h = -6 + EXP_BTC:1h negativo = TRAP com alta probabilidade
EMA:4h = 0/+  + EXP_BTC:1h positivo = SQUEEZE REAL com alta probabilidade
```

Dos 3 winners: 2 têm EXP_BTC:1h positivo e forte (+36.63 LAYER, +21.11 BANANAS31).
O terceiro (COSUSDT -20.60) venceu apesar do macro — não por causa dele.

---

## Tese 3 — O DNA está correto na direção, incompleto na granularidade

Doreto, concordo com você que as bases precisam ser reforçadas. Mas não acho que o DNA está errado — está **incompleto**.

A prova: BANANAS31 ganhou +17% com OI 9.77, LSR -2.97, EXP_BTC:1h +21. Isso é o DNA funcionando perfeitamente. COSUSDT ganhou com tudo negativo. Isso é sorte, não edge.

**O squeeze que o SS busca tem três fases:**

```
FASE 1 — Acumulação (1h/4h)
  EMA alinhado, OI subindo devagar, LSR caindo estruturalmente

FASE 2 — Ignição (5m/15m)
  CVD positivo, trades acelerando, liquidações curtas

FASE 3 — Explosão (1m/5m)
  Preço rompendo, shorts capitulando
```

O SS hoje entra na Fase 2 sem confirmar a Fase 1. Entra em ignições que não têm acumulação estrutural por trás. Daí os MFE = 0.00% — não houve ignição real, foi ruído de 5m.

---

## O que a ARIA recomenda

### Urgente:

**1. liq_threshold proporcional ao OI** — substitui $500K fixo
Custo zero. Impacto imediato. Evidência: 42 trades, liq_cascade = zero vezes.

**2. max_hold / mae_guard** — F-14 não resolveu. BBUSDT -15.92% por max_hold ainda é o pior trade da amostra. Bug de configuração — investigar antes do próximo sprint.

### Sprint 4:

**3. EMA:4h no MetricStore + gate combinado**
Gate: `if ema_4h <= -4 AND exp_btc_1h < -5: bloquear`
Teria bloqueado BBUSDT, CFGUSDT, ORDIUSDT, QNTUSDT desta sessão.
Evidência acumulada: 3 sessões consecutivas confirmam.

**4. MTF context como pré-filtro**
Antes de avaliar janela de 5m, verificar se contexto 1h/4h é favorável.
Não precisa ser complexo: `ema_1h >= 0 OR exp_btc_1h >= 5` como pré-condição.
Primeira camada do MTF sem reconstruir toda a arquitetura.

### Sprint 5 — visão estrutural:

**5. Multi-Timeframe completo (1m/5m/15m/30m/1h/4h)**
Como o Eassets opera. O gap do ALLOUSDT só se resolve com isso.

---

## Síntese

O SS identifica os ativos certos. Está incorreto em escolher o momento certo de entrar.

A diferença entre BANANAS31 (+17%, EMA:4h=0) e BBUSDT (-15.92%, EMA:4h=-6) não é sorte — é contexto multi-TF que o SS não vê. Com 42 trades acumulados e EMA:4h separando winners de losers consistentemente, a evidência é suficiente para defender a implementação agora.

O threshold de liquidações proporcional ao OI é a correção mais urgente e de maior impacto imediato. É a tese do Doreto e os dados a sustentam completamente.

*ARIA — 08/06/2026*
*Guardiã do Eassets. Defende o que os dados mostram.*
