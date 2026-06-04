# 🎯 Squeeze Sniper — Contexto Mestre do Projeto
> **Versão:** 3.0 · **Atualizado:** 04/06/2026

> **Instruções de uso:** Cole este documento no início de qualquer conversa nova com o Claude para retomar o projeto do zero sem perder contexto. Atualize a seção "Estado atual" sempre que houver evolução relevante.

---

## 🤖 Sobre o projeto

- **Dono:** Doreto
- **Projeto:** Bot de trading algorítmico — *Squeeze Sniper*
- **Exchange alvo:** Binance Futures (USDM)
- **Estágio atual:** Avançado, em modo paper trading / (testnet vamos validar em um próximo estágio se vamos seguir ao testnet ou ao LIVE com capital muito baixo)
- **Objetivo:** Exponencializar capital capturando long squeezes — colapsos de liquidação institucional em futuros da Binance

---

## 🔄 Estrutura de sessões de trabalho

O projeto roda em **2 sessões paralelas do Claude** com objetivos complementares:

| Sessão | Ambiente | Foco |
|--------|----------|------|
| **Brain** `Agente Brain — Squeeze Sniper · Estratégia & Evolução` | Claude.ai (trabalho / mobile) | Estratégia, análises, ideias, documentação, cruzamento de dados |
| **Forge** | Laptop pessoal (Antigravity) | Implementação, polimento de código, testes, calibrações, revisões |

> O **documento mestre** é a ponte entre as duas sessões. Deve ser atualizado e compartilhado sempre que houver evolução relevante em qualquer uma delas.

### 🤝 Protocolo de colaboração Brain × Forge (ratificado pelo Forge — 03/06/2026)

**Regra 1 — Quem escreve o quê**
- Brain escreve em `tasks.md`: demandas + evidências nos logs
- Forge executa e marca como concluído com arquivo/linha alterado
- Sem essa separação vira duplicação e ruído

**Regra 2 — Prioridade de conflito**
- Se Brain sugere algo que contradiz o código que Forge conhece por dentro → Forge investiga primeiro
- Só implementa com evidência confirmada
- Exemplo aplicado: achados #3 e #4 do Brain foram descartados após verificação no código

**Regra 3 — Contexto mestre versionado**
- `context.md` precisa ter data e versão em cada atualização
- Brain não pode passar estado desatualizado para sessões futuras
- Versão atual: v3.0 · 04/06/2026

**Fluxo contínuo:**
```
Brain (análise)                    Forge (execução)
     ↓                                    ↓
     ├── tasks.md (demandas+evidências) ──► executa
     │                                    │
     ◄── tasks.md (concluído+arquivo) ────┤ marca done
     │                                    │
     └── context.md versionado ───────────┘ memória compartilhada
```

---

## 🏗️ Arquitetura de integração Brain → Forge

### Backbone: GitHub (repositório privado)

O GitHub serve como **memória compartilhada e fila de tarefas** entre as duas sessões.

**Repositório:** `https://github.com/vjdoreto/squeeze-sniper` (privado)

**Estrutura do repositório:**
```
squeeze-sniper/
├── context.md          → documento mestre (sempre atualizado)
├── tasks.md            → fila de demandas Brain → Forge
├── docs/               → manifesto, DNA, roadmap
└── src/                → código do bot
```

**Fluxo de trabalho:**
1. Brain gera análise ou demanda → escreve em `tasks.md`
2. Forge lê as tasks, implementa e commita o código
3. Forge traz resultado de volta ao Brain (diff / código / logs)
4. Brain analisa, documenta e atualiza `context.md`

---

## 🧠 Estratégia central

O bot funciona como um **sniper de long squeezes**: identifica o momento em que posições compradas alavancadas estão sendo forçadas a fechar (liquidação em cascata), gerando uma avalanche de ordens de venda e busca frenética por liquidez.

A ideia é **embarcar junto com os grandes players** nesse movimento, aproveitando o momentum do colapso institucional.

### Lógica de entrada (confluência de sinais)

| Indicador | Condição para entrada |
|-----------|----------------------|
| OI (Open Interest) | Subindo — novas posições entrando |
| LSR (Long/Short Ratio) | Caindo — shorts dominando / longs sendo fechados |
| EXP_BTC (força vs BTC) | Positivo — ativo ganhando força contra o BTC |
| HFT Activity | Alto — presença de alta frequência detectada |
| Trades/min | Alto — atividade intensa no ativo |
| RSI | Forte (acima de 60–70) |
| CVD (Cumulative Volume Delta) | Subindo — pressão compradora líquida |
| Liquidações em massa | Subindo — confirmação do colapso |

---

## 📊 Motor de score (Squeezometer)

| Componente | Pts máx | Campo |
|-----------|---------|-------|
| EXP_BTC descolamento 5m | +30 | `exp_btc:5m` |
| CVD % crescimento 5m | +25 | `cvd_change_pct:5m` |
| OI % crescimento 5m | +20 | `oi_change_pct:5m` |
| Cascata de liquidação bônus | +20 | `liq_cascade` |
| LSR % queda 5m | +15 | `lsr_change_pct:5m` |
| EXP momentum 5m | +15 | `exp:5m` |
| Liquidações short 1m | +15 | `liq_short_1m_stable` |
| HFT burst 10s | +10 | `last_trades_10s` |
| OI aceleração 5m | +10 | `oi_accel:5m` |
| EMA trend 5m | +10 | `ema_trend:5m` |
| Range level 5m | +10 | `range_level:5m` |
| RSI 5m | +10 | `rsi:5m` |
| OB Imbalance | +10 | `ob_imbalance` |

> Score ≥ 90 dispara entrada · **Limitação atual:** score opera apenas em 5m (sem validação multiframe)

---

## 📋 Estado real do sistema — verificado pelo Forge (04/06/2026)

### Sprint 1.5 — CONCLUÍDO

| Fix | Arquivo | Linha | Status |
|-----|---------|-------|--------|
| mae_guard + squeeze_aborted | paper_tracker.py | — | ✅ |
| Trailing callback 50%/75% | paper_tracker.py | — | ✅ |
| Floor margem $20 | paper_tracker.py | L734 | ✅ |
| rsi_5m + ob_imbalance no signal dict | signal_engine.py | L755-757 | ✅ |
| liq_cascade threshold $5k → $500 | metric_engine.py | L700 | ✅ |
| DrawdownManager resetado | logs/risk_state.json | — | ✅ |

### Sprint 2 — CONCLUÍDO em 04/06/2026

| Fix | Arquivo | Linha | Status |
|-----|---------|-------|--------|
| WebSocket liquidações `!forceOrder@arr` | data_engine.py | L381 | ✅ |
| Gate CVD `min_cvd_change_pct_no_cascade: 1.0` | signal_engine.py | L580 | ✅ |
| Parâmetro no preferences.json (paper + live) | preferences.json | — | ✅ |
| Signal dict completo (22 campos) em paper_closed | paper_tracker.py | L793 | ✅ |

### Diagnóstico de 18 trades — 04/06/2026

| Métrica | Valor |
|---------|-------|
| Win Rate | 27.8% (5/18) |
| PnL total | -$6.45 |
| squeeze_failed | 10 trades · WR 0% · -$9.52 |
| trailing_stop | 7 trades · WR 71% · +$3.97 |
| squeeze_aborted | 1 trade · WR 0% · -$0.92 |

**Causa raiz confirmada:** `squeeze_failed` = novo `max_hold`. Bot entrava no setup (OI+LSR) antes do CVD confirmar agressão real. CVD explodia nos 5m após a saída nos 10 squeeze_failed. Fix aplicado: gate `cvd_not_confirming`.

**Descoberta — trades_1m inverteu como preditor:**
- Sessão anterior: winners 95/min · losers 58/min
- Esta sessão: winners 50/min · losers 96/min
- Conclusão: preditor não confiável com amostra < 50 trades

---

## ⏳ Pendências — próximos passos

### 🔴 CRÍTICO — próxima sessão
- [ ] **Verificar liquidações ao vivo** — confirmar `liq_short_1m > 0` após fix `!forceOrder@arr`. Se ainda zero, investigar conexão WebSocket no log de runtime
- [ ] **Kelly floor** — verificar se guard `min($20, capital×10%)` está funcionando. 3 winners saíram com margem $13 (kelly=0.001–0.017 bypassando o floor)

### 🟡 Alta prioridade — Sprint 3
- [ ] **Filtro de divergência temporal** — modo standby quando EXP_BTC:1m negativo mas 15m/1h forte (Sprint 2D)
- [ ] **Correlation Guard expandido** — cobrir 100+ símbolos além dos 15 atuais
- [ ] **Score multiframe** — `ema_trend:15m` e `ema_trend:1h` em `calculate_fit_score()`

### 🟢 Backlog — Sprint 3+
- [ ] **Liquidity Guard** — validar profundidade OB antes de entrar
- [ ] **50+ trades paper** — validação estatística antes do LIVE
- [ ] **Dry-run live** — `auto_pilot: false` por 24h

---

## 📈 KPIs mínimos para GO ao LIVE

| Métrica | Target |
|---------|--------|
| Trades coletados | ≥ 50 |
| Win Rate | ≥ 60% |
| Profit Factor | ≥ 1.5 |
| Max Drawdown | ≤ 12% |
| Captura MFE | ≥ 50% |
| Loss máximo por trade | ≤ 8% |

---

## 🧬 Análise dos trades (histórico)

### Sessão 02/06/2026 — 17 trades
- Win Rate: 82.35% (14W/3L) · PnL: +$0.07 · Problema: fees comendo lucro, trailing saindo cedo

### Sessão 03/06/2026 — 40 trades
- Win Rate: 42.5% (17W/23L) · PnL: -$1.74 · Causa: 13 max_hold com MFE=0 (52% do prejuízo)
- Fix aplicado: mae_guard + squeeze_aborted eliminam max_hold

### Sessão 04/06/2026 — 18 trades
- Win Rate: 27.8% (5/18) · PnL: -$6.45 · Causa: squeeze_failed = novo max_hold (CVD não confirmado)
- Fix aplicado: gate cvd_not_confirming + !forceOrder@arr + signal dict completo

---

## 💡 Insights acumulados

1. **A estratégia tem edge comprovado** — quando o sinal está certo (MAE baixo imediatamente), os ganhos são expressivos: +12%, +8%, +5.6%
2. **Cada sessão tem um padrão de falha dominante** — max_hold → squeeze_failed → próximo a identificar com liquidações funcionando
3. **Score alto não garante direção** — scores 96–100 geraram losses com MFE=0. O score precisa incorporar confirmação de momentum, não só confluência estática
4. **Filtro de divergência temporal é a próxima evolução crítica** — EXP_BTC:1m negativo com 15m/1h positivos = ativo em compressão. Entrar após o 1m alinhar é entrada de qualidade máxima
5. **Liquidações em massa são diferencial crítico** — 35pts potenciais no score estavam cegos. Fix !forceOrder@arr pode mudar o WR significativamente na próxima sessão
6. **trades_1m como preditor não é confiável com < 50 trades** — Forge estava certo em pedir amostra maior antes de alterar o score
7. **Mercado de sangue é o cenário ideal para o SS** — quando BTC cai e altcoins desacoplam, há liquidações em cascata todos os dias

---

## 🛠️ Scripts de análise disponíveis

```bash
python src/analyze_session_quick.py      # snapshot rápido após sessão
python src/analyze_leaks.py              # métricas de captura
python src/audit_deep_dive.py            # auditoria completa
python src/audit_ghost_outcomes.py       # validar filtros de recusa
python src/deep_performance_audit.py     # tiers de score
python src/audit_intelligence_advanced.py
```

---

*Versão: 3.0 · Última atualização: 04/06/2026*
