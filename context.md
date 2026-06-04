# Squeeze Sniper — Contexto Mestre
> **Versão:** 2.6 · **Data:** 03/06/2026  
> ⚠️ **PENDENTE ATUALIZAÇÃO:** Brain exportará v2.9 na próxima sincronização (após primeira sessão com fixes ativos). O v2.6 cobre tudo até 03/06/2026 22h. Nada bloqueia o trabalho de amanhã.  
> **Uso:** Cole este documento no início de qualquer conversa nova para retomar o projeto sem perder contexto.

---

## Sobre o Projeto

- **Dono:** Doreto (Bob Doreto · vjdoreto@hotmail.com)
- **Projeto:** SqueezeSniper V4 — bot de trading algorítmico
- **Exchange:** Binance Futures (USDM)
- **Estágio:** Paper trading avançado → validação → LIVE
- **Objetivo:** Capturar long squeezes — colapsos de liquidação institucional em futuros da Binance
- **Repositório:** `https://github.com/vjdoreto/squeeze-sniper` (privado)

---

## Estrutura de Sessões

| Sessão | Ambiente | Foco |
|--------|----------|------|
| **Brain** | Claude.ai (trabalho/mobile) | Estratégia, análise de logs, cruzamento de dados, roadmap |
| **Forge** | Laptop pessoal (Antigravity) | Implementação, código, testes, calibrações |

O **context.md** é a ponte entre as duas sessões. Atualizar e compartilhar após cada evolução relevante.

### Protocolo Brain × Forge (ratificado 03/06/2026)

1. Brain escreve em `tasks.md` com evidências nos logs
2. Forge verifica no código antes de implementar — não aceita sugestão sem confirmação
3. Forge marca como concluído com arquivo/linha alterado
4. Forge é guardião exclusivo do código — nenhum agente externo altera diretamente

```text
Hierarquia:
Proprietário (Bob Doreto)
    └── FORGE (implementação exclusiva)
            ├── Brain (análise — insumo, não ordem)
            └── Dados reais dos logs (evidência obrigatória)
```

---

## Estratégia Central

Bot funciona como **sniper de long squeezes**: identifica momento em que shorts alavancados são forçados a fechar (liquidação em cascata), gerando avalanche de compras forçadas.

### DNA do Sniper (hierarquia imutável)

1. `EXP_BTC` — exponencialidade vs BTC (filtro mestre)
2. `OI` — Open Interest (dinheiro novo entrando)
3. `HFT Trades` — validação de agressão real vs ruído
4. `LSR` — Long/Short Ratio (pressão dos shorts)
5. `RSI` — combustível técnico
6. `CVD` — pressão compradora líquida

**Regra de Ouro:** Imutavelmente **LONG ONLY**. Margem **ISOLATED**. Nunca CROSS.

---

## Motor de Score (calculate_fit_score)

| Componente | Pts máx | Campo |
|---|---|---|
| EXP_BTC descolamento 5m | +30 | `exp_btc:5m` |
| CVD % crescimento 5m | +25 | `cvd_change_pct:5m` |
| OI % crescimento 5m | +20 | `oi_change_pct:5m` |
| Cascata de liquidação | +20 | `liq_cascade` |
| LSR % queda 5m | +15 | `lsr_change_pct:5m` |
| EXP momentum 5m | +15 | `exp:5m` |
| Liquidações short 1m | +15 | `liq_short_1m_stable` |
| HFT burst 10s | +10 | `last_trades_10s` |
| OI aceleração 5m | +10 | `oi_accel:5m` |
| EMA trend 5m | +10 | `ema_trend:5m` |
| Range level 5m | +10 | `range_level:5m` |
| RSI 5m | +10 | `rsi:5m` |
| OB Imbalance | +10 | `ob_imbalance` |

> Score mínimo para entrada: **90** (paper e live)  
> Score opera apenas em 5m — sem validação multiframe ainda

---

## Análise de Trades — 03/06/2026 (40 trades)

| Métrica | Valor |
|---|---|
| Total trades | 40 |
| Win Rate | 42.5% (17W / 23L) |
| PnL total | -$1.74 |
| Avg MFE | +5.19% |
| Avg MAE | -6.98% |
| Captura MFE | -24.2% (negativo) |

**Causa raiz:** 13 trades `max_hold` (WR 0%, -$9.15). Sem eles: WR 62.96%, PnL +$7.41.

**Discriminadores de qualidade nos dados:**

| Preditor | Winners | Losers | r_pb |
|---|---|---|---|
| `oi_trend` | 0.018 | 0.013 | +0.131 (único preditor entry válido) |
| `trades_1m` | 95.5/min | 58.2/min | +0.061 (amostra pequena) |
| `score` | 96.4 | 95.7 | ~0 (inútil como preditor) |

---

## Fixes Implementados em 03/06/2026 (Sprint 1 + 1.5)

| Fix | Arquivo | Descrição |
|---|---|---|
| `mae_guard` | `paper_tracker.py`, `live_tracker.py` | Sai em 120s se PnL < -2% e MFE < 1% |
| `squeeze_aborted` | `paper_tracker.py`, `live_tracker.py` | Sai em 120s se PnL < -1.5% e MFE < 0.5% |
| Trailing callback adaptativo | `paper_tracker.py`, `live_tracker.py` | 50% quando MFE ≥ 3%, 75% abaixo |
| Floor margem $20 | `paper_tracker.py` L734 | `min($20, capital × 10%)` |
| `liq_cascade` $5k → $500 | `metric_engine.py` L700 | Threshold reduzido para capturar eventos reais |
| `rsi_5m` + `ob_imbalance` no signal dict | `signal_engine.py` L755-757 | Logging gap corrigido — Brain terá dados nas próximas análises |
| DrawdownManager resetado | `logs/risk_state.json` | `consecutive_losses=0, risk_multiplier=1.0` |
| Paridade paper ↔ live | `live_tracker.py`, `sniper.py` | Todos os gates espelhados |
| Dashboard redesign | `web_dashboard.py` | Logo SVG scope, glassmorphism, anti-flicker WS |
| Backup automático ao encerrar | `main.py`, `backup_session.py` | `create_backup()` + `taskkill /F /T /PID` |
| Git init + estrutura colaboração | `.git/`, `tasks.md`, `reports/` | Commit inicial a8ae357 |

---

## Insights Críticos

1. **Mercado de sangue é o cenário ideal** — quando BTC cai e USDT.D sobe, o dinheiro migra entre altcoins gerando liquidações em cascata. SS não precisa de bull market, precisa de volatilidade.

2. **Filtro de divergência temporal (novo)** — EXP_BTC:1m negativo + 15m/1h forte = ativo em compressão antes da squeeze. Entrar após 1m alinhar = entrada qualidade máxima. Elimina padrão ARUSDT (entrou na hora errada do movimento certo).

3. **MAE alto = entrada prematura** — trades com MAE > 8% logo após entrada quase sempre perdem. Win rate por MAE inicial: < 2% = 78%, < 5% = 61%.

4. **Score alto não garante direção** — scores 96-100 geraram losses com MFE = 0. Score precisa de confirmação de momentum, não só confluência estática.

5. **liq_cascade zerado no dia** — pipeline funcional, mercado estava quieto. Threshold $5k era alto demais, reduzido para $500.

---

## Roadmap Atual

**Versão:** 3.0 · Forge + Brain · `docs/ROADMAP_LIVE_V4.3.0_2026-06-03.md`

| Sprint | Objetivo | Status |
|---|---|---|
| 1 | Validação 40 trades + fixes | ✅ Concluído |
| 1.5 | Correções críticas pré-Sprint 2 | ✅ Concluído |
| 2 | Correlation Guard + margem segurança + MAE gate 60s (condicional) + filtro temporal | 🔜 Próximo |
| 3 | Liquidity Guard | ⏳ |
| 4 | 50+ trades paper + auditoria GO/NO-GO | ⏳ |
| 5 | Dry-run live 24h | ⏳ |
| 6 | Live $0.05 · 3 trades reais | ⏳ |
| 7 | Scale-up $5 → $20 → $50 → $100 | ⏳ |

**KPIs mínimos para GO ao LIVE:** WR ≥ 60% · PF ≥ 1.5 · MaxDD ≤ 12% · MFE ≥ 50% · sem loss > 8% · ≥ 50 trades

---

## Operações do Bot

**Reinicialização:** encerrar graciosamente (CTRL+C ou EXIT no dashboard) → backup automático → kill de processos → reiniciar.

**Reset de sessão:** HARD RESET no dashboard → apaga logs e força novo warmup (300s).

**Verificar antes de cada sessão:** `logs/risk_state.json` → confirmar `risk_multiplier=1.0`.

**Scripts de auditoria:**
```bash
python src/analyze_session_quick.py   # snapshot rápido
python src/analyze_leaks.py           # métricas de captura
python src/audit_deep_dive.py         # auditoria completa
python src/audit_intelligence_advanced.py  # análise estratégica
```

---

## Próxima Ação Imediata

Reiniciar o bot e coletar 20+ trades com os fixes ativos. Passar `analyze_session_quick.py` ao Brain para análise. Se WR > 55% e `mae_guard`/`squeeze_aborted` dominando os exits — Sprint 2 começa.

---

*Versão: 2.6 · 03/06/2026 · Brain × Forge*  
*⚠️ Atualizar para v2.9 na próxima sincronização*
