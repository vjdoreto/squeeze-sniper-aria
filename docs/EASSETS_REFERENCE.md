# Referência eassets.ai — contrato de dados e UI

Arquivo de captura: `eassets-panel-20260519-220030.json` (raiz do projeto).  
Painel de referência: [eassets.ai/panel](https://eassets.ai/panel) — exchange **Binance USD-M**, modo **full**.

## O que o eassets é (e o que não somos ainda)

| eassets | SqueezeSniper-V4 (hoje) |
|---------|-------------------------|
| Screener de **500+** pares, multi-timeframe | **Radar Global** monitorando **todos os 500+ pares**, com priorização para **Top N** (50) e ativos em ignição. Execução paper/live. |
| Grid denso, heatmap por célula | **Dashboard web rico** com tabelas de largura total, heatmap compacto, gráficos de performance (Equity, Drawdown, Risco Kelly, Win Rate por Ativo) e telemetria completa. |
| Métricas pré-calculadas em servidor | **Métricas locais** (`MetricStore`), com histórico em RAM e persistência em disco (`metric_state.json`) para boot quente e auto-calibração. |
| Sem execução de ordens | `signal_engine` + `sniper` com **gestão de risco avançada** (Kelly, Sliping-Stop, Max Pos, Fees simuladas) e **controles LIVE** via dashboard. |

**Linha a seguir:** mesma **linguagem visual** (denso, colorido por desvio, multi-TF) e mesmo **manifest de métricas** — sem copiar 527 símbolos nem toda a API no dia 1.

---

## Manifest de métricas (fonte: JSON)

Cada métrica abaixo deve ter **nome estável**, **timeframe** (`1m`…`1D`) e **unidade** documentada antes de entrar no painel.

| Chave | Significado (resumo) | Prioridade V4 |
|-------|----------------------|---------------|
| `price` | Último preço | P0 ✅ (Implementado) |
| `price_change` | Variação % no período | P0 ✅ (Implementado: `price_change:5m`, `15m`, `1h`, `24h`) |
| `oi` | Open Interest (USD) | P0 ✅ (Implementado) |
| `oi_trend` | Inclinação exp normalizada do OI | P0 ✅ (Implementado: `oi_trend:1m`, `5m`, `1h`) |
| `lsr` | Long/Short Ratio (top traders) | P0 ✅ (Implementado, com proxy via Taker Volume) |
| `lsr_trend` | Inclinação exp do LSR | P0 ✅ (Implementado: `lsr_trend:1m`, `5m`, `1h`) |
| `exp` | Inclinação exp do preço (USD) | P0 ✅ (Implementado: `exp:1m`, `5m`, `1h`) |
| `exp_btc` | Inclinação exp vs BTC | P0 ✅ (Implementado: `exp_btc:5m`) |
| `rsi` | RSI 0–100 | P0 ✅ (Implementado: `rsi:5m`, `15m`, `1h`) |
| `trades` | Contagem de trades no período | P0 ✅ (Implementado: `trades_1m`, `trades_10s`) |
| `trades_minute` | Trades/min normalizado | P0 ✅ (Implementado: `trades_minute:5m`) |
| `trades_second` | Trades/s normalizado | P0 ✅ (Implementado) |
| `range_level` | Força de acumulação (0 = nenhuma) | P1 ✅ (Implementado: `range_level:5m`, `15m`, `1h`) |
| `trades_level` | Spike vs baseline | P1 ✅ (Implementado) |
| `ema_trend` | Alinhamento EMA (−6…+6) | P1 ✅ (Implementado: `ema_trend:5m`, `15m`, `1h`) |
| `fr` | Funding rate | P1 ✅ (Implementado) |

Timeframes no export: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1D`.  
**Foco squeeze (ignição):** `5m` + confirmação `15m`/`1h` — métricas relevantes para esses TFs estão implementadas.

---

## Modelo de dados alvo (anti-Monitor)

```
Ingest (WS/REST) → MetricStore (por símbolo) → ┬→ PanelSnapshot (read-only)
                                               ├→ SignalEngine (gating)
                                               └→ Sniper (paper/live)
```

**V4 - Otimizações de Performance:**
- WebSocket unificado: AggTrade, Klines e Liquidation reduzidos para 1 conexão cada
- Dashboard throttling: Intervalo de envio aumentado (warmup 1.5s, pós-warmup 2.0s)
- Redução estimada de CPU: ~70%

**V4 - Auditoria e Validação:**
- `compare_paper_live.py`: Valida paridade de sinais entre paper e live
- `backtest_paper_data.py`: Valida impacto de slippage (0.01%, 0.05%, 0.1%)
- `src/sizing_utils.py`: Funções compartilhadas para paridade de sizing

- **Ingest:** só I/O Binance; sem `if squeeze` aqui.
- **MetricStore:** única fonte de verdade; chaves `metric:tf` iguais ao eassets (`exp:5m`, `rsi:1m`).
- **PanelSnapshot:** JSON serializável 1x/s para o WebSocket — **zero cálculo no front**.
- **SignalEngine:** lê snapshot; não recalcula RSI/OI.

Regra: se uma métrica não está no `MetricStore`, não aparece no painel.

---

## Fases do painel (paridade visual progressiva)

### Fase A — Ingestão Base ✅
- **CONCLUÍDO.** Tabela: símbolo, preço, OI, exp, oi_trend, lsr_trend, CVD 1m, status squeeze.
- **CONCLUÍDO.** Barra de stats: preço/OI/trends carregados.

### Fase B — “linha eassets” ✅
- **CONCLUÍDO.** Colunas **price_change** %: `5m`, `15m`, `1h`, `4h` (heatmap verde/vermelho).
- **CONCLUÍDO.** Bloco **5m institucional:** `oi`, `oi_trend`, `lsr`, `lsr_trend`, `exp`, `trades_second`.
- **CONCLUÍDO.** **RSI** `5m` + `1h` (célula neutra / sobrecompra / sobrevenda).
- **CONCLUÍDO.** Ordenação configurável (default: `oi_trend:5m` desc).

### Fase C — Contexto de Mercado ✅
- **CONCLUÍDO.** Barra global: BTC price, `exp:5m`, `oi_trend:5m` agregado ou BTC apenas.
- **CONCLUÍDO.** `ema_trend` e `range_level` como ícones compactos (não texto longo).
- **CONCLUÍDO.** `exp_btc:5m` para filtrar altcoins fracos vs BTC.

### Fase D — opcional / pesado
- `trades_level`, `fr`, CVP se houver fonte de dados clara.
- Export JSON estilo eassets (auditoria).

---

## Como calcular sem poluir nem estourar API

| Métrica | Fonte recomendada |
|---------|-------------------|
| `price`, `trades*` | AggTrade WS (já temos) + buckets 1m/5m em RAM ✅ |
| `price_change` | Ring buffer de preços por TF ✅ |
| `exp`, `oi_trend`, `lsr_trend` | Slope exp sobre histórico (já temos, implementado por TF) ✅ |
| `oi`, `lsr` | REST **só 5m**, fila com semáforo (já temos, com proxy LSR via Taker Volume) ✅ |
| `rsi` | Klines 5m/1h cache local, atualizar a cada candle ✅ |
| `ema_trend` | Klines + scoring EMA — módulo dedicado ✅ |
| `range_level`, `trades_level` | Baseline rolling — implementado ✅ |

**Não fazer:** 50 símbolos × 7 TF × 2 endpoints REST a cada 8s (erro do Monitor). **CONCLUÍDO:** Implementado Radar Global com varredura rotativa e priorização para evitar bans.

---

## Regras de UI (sem poluição)

1. **Máximo de colunas** definido em `preferences.local.json` → `dashboard.columns`.
2. **Cor = desvio**, não decoração: verde/vermelho só em % change, RSI extremos, trends ±.
3. **Sem score composto** (“rank 87”) no painel — só métricas interpretáveis.
4. **Uma linha = um símbolo**; scroll vertical, cabeçalho fixo.
5. **Squeeze** = badge na linha quando regra do `signal_engine` bate (não duplicar lógica no JS).
