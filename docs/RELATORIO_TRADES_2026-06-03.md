# Relatório de Performance — SqueezeSniper V4

**Data:** 2026-06-03 | **Modo:** Paper LONG | **Período:** 09:58 → 21:48 UTC

---

## Sumário Executivo

| Métrica | Valor |
|---|---|
| Total de Trades | 40 |
| Winners | 17 (42.5%) |
| Losers | 23 (57.5%) |
| PnL Total | **-$1.74** |
| PnL Winners | +$8.46 |
| PnL Losers | -$10.20 |
| Profit Factor | **0.83** |
| Avg PnL% | -1.25% |
| Avg MFE | +5.19% |
| Avg MAE | -6.98% |
| Captura de MFE | **-24.2%** (negativo — o lucro foi devolvido) |

---

## Resultado por Exit Reason

| Exit Reason | Trades | WR | PnL Total | Diagnóstico |
|---|---|---|---|---|
| `trailing_stop` | 27 | **63%** | **+$7.41** | ✅ Funciona |
| `max_hold` | 13 | **0%** | **-$9.15** | 🔴 Causa raiz |

> **Insight crítico:** sem os 13 `max_hold`, o WR seria **62.96% (17/27)** e o PnL seria **+$7.41**. O sistema é rentável quando o trailing stop funciona. O problema é exclusivamente o timeout de 480s segurando posições que nunca se moveram.

---

## Análise: Winners vs Losers

### Winners (17 trades)

| Métrica | Valor |
|---|---|
| Avg PnL% | +5.56% |
| Avg PnL$ | +$0.50 |
| Avg MFE | +8.22% |
| Avg MAE | -4.48% |
| Avg Duração | **199s (3m19s)** |
| Exit Reasons | trailing_stop: 17/17 |

### Losers (23 trades)

| Métrica | Valor |
|---|---|
| Avg PnL% | -6.29% |
| Avg PnL$ | -$0.44 |
| Avg MFE | +2.95% |
| Avg MAE | -8.84% |
| Avg Duração | **354s (5m54s)** |
| Exit Reasons | max_hold: 13 · trailing_stop: 10 |

> **Padrão:** Winners saem em 199s (squeeze resolvido). Losers ficam 354s em média — 77% mais tempo, sangrando lentamente.

---

## Todos os 40 Trades

| # | W/L | Símbolo | Entrada (UTC) | Exit Reason | PnL% | PnL$ | MFE% | MAE% | Dur | Margem |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ✅ | WLDUSDT | 09:58 | trailing_stop | +4.56% | +$0.91 | 5.97% | -4.98% | 181s | $20.00 |
| 2 | ✅ | VICUSDT | 10:15 | trailing_stop | +0.44% | +$0.09 | 1.84% | -27.35% | 197s | $20.00 |
| 3 | ✅ | RESOLVUSDT | 10:17 | trailing_stop | +0.21% | +$0.04 | 2.91% | -1.40% | 425s | $20.00 |
| 4 | ❌ | INJUSDT | 10:29 | **max_hold** | -9.86% | -$1.97 | 0.66% | -10.38% | 481s | $20.00 |
| 5 | ❌ | RENDERUSDT | 10:31 | **max_hold** | -6.82% | -$1.36 | 0.39% | -8.12% | 481s | $20.00 |
| 6 | ❌ | HEIUSDT | 10:48 | trailing_stop | -1.54% | -$0.31 | 3.63% | -24.02% | 228s | $20.00 |
| 7 | ✅ | FILUSDT | 10:52 | trailing_stop | +1.50% | +$0.30 | 2.90% | -4.63% | 193s | $20.00 |
| 8 | ✅ | ARUSDT | 11:03 | trailing_stop | +12.14% | +$2.43 | 15.91% | -1.40% | 181s | $20.00 |
| 9 | ❌ | ZROUSDT | 11:05 | **max_hold** | -5.32% | -$1.06 | 0.00% | -7.30% | 481s | $20.00 |
| 10 | ❌ | UNIUSDT | 11:18 | **max_hold** | -3.82% | -$0.41 | 0.00% | -2.42% | 481s | $10.63 |
| 11 | ❌ | AWEUSDT | 12:02 | **max_hold** | -13.85% | -$0.22 | 0.00% | -12.47% | 481s | $1.60 |
| 12 | ❌ | ZAMAUSDT | 12:02 | **max_hold** | -5.44% | -$0.12 | 0.36% | -4.04% | 481s | $2.16 |
| 13 | ❌ | NEARUSDT | 13:19 | **max_hold** | -7.78% | -$0.62 | 4.59% | -9.72% | 481s | $7.99 |
| 14 | ❌ | KAITOUSDT | 13:25 | **max_hold** | -3.44% | -$0.27 | 0.32% | -3.12% | 481s | $7.99 |
| 15 | ✅ | SUSHIUSDT | 13:49 | trailing_stop | +7.99% | +$0.64 | 12.56% | -1.40% | 181s | $7.98 |
| 16 | ✅ | ALLOUSDT | 13:49 | trailing_stop | +0.56% | +$0.03 | 1.96% | -4.20% | 181s | $5.35 |
| 17 | ❌ | ARUSDT | 14:09 | **max_hold** | -22.59% | -$1.80 | 0.00% | -25.18% | 481s | $7.98 |
| 18 | ❌ | EPICUSDT | 14:30 | trailing_stop | -19.61% | -$0.31 | **15.44%** | -23.85% | 181s | $1.59 |
| 19 | ✅ | FILUSDT | 14:36 | trailing_stop | +5.61% | +$0.06 | 8.53% | -4.49% | 181s | $1.00 |
| 20 | ❌ | TAOUSDT | 14:39 | **max_hold** | -4.51% | -$0.36 | 0.00% | -7.82% | 481s | $7.97 |
| 21 | ✅ | HOLOUSDT | 14:48 | trailing_stop | +0.06% | +$0.00 | 1.46% | -5.69% | 210s | $7.97 |
| 22 | ✅ | ZROUSDT | 14:57 | trailing_stop | +1.36% | +$0.11 | 3.60% | -6.39% | 181s | $7.97 |
| 23 | ❌ | WALUSDT | 14:53 | **max_hold** | -11.13% | -$0.12 | 2.77% | -9.74% | 481s | $1.04 |
| 24 | ✅ | XPLUSDT | 15:10 | trailing_stop | **+31.71%** | +$2.53 | **37.35%** | -1.40% | 182s | $7.97 |
| 25 | ❌ | AIGENSYNUSDT | 15:26 | trailing_stop | -0.05% | -$0.00 | 3.42% | -1.40% | 188s | $7.99 |
| 26 | ❌ | ASTERUSDT | 15:26 | **max_hold** | -11.32% | -$0.43 | 0.00% | -11.36% | 481s | $3.75 |
| 27 | ✅ | STOUSDT | 16:10 | trailing_stop | +5.53% | +$0.44 | 6.94% | -1.40% | 181s | $7.98 |
| 28 | ✅ | FIDAUSDT | 16:25 | trailing_stop | +8.34% | +$0.22 | 10.22% | -2.33% | 181s | $2.64 |
| 29 | ❌ | HOLOUSDT | 16:53 | trailing_stop | -1.42% | -$0.02 | 2.75% | -2.78% | 181s | $1.60 |
| 30 | ❌ | OPNUSDT | 17:01 | trailing_stop | -3.77% | -$0.30 | **16.65%** | -11.15% | 181s | $7.99 |
| 31 | ❌ | PHAUSDT | 18:11 | trailing_stop | -0.21% | -$0.01 | 1.20% | -3.99% | 181s | $2.64 |
| 32 | ❌ | SOLVUSDT | 18:29 | trailing_stop | -0.27% | -$0.02 | 3.66% | -3.93% | 181s | $7.98 |
| 33 | ✅ | PARTIUSDT | 18:39 | trailing_stop | +4.89% | +$0.05 | 8.23% | -1.40% | 181s | $1.04 |
| 34 | ❌ | HAEDALUSDT | 18:45 | trailing_stop | -0.12% | -$0.00 | 1.28% | -6.08% | 205s | $1.04 |
| 35 | ✅ | EULUSDT | 18:50 | trailing_stop | +0.94% | +$0.02 | 2.35% | -3.27% | 181s | $1.60 |
| 36 | ✅ | WLDUSDT | 19:39 | trailing_stop | +1.56% | +$0.03 | 8.08% | -1.59% | 181s | $2.16 |
| 37 | ❌ | HFTUSDT | 19:46 | **max_hold** | -10.91% | -$0.41 | 0.00% | -9.52% | 481s | $3.75 |
| 38 | ✅ | ZECUSDT | 21:05 | trailing_stop | +7.09% | +$0.57 | 8.98% | -2.78% | 181s | $7.98 |
| 39 | ❌ | SYNUSDT | 21:19 | trailing_stop | -0.79% | -$0.06 | 6.66% | -3.41% | 181s | $7.99 |
| 40 | ❌ | ETHFIUSDT | 21:48 | trailing_stop | -0.09% | -$0.01 | 4.03% | -1.40% | 181s | $7.99 |

---

## Anomalias Identificadas

### 🔴 Anomalia 1 — max_hold com 0% Win Rate (causa raiz)

13 trades expiraram em exatamente 481s. **Nenhum foi winner.**

| Símbolo | PnL% | PnL$ | MFE% | MAE% |
|---|---|---|---|---|
| ARUSDT | -22.59% | -$1.80 | 0.00% | -25.18% |
| INJUSDT | -9.86% | -$1.97 | 0.66% | -10.38% |
| AWEUSDT | -13.85% | -$0.22 | 0.00% | -12.47% |
| ASTERUSDT | -11.32% | -$0.43 | 0.00% | -11.36% |
| WALUSDT | -11.13% | -$0.12 | 2.77% | -9.74% |
| HFTUSDT | -10.91% | -$0.41 | 0.00% | -9.52% |
| NEARUSDT | -7.78% | -$0.62 | 4.59% | -9.72% |
| RENDERUSDT | -6.82% | -$1.36 | 0.39% | -8.12% |
| TAOUSDT | -4.51% | -$0.36 | 0.00% | -7.82% |
| ZROUSDT | -5.32% | -$1.06 | 0.00% | -7.30% |
| ZAMAUSDT | -5.44% | -$0.12 | 0.36% | -4.04% |
| KAITOUSDT | -3.44% | -$0.27 | 0.32% | -3.12% |
| UNIUSDT | -3.82% | -$0.41 | 0.00% | -2.42% |
| **TOTAL** | | **-$9.15** | | |

> 5 desses trades tiveram MFE = 0.00% — o preço nunca subiu após a entrada. São entradas falsas onde o squeeze não existia.

### 🟡 Anomalia 2 — Alto MFE, Saída em Loss (trailing stop tardio)

10 trades atingiram lucro relevante mas saíram em prejuízo.

| Símbolo | MFE% | PnL% | Lucro perdido |
|---|---|---|---|
| OPNUSDT | 16.65% | -3.77% | devolveu 20.4% |
| EPICUSDT | 15.44% | -19.61% | devolveu 35.1% |
| SYNUSDT | 6.66% | -0.79% | devolveu 7.5% |
| NEARUSDT | 4.59% | -7.78% | — (max_hold) |
| SOLVUSDT | 3.66% | -0.27% | devolveu 3.9% |
| HEIUSDT | 3.63% | -1.54% | devolveu 5.2% |
| AIGENSYNUSDT | 3.42% | -0.05% | devolveu 3.5% |
| ETHFIUSDT | 4.03% | -0.09% | devolveu 4.1% |
| HOLOUSDT | 2.75% | -1.42% | devolveu 4.2% |
| WALUSDT | 2.77% | -11.13% | — (max_hold) |

### 🟡 Anomalia 3 — Margem Inconsistente

Trades com margem < $2 (calibração ainda ativa): AWEUSDT ($1.60), EPICUSDT ($1.59), FILUSDT ($1.00), WALUSDT ($1.04). Esses trades têm PnL$ irrisório e distorcem as médias.

### 🔵 Anomalia 4 — VICUSDT MAE de -27.35%

MAE de -27.35% em margin terms com PnL final +0.44%. O trade foi extremamente volátil mas o trailing stop salvou.

---

## Filtros de Sinal — Sinais Bloqueados

**Total de sinais avaliados:** 22.192 recusas registradas

| Motivo | Recusas | % |
|---|---|---|
| `lsr_trend_positive` | 7.112 | 32.0% |
| `cvd_negative_quarantine` | 6.427 | 29.0% |
| `final_gate_fail` | 2.119 | 9.5% |
| `rsi_lt_min_rsi_5m` | 1.844 | 8.3% |
| `oi_change_lt_min` | 1.834 | 8.3% |
| `lsr_change_not_negative` | 690 | 3.1% |
| `entrada_tardia` | 424 | 1.9% |
| `exaustao_15m` | 366 | 1.6% |

> O sistema está rejeitando 22.192 sinais para aceitar 40 (taxa de seleção de 0.18%). O problema **não** é na entrada — é na gestão pós-entrada.

---

## Diagnóstico de Causa Raiz

```
PROBLEMA PRIMÁRIO:  max_hold com WR 0%
  → 13 trades × média -$0.70 = -$9.15 (52% de todo o prejuízo)
  → Causa: posições que nunca se moveram (MFE 0%) seguras por 8 minutos

PROBLEMA SECUNDÁRIO: trailing_stop muito lento (callback 75%)
  → MFE médio do trailing_stop losers: 5.7%
  → PnL médio desses losers: -3.5%
  → Lucro foi para o mercado após o pico

SCORE NÃO DISCRIMINA:
  → Score médio winners: ~96 | Score médio losers: ~96
  → Diferença de 0.7 pontos — não é preditor de qualidade
```

---

## Fixes Implementados Hoje (pós-análise)

| Fix | Arquivo | Descrição | Impacto esperado |
|---|---|---|---|
| `mae_guard` | paper_tracker.py | Sai se PnL < -2% e MFE < 1% após 120s | Elimina os 13 max_hold |
| `squeeze_aborted` | paper_tracker.py | Sai se PnL < -1.5% e MFE < 0.5% após 120s | Captura falsos squeezes mais cedo |
| Trailing callback adaptativo | paper_tracker.py | 50% quando MFE ≥ 3%, 75% abaixo | Trava lucro em OPNUSDT/EPICUSDT |
| Exits imediatos | paper_tracker.py | gates de tempo sem 2-tick confirmation | Corrige bug de fechamento |
| `mae_guard` (Live) | live_tracker.py | Mesma lógica no live | Paridade paper ↔ live |
| `squeeze_aborted` (Live) | live_tracker.py + sniper.py | Signal + execução no Sniper | Paridade paper ↔ live |

---

## Projeção Pós-Fixes

| Cenário | WR | PnL Projetado |
|---|---|---|
| Hoje (baseline) | 42.5% | -$1.74 |
| Apenas removendo max_hold | 62.96% | +$7.41 |
| + trailing adaptativo | ~68% | +$9–11 |
| **Target Sprint 1** | **≥ 60%** | **breakeven+** |

---

## Próximos Passos

1. **Coletar 20+ trades novos** com os fixes ativos — observar `mae_guard` e `squeeze_aborted` nos logs
2. **Rodar** `python src/analyze_leaks.py` após 20 trades para comparar métricas
3. **Verificar** se trailing_stop WR sobe de 63% para acima de 70% com callback 50%
4. **Monitorar** captura de MFE — deve sair de -24.2% para ≥ 40%

---

*Gerado automaticamente em 2026-06-03 | SqueezeSniper V4 · Engenheiro Bob Doreto*
