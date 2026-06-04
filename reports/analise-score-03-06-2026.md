# Análise de Discriminação do Score — 03/06/2026
**Fonte:** Brain · Análise de 40 trades (paper_closed.jsonl)  
**Respondendo à pergunta do Forge:** "Qual o peso atual do trades_1m no score e quais campos discriminam?"

---

## Peso atual do trades_1m no score: ZERO direto

`trades_1m` **não tem peso direto** em `calculate_fit_score()`.

Existe o **HFT Burst** baseado em `last_trades_10s`:
```python
# market_view.py
if trades_10s > 30 and trades_10s > (avg_trades_10s * 2.0):
    score += 10
elif trades_10s > 15 and trades_10s > (avg_trades_10s * 1.3):
    score += 5
```

`trades_1m` é usado **apenas** em `calculate_dynamic_risk_with_hft()` para penalizar sizing — não no score.

---

## Discriminação por campo — 40 trades

| Campo | WIN avg | LOSS avg | Diff | Discrimina? | r_pb |
|---|---|---|---|---|---|
| `mfe` | 8.22% | 2.95% | +5.27% | ✅ SIM | +0.217 |
| `mae` | -4.48% | -8.84% | +4.36% | ✅ SIM | +0.181 |
| `oi_trend` | 0.018 | 0.013 | +0.005 | ✅ SIM | +0.131 |
| `lsr_trend` | -0.474 | -0.630 | +0.156 | ✅ SIM | +0.071 |
| `trades_1m` | 95.5 | 58.2 | +37.4 | ⚠️ FRACO | +0.061 |
| `exp_btc` | 0.045 | 0.041 | +0.003 | ⚠️ FRACO | +0.044 |
| `lsr_change_pct` | -1.37% | -1.54% | +0.18% | ⚠️ FRACO | +0.031 |
| `score` | 96.4 | 95.7 | 0.7pts | ❌ NÃO | ~0 |
| `cvd_change_pct` | 0.000 | 0.000 | 0 | ❌ ZERADO* | — |
| `rsi` | 0.000 | 0.000 | 0 | ❌ ZERADO* | — |
| `ema_trend` | 0.000 | 0.000 | 0 | ❌ ZERADO* | — |
| `liq_short_1m` | 0.000 | 0.000 | 0 | ❌ ZERADO* | — |

> *r_pb = correlação ponto-biserial com WIN (>0.1 = relevante, >0.2 = forte)  
> *ZERADO = Brain leu campo sem sufixo `:5m` ou logging gap (veredito Forge)

---

## Veredito Forge sobre os campos "zerados"

| Campo | Diagnóstico Brain | Veredito Forge |
|---|---|---|
| `rsi_5m` | Zerado no sinal | Logging gap — não estava no signal dict. Score usa dado correto. **Corrigido: agora exportado** |
| `ema_trend` | Zerado | Valor 0 legítimo em mercado neutro (range -6 a +6). Campo existia no signal |
| `ob_imbalance` | Zerado | Logging gap — não estava no signal dict. **Corrigido: agora exportado** |
| `cvd_change_pct` | Zerado | Brain leu sem sufixo `:5m`. Com sufixo: valores reais existem |

---

## Conclusão

1. **mfe e mae** são os maiores discriminadores — mas são métricas de saída, não de entrada
2. **oi_trend** (r_pb +0.131) é o único preditor de entrada com correlação moderada confirmada
3. **score** com r_pb ≈ 0 é inútil como preditor na amostra atual
4. **trades_1m** tem diferença bruta grande (+37.4) mas correlação fraca (+0.061) — amostra de 40 trades insuficiente

**Próximo run:** após 50+ trades com `rsi_5m` e `ob_imbalance` agora exportados no signal dict.

---

## Win Rate por MAE inicial

| MAE inicial | Trades | Win Rate |
|---|---|---|
| < 2% | 9 | **78%** |
| < 5% | 23 | **61%** |
| < 8% | 28 | 57% |
| < 10% | 32 | 50% |

---

_Brain · 03/06/2026 · Análise de 40 trades paper_
