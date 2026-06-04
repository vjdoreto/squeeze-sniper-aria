# Mini Auditoria — Diagnóstico das Fraturas
**SqueezeSniper V4 | Foco: correções cirúrgicas em MetricEngine, Sizing, Trading Loop e Thresholds**

---

## Diagnóstico Resumido

| # | Problema | Arquivo | Impacto |
|---|----------|---------|---------|
| 1 | `_calc_exp_slope` retorna `None` | `src/metric_engine.py` | Sinais morrem (poucas oportunidades) |
| 2 | `max_notional_usdt` muito baixo | `src/sizing_utils.py` | Trades não abrem por "margem baixa" |
| 3 | Novos símbolos sem `_history` | `src/metric_engine.py` | Ativo fica morto por 5 min |
| 4 | Peneira dinâmica com `if` errado | `main.py` | Bloqueia ignições em pânico |
| 5 | Score recalculado sem cache | `main.py` | CPU alta, dashboard lag |
| 6 | Thresholds do SignalEngine agressivos | `preferences.json` | Poucos sinais aprovados |

---

## FASE 1 — Correção do Motor de Métricas
**Arquivo:** `src/metric_engine.py`

### Passo 1.1: `_calc_exp_slope` nunca retorna `None`

Localize o método atual (~linha 430) e substitua por:

```python
def _calc_exp_slope(self, values: Sequence[Optional[float]]) -> float:
    valid_values = [v for v in values if v is not None and v != 0.0]
    if len(valid_values) < 2:
        return 0.0
    n = len(valid_values)
    if all(v == valid_values[0] for v in valid_values):
        return 0.0
    x = list(range(n))
    base_val = valid_values[0]
    if base_val and base_val != 0:
        y = [((v - base_val) / base_val) * 100.0 for v in valid_values]
    else:
        y = [float(v) for v in valid_values]
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_xx = sum(xi * xi for xi in x)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    return slope
```

### Passo 1.2: `compute_tf_slopes` grava `0.0` em vez de `None`

```python
def compute_tf_slopes(target_d: Dict[str, Any], window_size: int, suffix: str):
    chunk = hist[-window_size:]
    if len(chunk) < 2:
        target_d[f"exp:{suffix}"] = 0.0
        target_d[f"oi_trend:{suffix}"] = 0.0
        target_d[f"lsr_trend:{suffix}"] = 0.0
        return
    price_series = [s.get("price") for s in chunk if (s.get("price") or 0) > 0]
    target_d[f"exp:{suffix}"] = self._calc_exp_slope(price_series) or 0.0
    oi_series = [s.get("oi") for s in chunk if (s.get("oi") or 0) > 0.0]
    target_d[f"oi_trend:{suffix}"] = self._calc_exp_slope(oi_series) or 0.0
    lsr_series = [s.get("lsr") if s.get("lsr") is not None else 0.0 for s in chunk]
    target_d[f"lsr_trend:{suffix}"] = self._calc_exp_slope(lsr_series) or 0.0
```

### Passo 1.3: History fake para novos símbolos

Em `init_symbols`, após criar o símbolo:

```python
if symbol not in self._history or not self._history[symbol]:
    now = time.time()
    self._history[symbol] = [
        {"price": 0.0, "oi": 0.0, "lsr": None, "cvd": 0.0, "timestamp": now - 2.0},
        {"price": 0.0, "oi": 0.0, "lsr": None, "cvd": 0.0, "timestamp": now},
    ]
    self._warmup_samples[symbol] = max(self._warmup_samples.get(symbol, 0), self._min_warmup)
```

---

## FASE 2 — Correção do Sizing
**Arquivo:** `src/sizing_utils.py`

### Passo 2.1: Margem mínima permissiva

```python
if usdt_margin_target < min_margin_usdt:
    logger.info(
        "Margem alvo muito baixa (%.2f USDT). Tentando margem mínima (%.2f USDT)",
        usdt_margin_target, min_margin_usdt
    )
    usdt_margin_target = min_margin_usdt
    notional_target = usdt_margin_target * leverage
    if notional_target / price < 0.00001:
        return {
            "quantity": 0.0, "notional_usdt": 0.0, "usdt_margin": 0.0,
            "effective_capital": effective_capital, "error": "margin_too_baixa",
        }
```

---

## FASE 3 — Correção do Trading Loop
**Arquivo:** `main.py`

### Passo 3.1: Usar cache de score (Fase 1)

No loop principal, substitua `score_val = calculate_fit_score(d)` por:

```python
score_val = state.get_fit_score(sym, d)
d["score"] = score_val  # Apenas para display — a fonte da verdade é o cache
```

### Passo 3.2: Peneira dinâmica corrigida (Fase 2)

Substitua o bloco da peneira:

```python
squeeze_level = state.market_squeeze_level
if squeeze_level > 80:
    sieve_threshold = 55   # Agressivo: captura ignições precoces
elif squeeze_level > 60:
    sieve_threshold = 65   # Moderado
else:
    sieve_threshold = 75   # Conservador: só elite

d_score = d.get("score", 0)
if d_score < sieve_threshold and not d.get("liq_cascade", False) and symbol not in inflight:
    if d_score > 30:
        state.add_ghost_signal({
            "symbol": symbol, "score": d_score,
            "reason": "sieve_blocked", "price": d.get("price")
        })
    continue
```

---

## FASE 4 — Ajuste de Thresholds
**Arquivo:** `preferences.json` ou `preferences.local.json`

```json
{
  "signal": {
    "min_oi_change_pct": 0.035,
    "min_exp": 0.012,
    "min_oi_trend": 0.003,
    "max_lsr_trend": -0.002,
    "cooldown_seconds": 320,
    "min_trades_1m": 2
  }
}
```

---

## Validação Pós-Aplicação

Rode o bot em **PAPER por 30-60min** e verifique:

| Critério | Como | OK se |
|----------|------|-------|
| Sinais aparecendo | Dashboard > Sinais recentes | ≥ 5 sinais/hora |
| Scores consistentes | Dashboard > Top Símbolos | 0-100, sem `None` |
| Trades abrindo | Dashboard > Paper LONG | Trades listados |
| Win Rate | Dashboard > Paper stats | > 50% após 10 trades |
| Sem erros novos | `logs/error.log` | Limpo |

> Se o win rate continuar < 45% após 20 trades, o problema está nos thresholds do `SignalEngine`. Aí entra calibração fina via `paper_closed.jsonl`.

---

## Se Ainda Estiver Com Problemas

Execute para diagnosticar saídas:

```bash
python -c "
import json
from pathlib import Path
trades = []
path = Path('logs/paper_closed.jsonl')
if path.exists():
    with open(path) as f:
        for line in f:
            trades.append(json.loads(line))
    for t in trades[-20:]:
        exit_data = t.get('exit', {})
        print(f\"{t['symbol']}: PnL {exit_data.get('pnl_pct', 0):.2f}% | Razão: {exit_data.get('reason', '?')}\")
else:
    print('Nenhum trade encontrado')
"
```

---

## Arquivos Modificados

| Arquivo | Passos |
|---------|--------|
| `src/metric_engine.py` | 1.1, 1.2, 1.3 |
| `src/sizing_utils.py` | 2.1 |
| `main.py` | 3.1, 3.2 |
| `preferences.local.json` | 4.1 |
