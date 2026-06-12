# BRAIN_CONTEXT.md — Squeeze Sniper
> Contexto estratégico para o agente Brain retomar no Claude Code (Antigravity).
> Forge é guardião deste arquivo — atualiza a cada sprint.
> Versão: 1.1 · 10/06/2026

> ⚠️ **AVISO R-07 — 11/06/2026:** Brain executou `git commit acf986c` diretamente ("commit de governança"). Isso é violação R-07 independente do tipo de arquivo. Não existe categoria de commit que autorize Brain a executar `git commit`. O fluxo é sempre: escrever conteúdo em `tasks.md` → Forge lê e commita. Próxima violação será escalada para Doreto com pedido de revisão do protocolo de boot do agente.

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
| Score mínimo entrada | **85/100** (reduzido 10/06) |
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
- **lsr_trend_positive com liq>$20k + trades≥15 + cvd>2.0** = padrão B-34 demand breakout — bypass ativo desde 10/06

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
| **min_score 90→85** | Score max=88; 25.307 rejeições; 0 trades em 6h. KATUSDT 17× bloqueado | 10/06 |
| **B-liq-cascade-tiers** | 0.02×OI → floor $100k p/ OI $5M → cascade impossível. Tiers por OI desbloqueiam | 10/06 |
| **B-34-bypass** | VELVETUSDT $69k liq bloqueado pelo gate lsr_trend_positive antes do score | 10/06 |
| **ema_trend:1h +5 pts bônus** | BEAT 4h=+6/1h=+6/5m=0 invisível ao score anterior — pullback em tendência | 10/06 |
| **funding_rate no ghost signal dict** | Campo ausente do `_write_ghost_signal` — T-06 era inauditável nos logs históricos. Paridade com sinal real restaurada | 11/06 |
| **ema_trend_1h no signal dict** | Campo ausente dos dois blocos de signal_engine.py — bônus +5 pts existia em market_view.py mas não era exportado. Brain pode agora auditar ema_trend_1h × MFE após 30+ trades | 11/06 |
| **Caso AIOUSDT +29% — miss por design** | Demand ramp orgânica (CVD+OI+FR escalando por horas) ≠ squeeze de liquidação. DNA funcionou corretamente para o padrão que foi projetado. Demand ramp = backlog estratégico pós-50 trades | 11/06 |
| **fix(B-34-bypass) — 5 gates LSR não checavam bypass** | `lsr_bypass_active=True` ignorava só o gate `lsr_trend_positive`. Quatro gates downstream bloqueavam de qualquer forma. Evidência: WLDUSDT liq=$23.5k/trades=345/cvd=15.88 — bypass logado 20× mas sem entrada. `a2d1410`. | 11/06 |
| **D3 `liq_required_no_cascade`** | Gate: sem cascade E liq≤$500 → recusa. 6/7 squeeze_failed tinham liq=0. CVD puro = demand ramp. `signal_engine.py:688` · `6d9554d` | 11/06 |
| **D4 bônus ema_trend_1h removido** | ema1h≥2 dava +5pts. ema1h=+6 WR=0% n=8. Campo no signal dict preservado. `market_view.py:102` · `6d9554d` | 11/06 |
| **D6 `overextension_double`** | Gate: ema4h≥6 AND ema1h≥6 → recusa. n=3 WR=0%. `signal_engine.py:699` · `6d9554d` | 11/06 |
| **D7 `lsr_multiframe_divergence`** | Gate: lsr:5m>0 AND lsr:1h>-0.5 → recusa. lsr_trend:1h confirmado em metric_engine.py:63. `signal_engine.py:707` · `6d9554d` | 11/06 |
| **Bug simétrico F-12: klines + CVD vinham do Spot** | `_listen_klines` e `_listen_agg_trades` usavam `multiplex_socket` (Spot) — bug idêntico ao F-12. CVD e RSI de todos os trades anteriores ao restart são inválidos | 10/06 |
| **queue_size=10000 + max_queue_size** | Overflow silencioso em spikes de volume — parâmetro correto da biblioteca | 10/06 |
| **D1: funding_rate no signal dict real** | Campo ausente de `signals.jsonl` e `paper_closed.jsonl` — T-06 inauditável nos trades reais. **Validado:** SQDUSDT `funding_rate=0.00005` no primeiro signal pós-restart | 11/06 |
| **F-19: _post_trade_pending reconstruído no boot** | Alpha decay 4h/12h/24h perdido a cada restart. `_rebuild_post_trade_pending()` reinsere trades das últimas 24h com snapshots incompletos | 11/06 |
| **Telegram: paper_reset + hard_reset + mode_change alerts** | Alertas ausentes para eventos críticos de controle. `telegram_alert.py` + `main.py` · `665244c` + `dfe080d` · 11/06 |
| **Squeezometer warming cooldown 900s → 300s** | Warming (70–85) agora com mesmo cooldown do panic (5min). Evita spam em mercado oscilante. `main.py:436` · `665244c` · 11/06 |

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
- [x] `liq_short_1m_stable` e `liq_cascade` com dados reais — **CONFIRMADO 09/06 21:27:47** (TRUMPUSDT $438, BTWUSDT $6090 — pipeline funcional)
- [x] `ema_trend_4h` no signal dict — **CONFIRMADO 09/06** (fix candles 100→50, commit `c7edbf8`)
- [x] `rsi:1h` real pós-cache quente — **CONFIRMADO 09/06** (gate rsi_1h_warmup não aparece no top-5 após 2º boot)
- [x] **CVD e klines de Futuros** — **CONFIRMADO 10/06** (`fde21af`). Bug simétrico ao F-12 corrigido: `_listen_klines` + `_listen_agg_trades` agora usam `futures_multiplex_socket`. Todos os trades anteriores a essa sessão têm CVD e RSI calculados com dados do Spot — histórico invalidado para T-01/T-02/T-03.
- [ ] Gate `ema_4h_bearish` disparando de fato em losers (auditar via `signal_refusals.jsonl` — aguarda 50+ trades)
- [ ] `liq_cascade` (boolean) gerando entradas de qualidade — aguarda amostras com liq_short_1m ativo
- [ ] **B-34-bypass WR** — bypass agora funcional (`a2d1410` corrigiu 5 gates que ignoravam `lsr_bypass_active`). Após 20+ trades com `lsr_bypass_active=True` + entrada real, Brain audita WR. WR < 50% → reverter
- [ ] **T-06 FR × MFE** — `funding_rate` agora presente nos ghost signals (T-09 · `4ffd73f`). Auditar após 30+ trades: FR > +0.0015 + EMA:4h≥0 + OI crescendo → MFE médio mais alto?
- [ ] **T-08 ema4h bypass virada** — logging enriquecido ativo (`4332d36`). Aguardando ~50 eventos `ema_4h_bearish` pós-restart para auditar falso positivo rate → go/no-go Passo 2
- [ ] **T-05 range_level × MFE** — backlog pós-50 trades. Hipótese: range_level:1h ≥ 3 + entrada = MFE médio 1.5× maior
- [ ] **T-06 FR × MFE** — FR > +0.001 em ativo com ema_trend:4h ≥ 0 + OI crescendo = squeeze iminente. Validar em 30+ trades com `funding_rate` nos logs

### Teses novas registradas (10/06/2026 · ARIA)
- **T-05:** range_level:1h ≥ 4 + ema_trend:4h ≥ 0 + exp_btc:1h > 5 → squeeze com MFE mais alto (energia represada). Campo range_level não está no pipeline SS hoje — backlog pós-50 trades.
- **T-06:** FR > +0.001 em ativo com ema_trend:4h ≥ 0 + OI crescendo = curto-circuito de short squeeze iminente. `funding_rate` já está no signal dict via `market_view.py:266` — ARIA pode auditar imediatamente nos próximos trades.

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

| **E1 — bypass `oi_trend_too_weak` para liq_cascade** | 46 ghosts HUSDT/ESPORTSUSDT (score 92–100) bloqueados com cascade real ativa — OI cai durante liquidação por design | 12/06 |
| **E2 — bypass `lsr_trend_not_negative` para liq_cascade** | 10 ghosts HUSDT (score 96) com liq=$17-18k bloqueados por lsr fraco — cascade é evidência mais forte que lsr_trend | 12/06 |
| **E3 — min_score paper 80 → 78** | Teto empírico = 78 em 3.757 refusals score_below_threshold — threshold 80 matematicamente inatingível | 12/06 |

*BRAIN_CONTEXT.md v1.9 · Forge é guardião · 12/06/2026 — E1/E2/E3 implementados (`aa5d2ee`, `b6730c7`). Gates oi_trend_too_weak e lsr_trend_not_negative agora bypassam liq_cascade=True. min_score 80→78. Soft restart necessário.*
