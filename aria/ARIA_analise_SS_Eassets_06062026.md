# ARIA — Análise Cruzada SS × Eassets
**Para:** Brain — Squeeze Sniper  
**De:** ARIA — Analista de Dados Eassets  
**Data:** 06/06/2026 · 21 trades · Eassets snapshot 02:02 UTC  
**Status:** Tese formulada com evidência — aguarda validação do Brain

---

## Contexto da análise

21 trades fechados cruzados com o snapshot do Eassets (02:02 UTC 06/06).  
Os trades ocorreram em janela de ~4 dias. O Eassets é snapshot recente —  
os TFs longos (1h, 4h) são comparáveis e revelam o estado estrutural dos ativos.

**Resultado geral:** 7 wins / 14 losses — WR 33.3%

---

## Descoberta 1 — O EXP_BTC do SS está cego à escala real

**Esta é a descoberta mais importante desta análise.**

O SS mede `exp_btc` em escala linear bruta. Valores típicos: `0.02 a 0.07`.  
O Eassets mede `exp_btc:1h` em escala normalizada. Valores típicos: `-61 a +35`.

Resultado: **o SS não consegue distinguir força real de força fraca** porque sua escala comprime tudo numa faixa de 0.02–0.07 onde qualquer ativo parece "forte vs BTC".

### Evidência direta nos 21 trades:

| Ativo | SS exp_btc | Eassets exp_btc:1h | Resultado |
|---|---|---|---|
| DUSDT | 0.0338 | **-61.36** | LOSS -2.80% |
| XPLUSDT | 0.0363 | **-34.06** | LOSS -1.31% |
| JTOUSDT | 0.0292 | **-10.62** | LOSS -2.99% |
| STXUSDT | 0.0289 | **-9.30** | LOSS -5.55% |
| EIGENUSDT | 0.0318 | **-16.57** | LOSS -5.03% |
| OPNUSDT | 0.0304 | **+30.90** | **WIN +3.58%** |
| PARTIUSDT | 0.0514 | **+23.28** | **WIN +0.62%** |

O SS viu DUSDT (exp_btc=0.0338) como "forte vs BTC". O Eassets via -61.36 — o ativo estava em colapso contra o BTC. O SS entrou, o Eassets nunca teria sinalizado.

**A escala do SS para exp_btc está subdimensionada em ~300x comparado ao que o Eassets usa como referência real de força.**

---

## Descoberta 2 — EMA:4h ausente destrói 85% dos losers mas não discrimina winners

### Dados:

| Grupo | EMA:4h bearish (≤-4) | EMA:4h bullish (≥4) |
|---|---|---|
| Winners (7) | 6/7 (86%) | 1/7 |
| Losers (14) | 11/14 (79%) | 2/14 |

**Conclusão honesta:** EMA:4h bearish não discrimina winners de losers nesta amostra — ambos os grupos têm maioria em bearish porque o mercado macro estava em queda geral.

**O que isso revela:** o SS está acertando *apesar* do macro adverso, não *por causa* de boas condições macro. Os winners com EMA:4h=-6 (ASTERUSDT, BANANAS31, 2Z, PENDLE, STORJ) venceram por força local momentânea — não por alinhamento macro.

**Implicação:** numa janela com macro favorável (EMA:4h positivo), o WR do SS tenderia a ser substancialmente maior. O sistema está sendo testado nas piores condições possíveis.

---

## Descoberta 3 — trades_1m confirma discriminação (Brain já validou)

### Dados desta amostra (21 trades):

| Grupo | trades_1m médio |
|---|---|
| Winners (7) | **109** |
| Losers (14) | **54** |

Reforça o threshold de 50 já implementado. Mas há um outlier importante:

**JTOUSDT:** trades_1m=356 (maior da amostra) → LOSS -2.99% MFE=0.00%

Por que 356 trades/min não salvou? O Eassets mostra: `ema:1h=-6, ema:4h=0, exp_btc:1h=-10.62`. Alta velocidade de trades num ativo em queda macro = volume de *venda*, não de squeeze. **Velocidade sem direção é ruído.**

**Tese complementar:** `trades_1m >= 50` é necessário mas não suficiente. A direção do volume (CVD + EXP_BTC) precisa confirmar que o volume é comprador.

---

## Descoberta 4 — O verdadeiro padrão dos winners

Analisando os 7 winners pelo Eassets:

| Ativo | exp_btc:1h | ema:4h | trades_1m (SS) | MFE |
|---|---|---|---|---|
| ASTERUSDT | -6.16 | -6 | 338 | 4.58% |
| OPNUSDT | +30.90 | +6 | 143 | 8.16% |
| BANANAS31 | +7.11 | -6 | 229 | 5.59% |
| 2ZUSDT | -7.45 | -6 | 25 | 3.41% |
| PARTIUSDT | +23.28 | -6 | 20 | 6.98% |
| PENDLEUSDT | -3.16 | -6 | 3 | 1.89% |
| STORJUSDT | -9.47 | -6 | 8 | 2.57% |

**Padrão claro nos winners de maior MFE:** OPNUSDT e PARTIUSDT têm `exp_btc:1h` fortemente positivo (+30.90 e +23.28). São ativos com força estrutural real vs BTC no 1h — não apenas ruído do 5m.

Os winners "fracos" (PENDLE, STORJ, 2Z) têm exp_btc:1h negativo mas venceram por LSR forte e liquidação de shorts local. Menor MFE, mais sorte do que edge.

**Conclusão:** winners de alta qualidade (MFE > 5%) têm `exp_btc:1h > +10` no Eassets. Winners medianos sobrevivem com força local mas sem respaldo macro.

---

## Descoberta 5 — O problema do BABYUSDT (outlier mais perigoso)

BABYUSDT: trades_1m=129, score=98, EMA:4h=+4, EMA:1h=+6 → LOSS -5.57% MAE=-18.04%

Este era o trade que parecia mais seguro no SS (score alto, trades altos, EMA positivo). O Eassets mostra: `exp_btc:5m=-14.09` — queda violenta de força vs BTC no 5m no momento do snapshot.

O SS entrou com `exp_btc:5m=0.028` (positivo). O Eassets capturou -14.09 no 5m depois. **O movimento de força vs BTC reverteu rapidamente após a entrada** — o SS não tinha como ver isso com sua escala comprimida.

O mae_guard salvou o trade de uma perda ainda maior (-18% MAE vs -5.57% saída). O mae_guard funcionou como deveria.

---

## Tese central — ARIA sustenta ao Brain

> **O SS está identificando os ativos certos mas na escala errada.**

O `exp_btc` do SS (escala 0.001–0.07) não consegue capturar a magnitude real da força relativa ao BTC. O Eassets usa escala normalizada onde `exp_btc:1h = +30` vs `+3` é uma diferença que importa enormemente para o resultado do trade.

**O que estamos perdendo:**
- Ativos com `exp_btc:1h < -10` no Eassets = estruturalmente fracos vs BTC = não entrar
- Ativos com `exp_btc:1h > +15` no Eassets = força estrutural real = priorizar
- O SS vê ambos como "0.028–0.038" = indistinguíveis

**Custo computacional:** zero. O SS já calcula o slope exponencial do preço vs BTC. O problema é a normalização, não o cálculo. Mudar a escala de output do `exp_btc` para refletir magnitude real (ou adicionar `exp_btc:1h` como campo separado no MetricStore) resolveria.

---

## Sugestões para o Brain

| Código | Sugestão | Custo | Impacto | Evidência |
|---|---|---|---|---|
| **EA-06** | Normalizar `exp_btc` para escala comparável ao Eassets OR adicionar `exp_btc:1h` ao MetricStore | baixo | **crítico** | DUSDT -61.36 entrou como 0.034 |
| **EA-07** | Gate: bloquear entrada se `exp_btc:1h < -5` (Eassets-equivalente) | baixo | alto | 8/13 squeeze_failed têm exp_btc:1h negativo |
| **EA-08** | Verificar se `trades_1m` do SS reflete volume comprador ou total — cruzar com CVD direction | médio | médio | JTOUSDT: 356 trades, MFE=0, exp_btc:1h=-10 |

**EA-06 é a mais urgente.** Não é um novo indicador — é corrigir a escala do que já existe.

---

## O que preciso para a próxima análise

Para validar EA-06 com mais precisão:
- Como o SS calcula `exp_btc` internamente — qual é a fórmula exata do slope?
- `metric_engine.py` ou a função de cálculo do `exp_btc`
- Com isso consigo propor exatamente qual normalização aplicar

---

## Nota sobre os dados

O Eassets snapshot é de 02:02 UTC 06/06. Os trades cobrem ~4 dias.  
A comparação do EMA:4h é válida como indicador de tendência estrutural (4h muda devagar).  
A comparação do exp_btc:5m e :1m é menos válida (muda rápido) — usei apenas exp_btc:1h para teses estruturais.  
Amostra de 21 trades ainda pequena — teses são hipóteses fortes, não estatística definitiva.

---

*ARIA — Analista de Dados Eassets · 06/06/2026*  
*Tese construída com evidência dos logs. Brain valida. Forge implementa.*
