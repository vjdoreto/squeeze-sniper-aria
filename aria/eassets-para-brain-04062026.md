# Briefing Eassets → Brain → Forge
**De:** Analista Eassets  
**Para:** Brain  
**Data:** 04/06/2026 · Sessão "Analista Eassets"  
**Versão:** 1.0  
**Prioridade:** Alta — evidências diretas nos logs de hoje

---

## Contexto desta análise

Este documento foi produzido cruzando três fontes simultâneas:
- `paper_closed.jsonl` — 13 trades fechados na sessão de hoje
- `signals.jsonl` — 84 sinais gerados na mesma sessão
- `eassets-panel-20260604-142322.json` — snapshot real do Eassets às 17:23 UTC
- Prints visuais do Eassets (30 ativos) e do dashboard SS (Paper + Live)

O Eassets opera como screener puro — rastreia, filtra, exibe. O SS rastreia e executa. O objetivo aqui não é replicar o Eassets, mas extrair o que ele faz que o SS ainda não faz, com custo computacional justificado.

---

## Descoberta 1 — O gate `ema_trend:1h ≤ -3` existe mas falhou no NILUSDT

### Evidência direta
NILUSDT entrou às 16:58, saiu às 17:00 com **-9.6% em 91 segundos**. MFE = 0. A posição nunca foi favorável.

No JSON do Eassets capturado às 17:23 (23 minutos após a saída), NILUSDT ainda mostrava:

```
ema_trend:1h  = -6   (bearish forte)
ema_trend:4h  = -6   (bearish forte)
ema_trend:30m = -6   (bearish)
exp:1h        = -34.34
exp:30m       = -18.78
rsi:4h        = 35.28 (oversold no swing)
```

O `ema_trend:5m` era apenas `+4` — micromomentum positivo dentro de uma tendência macro completamente bearish. No print do SS o NILUSDT aparece na linha 13 com `ema_trend` em `-0.19` (negativo vermelho visível) — o dado chegou, mas não bloqueou.

### Diagnóstico
O código em `signal_engine.py` tem o gate:
```python
if ema_tr <= -3 and not liq_cascade:
    return None  # bloqueia
```
Mas o `ema_tr` lido é `ema_trend:5m`. O valor era `+4` no 5m no momento da entrada — o gate não disparou. O macro (-6 no 1h) foi ignorado.

### Sugestão EA-01 para o Forge
**Adicionar verificação de `ema_trend:1h` ao gate de entrada.**

```python
# signal_engine.py — logo após o gate ema_trend:5m existente
ema_1h = d.get("ema_trend:1h") or 0
if ema_1h <= -4 and not liq_cascade and not is_high_quality:
    self._maybe_log_refusal(symbol, "ema_1h_bearish_macro",
        {"ema_1h": ema_1h, "ema_5m": ema_tr})
    return None
```

**Custo:** zero — `ema_trend:1h` já existe no MetricStore e já é calculado.  
**Impacto esperado:** bloquear entradas em microrebote dentro de tendência macro de queda. NILUSDT teria sido bloqueado.  
**Threshold sugerido:** `-4` (não `-3`, para não ser excessivamente restritivo em correções normais).

---

## Descoberta 2 — `ema_trend:4h` ausente no SS

### Evidência do Eassets
O JSON mostra `ema_trend:4h` para todos os 35 ativos. Os 5 setups de maior qualidade do painel tinham alinhamento completo `5m=6, 1h=6, 4h=6`:

| Ativo | oi_trend:5m | lsr_trend:5m | ema:4h |
|---|---|---|---|
| WLDUSDT | 23.6 | -16.2 | 6 |
| EPICUSDT | 21.5 | -15.6 | 6 |
| VELVETUSDT | 18.0 | -46.5 | 6 |

Sem o `ema_trend:4h`, o SS não consegue distinguir esses setups de máxima qualidade de ativos que parecem bons no 5m+1h mas estão em reversão no swing de 4h.

### O que o Eassets mostra visualmente
No print do painel Eassets, a última coluna à direita exibe `EMA Trend` em blocos coloridos por timeframe (1m, 5m, 15m, 30m, 1h, 4h). É visualmente imediato ver se um ativo está alinhado em todos os TFs ou se tem divergência.

### Sugestão EA-02 para o Forge
**Adicionar `ema_trend:4h` ao MetricStore usando as klines de 4h já buscadas.**

No `metric_engine.py`, a função que calcula `ema_trend:5m` e `ema_trend:1h` usa os buffers de klines existentes. O 4h precisaria de um buffer adicional `_klines[s]["4h"]`.

**Custo:** baixo — klines 4h precisam ser buscadas no bootstrap (igual ao 1h atual). ~50 klines por símbolo prioritário. Não fazer para todos os 529 — apenas para o Top N (50) em monitoramento ativo.  
**Impacto:** identificar setups de alinhamento bull completo + bloquear entradas em ativos bearish no swing.  
**Uso sugerido no signal_engine:** `ema_trend:4h <= -3` → bloquear. `ema_trend:4h >= 4` → bônus no score.

---

## Descoberta 3 — `range_level` multi-TF: o SS usa só o 5m, o Eassets usa 5 TFs

### Evidência direta — o caso NILUSDT novamente
No JSON do Eassets, NILUSDT tinha:

```
range_level:1m  = 4  (alta acumulação micro)
range_level:5m  = 4  (alta acumulação micro)
range_level:15m = 1  (fraca)
range_level:30m = 0  (nenhuma)
range_level:1h  = 0  (nenhuma)
```

O `range_level:5m = 4` parece excelente isoladamente. Mas sem respaldo no 15m/30m/1h, é apenas microacumulação — o preço está comprimido no curto prazo dentro de uma tendência de queda maior. O Eassets mostra isso visualmente com os 5 blocos de TF lado a lado.

### Comparação com setup real
龙虾USDT (top 1 do painel Eassets naquele momento):
```
range_level:1m  = 2
range_level:15m = 4
range_level:30m = 3
range_level:1h  = 1
oi_trend:5m     = 24.7
```
Acumulação em múltiplos TFs = squeeze estrutural. NILUSDT tinha acumulação só no micro = trap.

### Sugestão EA-03 para o Forge
**Criar `range_confluence_score` como soma ponderada dos range_levels disponíveis.**

```python
# Em signal_engine.py ou market_view.py (calculate_fit_score)
r5m  = d.get("range_level:5m", 0) or 0
r15m = d.get("range_level:15m", 0) or 0
r1h  = d.get("range_level:1h", 0) or 0

range_confluence = (r5m * 1.0) + (r15m * 1.5) + (r1h * 2.0)
# Penalizar entradas com range_confluence < 2 (só microacumulação)
# Bonificar entradas com range_confluence >= 6 (acumulação multi-TF real)
```

**Custo:** zero — `range_level:15m` e `range_level:1h` já existem no MetricStore e são calculados. Só falta usar no gating/score.  
**Impacto:** bloquear entradas em microacumulação sem respaldo macro. Alto valor com custo zero.

---

## Descoberta 4 — CVD sem discriminação de intensidade

### Evidência dos logs
Dois trades de hoje com score 100 ambos:

| Trade | cvd_change_pct:5m | score | resultado |
|---|---|---|---|
| MEMEUSDT | +11.4% | 100 | +2.18% ✅ |
| ZBTUSDT | +70.0% | 100 | -0.51% ❌ |

CVD 6× mais forte em ZBTUSDT, mesmo score. O cap em 999.9% com escala linear faz com que valores entre 10% e 200% sejam tratados como equivalentes no score.

### O que o Eassets faz diferente
No JSON do Eassets, `lsr_trend:5m` para VELVETUSDT é `-46.51` e para NILUSDT é `-1.78`. São tratados como magnitudes completamente diferentes na ordenação e coloração do painel — o Eassets não caps lineares, usa escala contínua para ordenação visual.

### Sugestão EA-04 para o Forge
**Aplicar escala logarítmica ao CVD internamente no `calculate_fit_score()`.**

```python
# Em src/market_view.py — calculate_fit_score()
import math

# Substituir uso direto de cvd_change_pct por versão log-normalizada
cvd_raw = signal.get("cvd_change_pct", 0) or 0
cvd_log = math.log10(abs(cvd_raw) + 1) * (10 if cvd_raw >= 0 else -10)
# cvd_raw=11%  → cvd_log ≈ 10.9
# cvd_raw=70%  → cvd_log ≈ 18.5
# cvd_raw=500% → cvd_log ≈ 27.0
# cvd_raw=999% → cvd_log ≈ 30.0
```

O display no dashboard mantém o valor original (%). Só o score interno usa a escala log.  
**Custo:** zero — uma linha de cálculo.  
**Impacto:** score passa a discriminar CVD fraco de CVD forte. Aumenta correlação score×resultado.

---

## Descoberta 5 — Diferença de normalização de escala (informativo, não urgente)

### O que foi observado
O Eassets reporta `oi_trend:5m = 23.59` para WLDUSDT. O SS reporta `oi_trend:5m ≈ 0.023` para ativos equivalentes. Fator: **~1000×**.

Não é bug. São sistemas diferentes:
- **SS:** slope linear bruto (variação por snapshot, escala de 0.001 a 0.1)
- **Eassets:** ângulo normalizado percentual (escala 0–100, onde 100 = crescimento vertical)

Os thresholds do SS foram calibrados para a escala do SS — estão corretos. Mas ao comparar visualmente os dois painéis, os números não são comparáveis diretamente. Isso é só para o Brain ter ciência ao cruzar dados entre os dois sistemas.

---

## Observações visuais dos prints

### Print 1 — Eassets (30 ativos)
- Painel denso com **todas as métricas em colunas por timeframe** visíveis simultaneamente: FR, OI Trend, LSR Trend, EXP BTC (1h/30m/15m/1m), EXP (1h/30m/15m/1m), RSI (4h/1h/15m/5m), Trades, Trades/min, Trades/s, Range Level, Trades Level, EMA Trend (4h/1h/30m/15m/5m/1m)
- Coloração heatmap por desvio em cada célula — imediatamente visual qual TF está quente
- Barra global no topo: BTC price change multi-TF, RSI multi-TF, Trades Level, Trades/min, Trades/s, OI Trend, LSR Trend — tudo com heatmap de cor ao vivo
- **NILUSDT visível na linha 13** com células vermelhas em múltiplas colunas — qualquer analista veria o perigo antes de entrar

### Print 2 — SS Dashboard (Paper)
- **Win Rate: 35.71%** com 14 trades totais na sessão
- **Retorno: -0.51% (-$49.75)** — ainda em calibração, esperado
- Ghost Signals (Audit): 3 entradas NIL bloqueadas por "cvd not confirming" — o gate de Sprint 2 funcionando
- Sinais Bloqueados: **19.593 total** — top motivos: `cvd_not_confirming`, `lsr_trend_too_weak`, `lsr_change_too_weak`, `cvd_not_confirming`, `final_gate_fail`
- Post-Trade Impact (Alpha Decay): visível no dashboard — dados ricos já disponíveis
- Linha NILUSDT: MFE 0.0%, `squeeze_failed` — confirmado trap

### Print 3 — SS Dashboard (Live)
- Capital atual: **$28.12** — modo live com capital mínimo
- **0 trades abertos, 0 fechados** — aguardando sinais no modo live
- Post-Trade Impact mostra 9 trades históricos com drift pós-saída:
  - WIF: saiu trailing_stop -1.86% → drift 5m: -0.32% (correto sair)
  - WLD: saiu trailing_stop +3.01% → drift 5m: -0.96% (saída boa)
  - 龙虾: saiu trailing_stop +0.65% → drift 30m: -4.33% (trailing funcionou)
  - Vários `squeeze_failed` mostrando drift próximo de zero — saída rápida evitou perdas maiores

---

## Resumo das 5 sugestões — ordem de prioridade

| Código | Sugestão | Arquivo | Custo | Impacto | Sprint sugerido |
|---|---|---|---|---|---|
| **EA-01** | Gate `ema_trend:1h <= -4` no signal_engine | `signal_engine.py` | zero | crítico | Sprint 3 (agora) |
| **EA-03** | `range_confluence_score` usando 5m+15m+1h | `signal_engine.py` ou `market_view.py` | zero | alto | Sprint 3 (agora) |
| **EA-04** | CVD log-scale no `calculate_fit_score()` | `src/market_view.py` | zero | médio | Sprint 3 (agora) |
| **EA-02** | `ema_trend:4h` no MetricStore + gate | `metric_engine.py` + `signal_engine.py` | baixo | alto | Sprint 4 |
| **EA-05** | `trades_second` multi-TF (velocidade sustentada vs spike) | `metric_engine.py` | baixo | futuro | Sprint 5+ |

---

## Critério de validação (para o Brain confirmar antes de passar ao Forge)

Antes de implementar EA-01 e EA-03, o Brain deve verificar nos logs:
1. `signal_refusals.jsonl` — quantos sinais seriam bloqueados retroativamente por `ema_1h <= -4`
2. `paper_closed.jsonl` — dos 13 trades, quantos tinham `ema_trend:1h` negativo na entrada
3. `signals.jsonl` — distribuição de `ema_trend` nos 84 sinais gerados (campo `ema_trend` está presente desde Sprint 2)

Se o Brain confirmar que os losers têm `ema_trend:1h < -4` e os winners não — EA-01 vira tarefa imediata para o Forge.

---

## O que este analista precisaria para a próxima análise

Para continuar evoluindo com mais precisão:
- `signal_refusals.jsonl` da sessão de hoje — para cruzar motivos de bloqueio com o painel Eassets
- `market_view.py` (calculate_fit_score) — para sugerir ajustes de peso com evidência
- Mais sessões acumuladas (`paper_closed.jsonl` com 30+ trades) — para validar EA-01 estatisticamente

---

*Analista Eassets · Sessão "Analista de dados Eassets" · 04/06/2026*  
*Este documento é insumo para o Brain. O Brain valida com dados antes de passar ao Forge.*  
*O Forge é guardião exclusivo do código — não implementar sem evidência confirmada.*
