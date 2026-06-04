# Governança — SqueezeSniper-V4

Operação e evolução do projeto após o pivot do `#3 Monitor`.
Referência visual e de dados: [docs/EASSETS_REFERENCE.md](EASSETS_REFERENCE.md), captura `eassets-panel-20260519-220030.json`.

## Norte estratégico

**Produto:** rastro institucional (OI/LSR/fluxo) + detecção de squeeze + execução paper/live.
**Referência UX:** painel eassets (denso, heatmap, multi-TF) — **inspirado, não clonado no dia 1**.
**Anti-meta:** outro Monitor monolítico com 200 indicadores e score mágico.

## As Leis de Ferro (Novos Princípios)

1. **Gating Macro Inegociável (Dominância Assassina)** — O motor (`data_engine.py`) **nunca** pode deixar de rastrear `BTCUSDT`, `ETHUSDT` e `BTCDOMUSDT`. Sinais LONG em altcoins são sumariamente bloqueados se o BTC estiver caindo e a Dominância subindo.
2. **Cérebro Automático (Fit Score)** — A tomada de decisão humana foi substituída por matemática. O `calculate_fit_score` exige alinhamento de OI Trend, LSR, EXP_BTC e CVD 1m. Qualquer remoção dessas métricas do pipeline é estritamente proibida, pois descalibra o Score de 0-100.
3. **Execução Dinâmica Sensível ao Fluxo** — O `sniper.py` foi proibido de usar "Take Profits fixos cegos". O TP é sempre alargado matematicamente se o CVD > 10k/50k e o SL é alargado se a volatilidade 1h > 5%. E o `tickSize` oficial da Binance **sempre** será respeitado para arredondamentos.
4. **Lean hot path** — Só entra no loop crítico o que muda a entrada (OI, LSR, exp, CVD).
5. **Painel Read-Only e Visual** — O Treemap e a Barra Macro consolidam o estado do mercado. O front não calcula indicadores, ele apenas consome o snapshot em memória gerado pelo `bot_state.py`.

## Protocolo de Boot Seguro (P0)

**Implementado**: 2026-05-30 (Sprint P0)

- ✅ Sistema **SEMPRE** inicia em PAPER mode
- ✅ LIVE só após warmup de 300s (5 minutos)
- ✅ Validação de saldo mínimo obrigatória antes de LIVE
- ✅ Isolamento completo paper/live (sem contaminação cruzada)
- ✅ `_apply_runtime_mode()` como único ponto de verdade para troca de modo
- ✅ `state.bind_sniper()` para sincronização de estado

**Arquivos**: `main.py`, `config.py`, `bot_state.py`

## Correlation Guard (DNA Sniper P0)

**Implementado**: 2026-05-30 (Sprint P0)

Evita múltiplas posições no mesmo grupo de correlação:

```python
CORR_GROUPS = {
    "L1": ["SOLUSDT", "AVAXUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT"],
    "DeFi": ["AAVEUSDT", "UNIUSDT", "CRVUSDT"],
    "Meme": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT"],
}
```

- ✅ Máximo 1 posição por grupo
- ✅ Evita exposição duplicada
- ✅ Debug JSONL para auditoria

**Arquivos**: `src/live_tracker.py`

## Motor de Execução LIVE (Concluído)

- ✅ **Partial Breakeven**: Execução real de venda parcial no ponto de lucro zero + taxas.
- ✅ **LSR Gap Guard**: Fallback para última métrica válida em caso de erro 429/timeout REST.
- ✅ **Advanced API**: Endpoints para calibração de ATR, Trailing e Kelly em runtime.
- ✅ **Data Audit**: Logging contínuo de completude de métricas (P0.1).
- ✅ **Data Resiliency**: Lógica de Retry (2x) para OI e LSR Oficial no DataEngine (P1.2).
- ✅ **Latency Guard**: Cache de filtros injetado no Sniper via `hydrate_filters` (P3 Fix).
- ✅ **Adaptive Polling**: Trailing stop com frequência variável (10s/30s) para economizar API.
- ✅ **CPU Sieve**: Cache de Fit Score com 2s TTL e telemetria de Hit Rate.

**Impacto**: Performance crítica melhorada sem perda de qualidade.

**Arquivos**: `main.py`

## Partial Breakeven (DNA Sniper P1)

**Implementado**: 2026-05-30 (Sprint P1)

- ✅ Fecha parcial da posição no breakeven (entry + fees)
- ✅ Protege capital em lucro
- ✅ Configurável via `partial_tp_breakeven_pct`
- ✅ Flag `breakeven_partial_closed` para controle
- ✅ Debug JSONL para auditoria

**Exemplo**: Se `partial_tp_breakeven_pct = 0.5`, fecha 50% da posição quando preço atinge breakeven.

**Arquivos**: `src/live_tracker.py`

## Trailing Stop (DNA Sniper P1)

**Implementado**: 2026-05-30 (Sprint P1)

- ✅ Baseado em swing low (ou preço - 0.5% se indisponível)
- ✅ Ativa após lucro mínimo de 1%
- ✅ **Nunca abaixa SL** (segurança)
- ✅ Configurável via `sl_trailing_swing_low`
- ✅ Debug JSONL para auditoria

**Regra**: `new_sl = max(swing_low, current_sl, entry_price)`

**Arquivos**: `src/live_tracker.py`

## Close Confirmation (DNA Sniper P2)

**Implementado**: 2026-05-30 (Sprint P2)

- ✅ Valida preço de fechamento contra preço estável do mercado
- ✅ Rejeita fechamento se divergência > 2%
- ✅ Evita slippage extremo em ordens de mercado
- ✅ Debug JSONL para auditoria

**Exemplo**: Se close_price = 100 e stable_price = 98, divergência = 2.04% → **REJEITADO**

**Arquivos**: `src/live_tracker.py`

## Contrato de Dados (Alinhamento de Colunas)
Para evitar o deslocamento visual ("RSI em Stats"), qualquer alteração na tabela deve seguir:
- **Sincronia Total:** Se adicionar um `<th>` no `web_dashboard.py`, deve adicionar o correspondente `<td>` na mesma posição ordinal no loop de renderização.
- **Chaves Planas:** O `market_view.py` envia apenas escalares (números/strings). Acesso a dicionários aninhados (`r.rsi["5m"]`) no JS é proibido; use chaves planas (`r.rsi_5m`).
- **Fallback Seguro:** Toda métrica deve prever `null` ou `—` para evitar erros de renderização que travam o loop do Dashboard.
- **Sem NONE Values:** Métricas numéricas devem usar `0.0` ou `50.0` (RSI) como fallback, nunca `None`.

## Configuração

| Arquivo | Conteúdo | Git |
|---------|----------|-----|
| `.env` | `API_KEY`, `API_SECRET`, integrações | **Nunca** |
| `preferences.local.json` | modo, top_n, dashboard, thresholds | **Ignorado** (local) |
| `preferences.json` / `.example` | defaults e template | Sim |

Prioridade: `preferences.local.json` → `preferences.json` → `PREFERENCES_FILE` no `.env`.

## Mapa de módulos

| Alvo | Implementado | Próximo passo |
|------|--------------|---------------|
| `metric_engine.py` | ✅ lógica separada | chaves `metric:tf` |
| `signal_engine.py` | ✅ | regras 5m + filtros P1 |
| `executor` / `sniper.py` | ✅ paper/live | tickSize SL/TP |
| `web_dashboard` | Fase A | Fase B (grid eassets) |
| `persistence.py` | ✅ JSONL sinais | snapshot métricas horário |
| `sizing_utils.py` | ✅ (V4) | paridade paper/live |
| `compare_paper_live.py` | ✅ (V4) | auditoria contínua |
| `backtest_paper_data.py` | ✅ (V4) | validação slippage |

## Auditoria e Validação (V4)

### Scripts de Auditoria
- **`compare_paper_live.py`**: Compara sinais, PnL e métricas entre paper e live
  - Identifica sinais que apareceram apenas em um modo
  - Valida paridade de execução
  - Salva resultado em `logs/paper_live_comparison.json`

- **`backtest_paper_data.py`**: Valida impacto de slippage em trades do paper
  - Simula slippage de 0.01%, 0.05%, 0.1%
  - Compara PnL paper vs backtest
  - Identifica trades que mudaram de resultado
  - Salva resultado em `logs/backtest_results.json`

### Paridade Paper→Live
- **Latência Simulada**: Paper adiciona delay aleatório 100-200ms em `open_long()`
- **Sizing Unificado**: `src/sizing_utils.py` garante mesma lógica de dimensionamento
- **Kelly Criterion**: Função compartilhada para cálculo de risco dinâmico

## Prioridade de métricas (governança de escopo)

| Tier | Métricas | Painel | Sinal squeeze |
|------|----------|--------|---------------|
| **P0** | price, oi, oi_trend, lsr, lsr_trend, exp | 5m | obrigatório |
| **P1** | price_change, rsi, trades_*, exp_btc | 5m/1h/4h | filtros |
| **P2** | ema_trend, range_level, trades_level | ícones | opcional |
| **P3** | fr, CVP | omitir até demanda | omitir |

**Proibido** adicionar P2/P3 antes de P0/P1 estáveis em paper 48h+.

## Definition of Done (marco)

1. `python main.py` ≥10 min sem crash; Ctrl+C limpo.
2. Métricas novas documentadas em `EASSETS_REFERENCE.md`.
3. Paper validado; live só com checklist explícito.
4. Rate limit: sem 429 sustentado; `top_n` e semáforo REST documentados.

## Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| **Bloqueio de API (429)** | Filtro `top_n` ≤ 150 usando apenas contratos `USDT`. Polling de LSR reduzido para 60s cache. |
| **Erros de Ordem "Min Price"** | `sniper.py` agora consulta o `PRICE_FILTER` e ajusta os `tickSize` exatos de SL/TP por ativo. |
| **Entradas Cegas (Faca Caindo)** | Regra P2 em ação: Gating bloqueia compra em ativos derretendo e em dias de colapso do BTC. |
| **Crash Visual** | `uvicorn` rodando em thread separada; Javascript encapsulado e testado para grids complexos (Treemap). |
| **Latência** | EXP_BTC calculado matematicamente usando *Futures* do BTC, evitando conexões de *Spot* puramente para latência zero. |

## Artefatos de referência

- `eassets-panel-20260519-220030.json` — contrato real de campos (não commitar exports gigantes no futuro; usar `docs/samples/` se necessário).
- Capturas de painel em `assets/` para regressão visual.

## Revisão

Atualizar `ROADMAP.md` (estado atual) a cada marco fechado ou sprint encerrado.
