# BRAIN_CONTEXT.md — Squeeze Sniper
> Contexto estratégico para o agente Brain retomar no Claude Code (Antigravity).
> Forge é guardião deste arquivo — atualiza a cada sprint.
> Versão: 1.0 · 09/06/2026

---

## 1. O Projeto em Uma Frase

Bot de trading algorítmico LONG ONLY em Binance Futures USDM que captura **long squeezes** — colapsos de liquidação institucional em altcoins que geram momentum explosivo de alta.

---

## 2. Estado Atual do Sistema

| Dimensão | Estado |
|----------|--------|
| Modo | **Paper trading ativo** |
| Capital simulado | $1.000 USDT |
| Leverage | 10× |
| Posições máximas | 20 simultâneas |
| Score mínimo entrada | 90/100 |
| Exchange | Binance Futures USDM |
| Repositório privado | `vjdoreto/squeeze-sniper` |
| Repositório público (Brain) | `vjdoreto/squeeze-sniper-brain` |

---

## 3. Padrões Confirmados com Evidência

### ✅ Padrões que funcionam (winners)
- **EXP_BTC positivo + OI crescendo + LSR caindo** = tríade de entrada institucional
- **liq_cascade = True** = confirmação de colapso real → bypass de vários gates + bônus +20 no score
- **CVD crescendo > 1.5% em 5m** = pressão compradora líquida confirmada
- **EMA:4h ≥ 0** = macro favorável → winners majoritários nessa condição
- **RSI:5m entre 40–55** = zona de ignição (BANANAS31 +17% com RSI=48 — bloqueado erroneamente até 09/06)
- **Trades:1m ≥ 10 + OI trend ≥ 0.008 + LSR trend ≤ -0.3** = gate combo EA-Sprint3 discrimina bem

### ❌ Padrões de losers confirmados
- **EMA:4h ≤ -4** = macro bearish → WAXPUSDT EMA:4h=-6 entrou e saiu -16.93%
- **max_hold disparando** = bot entrou cedo demais, ativo não moveu
- **MFE = 0 imediato** = entrada prematura (EXP_BTC:1m fraco enquanto 15m/1h forte)
- **volume_quality_spike ≥ 2.0** = CVD explodindo APÓS a squeeze, não durante

---

## 4. Decisões Estratégicas Tomadas (com evidência)

| Decisão | Evidência | Data |
|---------|-----------|------|
| Gate combo (trades/oi/lsr) hardcoded | EA-Sprint3: discriminação 78%+ winners | 05/06 |
| min_rsi_5m paper: 60 → 45 | BANANAS31 +17% bloqueado com RSI=48 | 09/06 |
| mae_guard_late mfe threshold: 2% → 3% | BBUSDT MFE=2.98% escapou, -15.92% | 08/06 |
| ema_4h_bearish AND removido | WAXPUSDT norm_1h=+1.378 → gate nunca disparou | 09/06 |
| liq_threshold proporcional ao OI | threshold fixo $500k impossível p/ altcoins $3-5M OI | 08/06 |
| futures_multiplex_socket | F-12 causa raiz: stream spot nunca entregava eventos | 09/06 |

---

## 5. Estado do DNA — Gates Ativos

Veja `SQUEEZE_SNIPER_DNA.md` para lista completa. Destaques críticos:

- **F-13** `rsi_1h_warmup`: bloqueia entrada se rsi:1h = 50.0 artificial (uptime < 600s)
- **F-14** `mae_guard_late`: sai se duration ≥ 240s E pnl < -3% E mfe < 3%
- **F-15** `volume_quality_spike`: bloqueia se cvd_change_pct/(trades_1m+1) ≥ 2.0
- **F-18** `ema_4h_bearish`: bloqueia se ema_trend:4h ≤ -4 (sozinho — AND removido)

**Sequência de saída:** squeeze_failed(90s) → squeeze_aborted(120s) → mae_guard(120s) → mae_guard_late(240s) → trailing(180s+) → max_hold(480s)

---

## 6. O Que Está Pendente de Validação

### Alta prioridade — aguardando primeiros trades com sistema limpo
- [ ] `liq_short_1m_stable` e `liq_cascade` com dados reais (F-12 corrigido em 09/06 — era endpoint Spot, corrigido para Futures)
- [ ] `ema_trend_4h` no signal dict (corrigido 09/06 — não estava sendo exportado)
- [ ] `rsi:1h` real pós-cache quente (corrigido 09/06 — não recalculava após load)
- [ ] Gate `ema_4h_bearish` disparando de fato em losers (auditar via `signal_refusals.jsonl`)

### Backlog estratégico (Brain define prioridade)
- [ ] **Gate momentum sub-minuto** — ring buffers 10s/20s/30s AggTrade
- [ ] **Macro CMC** — USDT.D + BTC.D + Fear&Greed polling 5min
- [ ] **Filtro divergência temporal** — STANDBY quando EXP_BTC:1m < 0 mas 15m/1h forte
- [ ] **Filtro multiframe no score** — ema_trend:15m e ema_trend:1h no Squeezometer
- [ ] **50+ trades paper** — threshold para validação estatística GO/LIVE

---

## 7. Protocolo Brain → Forge

1. Brain escreve demanda em `tasks.md` com: descrição + evidência nos logs + campo exato
2. Forge executa, commita com arquivo:linha alterado, marca done em `tasks.md`
3. Forge atualiza `context.md` + `SQUEEZE_SNIPER_DNA.md` se houve mutação do DNA
4. Forge commita `context.md` nos dois repos ao final de cada sprint
5. Brain nunca toca código — consulta DNA, não edita

**R-01:** Forge investiga antes de implementar qualquer sugestão do Brain que contradiga o código conhecido.
**R-02:** Mutações de parâmetros do DNA requerem evidência explícita + autorização de Bob Doreto.

---

*BRAIN_CONTEXT.md v1.0 · Forge é guardião · 09/06/2026*
