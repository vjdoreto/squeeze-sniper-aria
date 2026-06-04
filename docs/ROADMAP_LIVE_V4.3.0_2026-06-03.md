# Roadmap para LIVE — SqueezeSniper V4.3.0
**Versão:** 3.0 · **Data:** 2026-06-03  
**Base:** ROADMAP_LIVE_V4.2.5 (FORGE) + insights Brain v2.0  
**Premissa:** Sem delírios. Cada sprint tem critério de saída mensurável. Só avança quem passa.  
**Guardião:** FORGE — único agente autorizado a alterar o sistema

---

## Estado Real em 03/06/2026

### Concluído hoje

| Item | Arquivo / Linha | Fonte |
|---|---|---|
| `mae_guard` — sai em 120s se PnL < -2% e MFE < 1% | `paper_tracker.py`, `live_tracker.py` | Forge |
| `squeeze_aborted` — sai em 120s se PnL < -1.5% e MFE < 0.5% | `paper_tracker.py`, `live_tracker.py` | Forge |
| Exits imediatos para gates de tempo (bug 2-tick) | `paper_tracker.py` | Forge |
| Trailing callback adaptativo — 50% quando MFE ≥ 3% | `paper_tracker.py`, `live_tracker.py` | Forge |
| Paridade paper ↔ live nos gates | `live_tracker.py` + `sniper.py` | Forge |
| Floor margem $20 com guard de segurança | `paper_tracker.py` L734 | Forge + Brain |
| `liq_cascade` $5k → $500 | `metric_engine.py` L700 | Brain (logs) → Forge |
| `rsi_5m` e `ob_imbalance` exportados no signal dict | `signal_engine.py` L755-757 | Brain (logging gap) → Forge |
| DrawdownManager resetado | `logs/risk_state.json` | Brain (logs) → Forge |
| Dashboard redesign + anti-flicker WebSocket | `web_dashboard.py` | Forge |
| Backup automático ao encerrar + kill de processo | `main.py`, `backup_session.py` | Forge |
| Git init + commit inicial a8ae357 | `.git/` | Forge |
| Manifesto FORGE atualizado — guardião exclusivo | `docs/Engenheiro e DNA do Sniper.md` | Forge |

### Genuinamente Pendente

| Item | Risco | Para LIVE? | Sprint |
|---|---|---|---|
| Correlation Guard expandido (só 7 grupos, ~40 símbolos) | ALTO | Sim | 2A |
| Margem de segurança Sniper (`balance < usdt_amount × 1.1`) | ALTO | Sim (quando > $100) | 2B |
| MAE gate 60s (condicional — aguarda 20+ trades) | MÉDIO | Não imediato | 2C |
| Filtro de divergência temporal EXP_BTC:1m vs 15m/1h | MÉDIO | Não imediato | 2D |
| Liquidity Guard (validar OB antes de entrar) | ALTO | Sim | 3 |
| Validação estatística 50+ trades | CRÍTICO | Pré-requisito LIVE | 4 |

### Descartado (não precisa para ir ao LIVE)

- Backtesting walk-forward — `backtest_engine.py` existe, rodar é tarefa operacional
- Regime detection — melhoria de performance, não segurança
- UI Dashboard para persistir filtros — cosmético
- Adicionar peso trades_1m no score — aguarda amostra ≥ 50 trades com r_pb confirmado

---

## Roadmap por Sprints

### Sprint 1 — Validação v4.2.5 · CONCLUÍDO ✅

**Resultado:** 40 trades analisados. WR 42.5% com causa raiz identificada e corrigida.

| KPI | Target | Resultado | Status |
|---|---|---|---|
| Margem média | ≥ $40 | ~$9 (calibração ativa) | ❌ |
| Duração média | ≥ 3min | 4.8min | ✅ |
| Captura MFE | ≥ 55% | -24.2% | ❌ |
| R:R ratio | ≥ 1.2:1 | 0.83 | ❌ |
| Win Rate | ≥ 60% | 42.5% | ❌ |

**Insight:** trailing_stop WR = 63% (+$7.41). max_hold WR = 0% (-$9.15). Sem max_hold: WR 62.96%.  
**Decisão:** Fixes implementados. Avança para coleta de 20+ trades com novo regime.

---

### Sprint 1.5 — Correções Críticas Pré-Sprint 2 · CONCLUÍDO ✅

> Sprint adicionado pelo Brain com base em análise forense dos logs. Todos os itens executados pelo Forge em 03/06/2026.

| Ação | Status | Veredito |
|---|---|---|
| Pipeline liquidações (liq_cascade $5k→$500) | ✅ Feito | Pipeline funcional. Threshold reduzido para capturar eventos reais |
| Resetar DrawdownManager (risk_multiplier=0.5) | ✅ Feito | Era consecutive_losses=4. Resetado para 1.0x |
| Verificar cvd/oi_change_pct zerados | ✅ Verificado | Brain leu chave errada (sem `:5m`). Dados chegam corretos |
| Floor mínimo $20 no sizing | ✅ Feito | `min($20, capital × 10%)` em `paper_tracker.py` |
| Fix logging aborts (score=0) | ✅ Verificado | Não era bug. `signal_score` já estava correto |
| Exportar rsi_5m e ob_imbalance no signal dict | ✅ Feito | Brain identificou logging gap. Próxima análise terá esses dados |

**Critério de saída:** ✅ Liquidações com threshold correto + DrawdownManager resetado + sizing corrigido

---

### Sprint 2 — Proteção de Capital (2–3 dias de código)

**Status:** Pendente · **Início:** após 20+ trades com fixes do Sprint 1.5 confirmados

#### 2A — Expandir Correlation Guard

**Problema:** 7 grupos cobrem ~40 símbolos. Com 100+ monitorados, posições simultâneas em cascata se BTC cair.

```python
# risk_manager.py — CORR_GROUPS atual (já tem estes):
CORR_GROUPS = {
    "L1":      ["SOLUSDT","AVAXUSDT","NEARUSDT","APTUSDT","SUIUSDT","ADAUSDT","DOTUSDT","ATOMUSDT"],
    "DeFi":    ["AAVEUSDT","UNIUSDT","CRVUSDT","COMPUSDT","MKRUSDT","SNXUSDT"],
    "Meme":    ["DOGEUSDT","SHIBUSDT","PEPEUSDT","FLOKIUSDT","BONKUSDT"],
    "AI":      ["FETUSDT","AGIXUSDT","OCEANUSDT","RENDERUSDT","WLDUSDT"],
    "Gaming":  ["AXSUSDT","SANDUSDT","MANAUSDT","ENJUSDT","GALAUSDT"],
    "Layer2":  ["MATICUSDT","ARBUSDT","OPUSDT","STRKUSDT","ZKUSDT"],
    "BTC_Eco": ["WBTCUSDT","STXUSDT","RUNEUSDT"],
}
# Adicionar grupos: RWA, Perp DEX, Oracles, etc.
```

**Regra:** Máximo 1 posição por grupo. Paper e Live.

#### 2B — Reinstaurar Margem de Segurança do Sniper

```python
# src/sniper.py
safety_factor = 1.1 if self.usdt_amount > 100 else 1.0
if balance < self.usdt_amount * safety_factor:
    ...  # bloquear entrada
```

#### 2C — MAE Gate 60s *(condicional)*

**Condição de ativação:** Brain identificou WR 78% com MAE < 2% nos primeiros 60s, mas amostra é 9 trades — insuficiente.  
**Implementar somente se** 20+ trades com gates 120s confirmarem o padrão.

```python
# paper_tracker.py — verificação adicional em 60s
if duration >= 60 and pnl_pct < -1.5 and current_mfe < 0.5:
    exit_reason = "mae_gate_60s"
```

#### 2D — Filtro de Divergência Temporal *(Brain insight)*

**Conceito:** EXP_BTC:1m negativo + EXP_BTC:15m/1h forte = ativo em compressão antes da squeeze. Entrar após 1m alinhar = entrada de qualidade máxima. Elimina padrão ARUSDT (EXP_BTC:1m=-2.47 mas 1h=+42 → entrou na hora errada do movimento certo).

```python
# signal_engine.py — modo standby por divergência de timeframe
exp_1m  = d.get("exp_btc:1m") or 0.0
exp_15m = d.get("exp_btc:15m") or 0.0
exp_1h  = d.get("exp_btc:1h") or 0.0

if exp_1m < 0 and exp_15m > 10 and exp_1h > 15:
    # Standby: momentum de curto prazo diverge do trend maior
    # Não rejeita — marca como ghost e aguarda alinhamento
    return None  # ou log como "standby_temporal_divergence"
```

**Critério de saída Sprint 2:** Código implementado + paper rodando 4h sem crash.

---

### Sprint 3 — Liquidity Guard (3–4 dias de código)

**Objetivo:** Validar liquidez do Order Book antes de abrir posição. Crítico para Live — slippage real pode ser 2–5x maior que o simulado em moedas de baixa liquidez.

```python
def validate_liquidity(order_book: dict, order_size_usdt: float, price: float) -> tuple[bool, str]:
    """Rejeita entrada se não há liquidez suficiente para saída segura."""
    asks = order_book.get("asks", [])
    if not asks:
        return False, "order_book_empty"

    remaining = order_size_usdt
    filled_cost = 0.0
    for ask_price, ask_qty in asks[:10]:
        ask_price, ask_qty = float(ask_price), float(ask_qty)
        available = ask_price * ask_qty
        if remaining <= available:
            filled_cost += remaining * (ask_price / price)
            remaining = 0
            break
        filled_cost += available * (ask_price / price)
        remaining -= available

    if remaining > 0:
        return False, "insufficient_book_depth"

    implied_slippage = filled_cost - 1.0
    if implied_slippage > 0.003:
        return False, f"slippage_too_high_{implied_slippage:.3f}"

    return True, "ok"
```

**Onde plugar:** `paper_tracker.py` antes de `open_long()`. Depois espelhar em `sniper.py` para Live.

**Critério de saída:** Liquidity Guard ativo em Paper, rejeitando ≥ 1 trade por sessão com log auditável.

---

### Sprint 4 — Validação Estatística Paper (7–14 dias de runtime)

**Este sprint é principalmente operacional. Bot rodando, não código.**

**Protocolo:**

```
Dia 1–3:   Coletar trades (target: 30+)
Dia 3:     python src/audit_deep_dive.py
Dia 3:     python src/deep_performance_audit.py
Dia 3:     python src/audit_ghost_outcomes.py
Dia 7:     python src/analyze_leaks.py (50+ trades)
Dia 7:     Decisão: ajustar ou avançar
Dia 10–14: Se ajuste, coletar mais 30 trades
Dia 14:    Decisão final GO / NO-GO
```

**KPIs mínimos para GO:**

| Métrica | Target mínimo |
|---|---|
| Trades coletados | ≥ 50 |
| Win Rate | ≥ 60% |
| Profit Factor (Win médio / Loss médio) | ≥ 1.5 |
| Max Drawdown no período | ≤ 12% |
| Captura MFE média | ≥ 50% |
| Nenhum trade com loss > 8% | Obrigatório |

**Regra de ouro:** Só altera parâmetro se `audit_ghost_outcomes.py` mostrar que o motivo de recusa está barrando > 50% de sinais que seriam vencedores.

**Análise do score (pós-Sprint 4):**  
Com dados de 50+ trades e `rsi_5m` + `ob_imbalance` agora exportados, o Brain poderá re-rodar a análise de discriminação. Se `oi_trend` (r_pb +0.131) se confirmar como preditor único, avaliar aumento de peso no score. Não antes.

---

### Sprint 5 — Preparação Live (2–3 dias, pós Sprint 4 GO)

#### 5A — DNA PTP (reavaliação)

Após Sprint 4: se captura MFE ≥ 55%, manter trailing puro. Se abaixo, reabilitar Partial TP com delay.

#### 5B — Live Dry-Run

```json
"live": { "auto_pilot": false, "usdt_amount": 0.05 }
```

Rodar 24h. Validar que sinais Live são subconjunto dos Paper (Live é mais restritivo).

#### 5C — Checklist de Segurança Live

- [ ] `margin_mode: ISOLATED` confirmado (nunca CROSS)
- [ ] SL nunca abaixo do preço de liquidação (`sniper.py`)
- [ ] `max_open_positions: 3` (Live)
- [ ] Correlation Guard ativo para Live
- [ ] Liquidity Guard ativo para Live
- [ ] Margem de segurança 10% ativa (`usdt_amount` será > $100)

---

### Sprint 6 — Live Gradual (Semana 1 com capital real)

```json
"live": { "auto_pilot": true, "usdt_amount": 0.05, "max_open_positions": 1 }
```

**Validar em cada trade:**
1. Slippage real vs simulado — diferença ≤ 0.15%
2. SL/TP executados no preço esperado
3. Fees corretas (0.04% taker)
4. Correlation Guard funcionando em Live

**Critério de saída:** 3 trades fechados sem erro de execução → Sprint 7.

---

### Sprint 7 — Live Scale-Up (Progressivo, semanas 2–4)

| Etapa | usdt_amount | max_open_positions | Duração mínima |
|---|---|---|---|
| 7A | $5 | 1 | 3 dias / 10 trades |
| 7B | $20 | 2 | 5 dias / 15 trades |
| 7C | $50 | 2 | 7 dias / 20 trades |
| 7D | $100 | 3 | 14 dias / 30 trades |

**Regra de bloqueio em qualquer etapa:**
- Drawdown > 10% → volta etapa anterior
- 3 losses seguidos → pausa 24h + `audit_deep_dive.py`

---

## Timeline Estimada

```
Hoje (+0d)   │ Sprint 1.5: CONCLUÍDO — fixes ativos
+1 dia       │ Coletar 20+ trades com novo regime (mae_guard, sizing $20, liq cascade $500)
+3 dias      │ Sprint 2: Correlation Guard + margem segurança + MAE 60s (se dados confirmarem)
+6 dias      │ Sprint 3: Liquidity Guard
+20 dias     │ Sprint 4: 50+ trades + auditoria completa
+23 dias     │ Sprint 5: Dry-run live 24h
+24 dias     │ Sprint 6: 3 trades reais ($0.05)
+43 dias     │ Sprint 7D: $100 com 3 posições
```

**Prazo total até Live estável com capital relevante: ~45 dias.**  
Otimista (tudo passando no primeiro ciclo). Se falhar KPIs, repete o sprint — sem atalhos.

---

## Scripts de Auditoria

| Script | Quando usar |
|---|---|
| `python src/analyze_session_quick.py` | Qualquer momento — snapshot rápido |
| `python src/analyze_leaks.py` | Sprint 1 e 4 — métricas de captura |
| `python src/audit_deep_dive.py` | Sprint 4 — auditoria completa |
| `python src/deep_performance_audit.py` | Sprint 4 — tiers de score |
| `python src/audit_ghost_outcomes.py` | Sprint 4 — validar filtros |
| `python src/audit_intelligence_advanced.py` | Sprint 4 — análise avançada |

---

## Anti-Padrões (Não Fazer)

1. Não ir para LIVE antes do Sprint 4 — sem 50 trades é roleta
2. Não relaxar filtros do Live abaixo do Paper — o conservador protege capital real
3. Não escalar capital antes de validar slippage real — Paper não simula tudo
4. Não confiar só no Win Rate — Profit Factor e Drawdown máximo são igualmente críticos
5. Não alterar peso do score sem amostra ≥ 50 trades com r_pb confirmado
6. Não ignorar `risk_state.json` — verificar antes de cada nova sessão
7. Não criar novos módulos antes de usar os scripts de auditoria existentes

---

## Hierarquia de Decisão

```text
Proprietário (Bob Doreto)
    └── FORGE (implementação exclusiva)
            ├── Brain (análise estratégica — insumo)
            └── Dados reais dos logs (evidência — obrigatório)
```

Sugestões externas são insumos. Implementação só ocorre com evidência confirmada no código.

---

**Responsável:** Bob Doreto  
**Capital em risco:** Real — cada sprint aprovado por dados, não por intuição  
**Versão:** 3.0 · 2026-06-03 · Forge + Brain  
**Substitui:** ROADMAP_LIVE_V4.2.5_2026-06-02.md
