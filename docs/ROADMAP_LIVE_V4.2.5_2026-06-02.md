# Roadmap para LIVE — SqueezeSniper V4.2.5

**Data:** 2026-06-02  
**Versão base:** v4.2.5  
**Objetivo:** Transição segura PAPER → LIVE com capital real  
**Premissa:** Sem delírios. Cada sprint tem critério de saída mensurável. Só avança quem passa.

---

## Estado Real (Inventário Honesto)

### Confirmado FEITO (verificado em código hoje)

| Item | Arquivo / Linha |
| ---- | --------------- |
| Boot sempre em PAPER | `main.py` — `_apply_runtime_mode()` |
| DrawdownManager integrado | `main.py` L2303, L435–464 (⚠️ AUDITORIA_BRUTAL estava desatualizada) |
| Trailing stop MFE-based (75% callback) | `paper_tracker.py` L1029 + `preferences.json` |
| Min hold gate 180s | `paper_tracker.py` L1129–1131 |
| Sizing dinâmico (`max(1.0, capital × risk × 0.8)`) | `paper_tracker.py` L730 |
| Score mínimo 90 | `preferences.json` — `signal.min_score` |
| SL 2.5% / TP 8% / Partial breakeven 35% | `preferences.json` + `paper_tracker.py` L1063 |
| Correlation Guard (3 grupos) | `paper_tracker.py` L22–26 |
| Preferences único (`preferences.json`) | Refatoração feita hoje |
| Paridade Paper ↔ Live (8 parâmetros) | Auditoria finalizada hoje |

### GENUINAMENTE PENDENTE

| Item | Risco | Para LIVE? |
| ---- | ----- | ---------- |
| Correlation Guard expandido (só 15 de 100+ símbolos cobertos) | ALTO | Sim |
| Liquidity Guard (validar profundidade OB antes de entrar) | ALTO | Sim |
| `trailing_stop_distance_pct` não wired no PaperConfig | BAIXO | Não (usa default correto 0.015) |
| DNA PTP desabilitado (aguardando validação do trailing puro) | MÉDIO | Avaliação após Sprint 1 |
| Margem de segurança 10% removida no Sniper (ver SAFETY_BACKLOG) | ALTO | Sim — quando capital > $100 |
| Validação estatística (100+ trades paper) | CRÍTICO | Pré-requisito LIVE |

### DESCARTADO (não precisa para ir ao LIVE)

- Backtesting walk-forward (existe `backtest_engine.py` — rodar é tarefa operacional, não sprint de código)
- Regime detection (melhoria de performance, não segurança)
- UI do Dashboard para persistir filtros (cosmético)
- Novos módulos de análise (já existem 7 `analyze_*.py` subutilizados)

---

## Roadmap por Sprints

### Sprint 1 — Validação v4.2.5 (AGORA, 0–48h)

**Objetivo:** Confirmar que as correções de leaks funcionam com dados reais.

**Ação:** Iniciar o bot em PAPER e deixar rodar.

**KPIs obrigatórios (via `python src/analyze_leaks.py` após 24h):**

| Métrica | Target | Bloqueio se abaixo |
| ------- | ------ | ------------------ |
| Margem média por trade | ≥ $40 | Revisar sizing |
| Duração média dos trades | ≥ 3min | Revisar min_hold_seconds |
| Captura de MFE | ≥ 55% | Revisar trailing_stop_callback |
| R:R ratio | ≥ 1.2:1 | Revisar SL/TP |
| Win Rate | ≥ 60% | Revisar filtros de sinal |

**Critério de saída:** ≥ 3 dos 5 KPIs atingidos em 20+ trades → avança para Sprint 2.  
**Se falhar:** Ajuste cirúrgico baseado em dados. Não avança sem passar.

---

### Sprint 2 — Proteção de Capital (2–3 dias de código)

**Objetivo:** Cobrir os dois gaps de risco real antes de ir para LIVE.

#### 2A — Expandir Correlation Guard

**Problema:** CORR_GROUPS atual cobre apenas 15 símbolos (L1, DeFi, Meme). Com 100+ símbolos monitorados, qualquer outra altcoin pode ter 5 posições simultâneas se BTC cair — drawdown instantâneo.

**Solução mínima viável:**

```python
CORR_GROUPS = {
    "L1": ["SOLUSDT", "AVAXUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT", "ADAUSDT", "DOTUSDT", "ATOMUSDT"],
    "DeFi": ["AAVEUSDT", "UNIUSDT", "CRVUSDT", "COMPUSDT", "MKRUSDT", "SNXUSDT"],
    "Meme": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT", "BONKUSDT"],
    "AI": ["FETUSDT", "AGIXUSDT", "OCEANUSDT", "RENDERUSDT", "WLDUSDT"],
    "Gaming": ["AXSUSDT", "SANDUSDT", "MANAUSDT", "ENJUSDT", "GALAUSDT"],
    "Layer2": ["MATICUSDT", "ARBUSDT", "OPUSDT", "STRKUSDT", "ZKUSDT"],
    "BTC_Eco": ["WBTCUSDT", "STXUSDT", "RUNEUSDT"],
}
```

**Regra mantida:** Máximo 1 posição por grupo. Aplica em Paper e Live.

#### 2B — Reinstaurar margem de segurança do Sniper

**SAFETY_BACKLOG (2026-05-29):** A checagem `balance < usdt_amount * 1.1` foi removida. Deve ser reinstaurada quando `usdt_amount > $100` para garantir cobertura de fees e flutuações.

**Solução:** Condicional simples em `src/sniper.py`:

```python
safety_factor = 1.1 if self.usdt_amount > 100 else 1.0
if balance < self.usdt_amount * safety_factor:
    ...
```

**Critério de saída Sprint 2:** Código implementado + Paper rodando sem crash por 4h.

---

### Sprint 3 — Liquidity Guard (3–4 dias de código)

**Objetivo:** Validar liquidez do Order Book antes de abrir posição. Crítico para Live.

**Problema atual:** O sistema entra em qualquer símbolo que passe os filtros de sinal, sem checar se consegue sair. Em moedas de baixa liquidez, o slippage real pode ser 2–5x maior que o simulado.

**Implementação mínima viável:**

```python
def validate_liquidity(order_book: dict, order_size_usdt: float, price: float) -> tuple[bool, str]:
    """Rejeita entrada se não há liquidez suficiente para saída segura."""
    asks = order_book.get("asks", [])  # [[price, qty], ...]
    if not asks:
        return False, "order_book_empty"

    # Simula impacto da ordem: quanto de slippage teria
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
    if implied_slippage > 0.003:  # 0.3% de slippage máximo
        return False, f"slippage_too_high_{implied_slippage:.3f}"

    return True, "ok"
```

**Onde plugar:** Em `signal_engine.py` ou `paper_tracker.py`, antes de `open_long()`.

**Critério de saída Sprint 3:** Liquidity Guard ativo em Paper, rejeitando ≥1 trade por sessão com log auditável.

---

### Sprint 4 — Validação Estatística Paper (7–14 dias de runtime)

**Objetivo:** Ter dados suficientes para decidir com confiança se vai para LIVE.

**Este sprint é principalmente operacional (bot rodando), não de código.**

**Protocolo (baseado em VALIDATION_PROTOCOL.md):**

Dia 1–3:   Coletar trades (target: 30+ trades)
Dia 3:     python src/audit_deep_dive.py
Dia 3:     python src/deep_performance_audit.py
Dia 3:     python src/audit_ghost_outcomes.py
Dia 7:     python src/analyze_leaks.py (50+ trades)
Dia 7:     Decisão: ajustar ou avançar
Dia 10–14: Se ajuste, coletar mais 30 trades
Dia 14:    Decisão final: GO / NO-GO para Live

**KPIs mínimos para GO:**

| Métrica | Target mínimo |
| ------- | ------------- |
| Trades coletados | ≥ 50 |
| Win Rate | ≥ 60% |
| Profit Factor (Win médio / Loss médio) | ≥ 1.5 |
| Max Drawdown no período | ≤ 12% |
| Captura MFE média | ≥ 50% |
| Nenhum trade com loss > 8% | Obrigatório |

**Regra de ouro (do VALIDATION_PROTOCOL):**  
Só altera um parâmetro se `audit_ghost_outcomes.py` mostrar que o motivo de recusa está barrando >50% de sinais que seriam vencedores.

---

### Sprint 5 — Preparação Live (2–3 dias, pós Sprint 4 GO)

**Objetivo:** Validar o pipeline live sem arriscar capital real.

#### 5A — DNA PTP (reavaliação)

Após Sprint 4, analisar se os trades ficaram longos o suficiente sem o PTP. Se a captura MFE estiver ≥55%, manter desabilitado. Se estiver abaixo, reabilitar com delay respeitado.

#### 5B — Live Dry-Run (auto_pilot: false)

```json
// preferences.json
"live": {
    "auto_pilot": false,   // Gera sinais mas NÃO executa
    "usdt_amount": 0.05
}
```

Rodar por 24h. Validar:

- Sinais Live são subconjunto dos sinais Paper (Live é mais restritivo)
- Nenhum crash ao tentar executar
- Logs `live_debug.jsonl` limpos

#### 5C — Checklist de Segurança Live

- [ ] `margin_mode: ISOLATED` confirmado (nunca CROSS)
- [ ] SL nunca abaixo do preço de liquidação (verificar `sniper.py`)
- [ ] `max_open_positions: 3` (Live)  
- [ ] Correlation Guard ativo para Live também
- [ ] Liquidity Guard ativo para Live também
- [ ] Margem de segurança 10% ativa (`usdt_amount` será >$100)

---

### Sprint 6 — Live Gradual (Semana 1 com capital real)

**Objetivo:** 3 trades completos reais para validar execução.

**Configuração inicial:**

```json
"live": {
    "auto_pilot": true,
    "usdt_amount": 0.05,     // Mínimo — literalmente teste de infraestrutura
    "max_open_positions": 1  // Uma posição por vez
}
```

**Validar em cada trade:**

1. Slippage real vs simulado — diferença ≤ 0.15%
2. SL/TP executados no preço esperado
3. Fees corretas (0.04% taker)
4. Correlation Guard funcionando em live

**Critério de saída:** 3 trades fechados sem erro de execução → Sprint 7.

---

### Sprint 7 — Live Scale-Up (Progressivo, semanas 2–4)

**Escalonamento controlado:**

| Etapa | usdt_amount | max_open_positions | Duração mínima |
| ----- | ----------- | ------------------ | -------------- |
| 7A | $5 | 1 | 3 dias / 10 trades |
| 7B | $20 | 2 | 5 dias / 15 trades |
| 7C | $50 | 2 | 7 dias / 20 trades |
| 7D | $100 | 3 | 14 dias / 30 trades |

**Regra de bloqueio em qualquer etapa:**

- Drawdown > 10% na etapa → volta para etapa anterior
- 3 losses seguidos → pausa 24h, roda `audit_deep_dive.py`, avalia

---

## Timeline Estimada (Realista)

Hoje     │ Sprint 1: Liga o bot com v4.2.5
+2 dias  │ Sprint 1: Analisa KPIs (20+ trades)
+5 dias  │ Sprint 2: Correlation Guard + margem segurança
+8 dias  │ Sprint 3: Liquidity Guard
+22 dias │ Sprint 4: 50+ trades Paper coletados + auditoria
+25 dias │ Sprint 5: Dry-run live 24h
+26 dias │ Sprint 6: 3 trades reais (capital mínimo)
+45 dias │ Sprint 7D: $100 com 3 posições

**Prazo total até Live estável com capital relevante: ~45 dias.**  
Otimista (se tudo passar no primeiro ciclo). Se falhar KPIs, repete o sprint.

---

## O Que NÃO Fazer (Anti-Padrões)

1. **Não criar novos módulos** antes de usar os 7 `analyze_*.py` que já existem
2. **Não ir para LIVE antes de Sprint 4** — sem 50 trades de dados é roleta
3. **Não relaxar filtros do Live abaixo do Paper** — o conservador protege capital real
4. **Não escalar capital antes de validar slippage real** — o Paper não simula tudo
5. **Não confiar só no win rate** — profit factor e drawdown máximo são igualmente críticos

---

## Scripts de Auditoria (usar em cada sprint)

| Script | Quando usar |
| ------ | ----------- |
| `python src/analyze_leaks.py` | Sprint 1 e 4 — métricas de captura |
| `python src/audit_deep_dive.py` | Sprint 4 — auditoria completa |
| `python src/deep_performance_audit.py` | Sprint 4 — tiers de score |
| `python src/audit_ghost_outcomes.py` | Sprint 4 — validar filtros |
| `python src/analyze_session_quick.py` | Qualquer momento — snapshot rápido |
| `python src/audit_intelligence_advanced.py` | Sprint 4 — análise avançada |

---

**Responsável:** Engenheiro Bob Doreto
**Capital em risco:** Real — cada sprint deve ser aprovado por dados, não por intuição  
**Versão do documento:** 1.0 — 2026-06-02
