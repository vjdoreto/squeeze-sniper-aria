# BRAIN_CONTEXT.md — Squeeze Sniper
> Contexto estratégico para o agente Brain retomar no Claude Code (Antigravity).
> Forge é guardião deste arquivo — atualiza a cada sprint.
> Versão: 2.5 · 13/06/2026

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
| **D-URGENTE-1: SL fill no sl_price, não no tick** | 2-confirmações causava fill no 2º tick (já mais baixo). Slippage artificial 1-1.3% = 10-13% PnL extra perdido/SL. ESPORTS -43% (esperado -30%), ENJ -34% (esperado -30%). `paper_tracker.py` · `7ebc3b8` · 12/06 |
| **D-HIGH-1: CVD floor -10% mesmo com cascade** | cascade=True não pode ser passe livre para CVD negativo. ENJ 12:52 cvd=-0.56%+cascade→-34%; ENJ 13:59 cvd=+29%+cascade→+31%. Gate cvd_negative_cascade_entry. `signal_engine.py` · `d256018` · 12/06 |
| **D-MEDIUM-2: CVD saturado ≥950 bloqueia** | CVD=999.9 (TIA) e 826.9 (RIF) → squeeze_failed imediato, MFE=0. Dado saturado não discrimina. Gate cvd_data_saturated. `signal_engine.py` · `d256018` · 12/06 |
| **D-HIGH-2: Throttle 4h após stop_loss hit** | ESPORTS -43% voltou a entrar 108min depois (cooldown 1h insuficiente). extend_cooldown() no SymbolThrottler define 4h bloqueio. `risk_manager.py` + `main.py` · `d2eac09` · 12/06 |
| **cvd_negative_quarantine (documentação)** | Gate Sprint 3 renomeado. Ativa quando cvd_delta_1m<0 AND NOT compensação AND is_high_quality=False. is_high_quality=True quando liq_cascade=True — por isso cascade bypassa. `signal_engine.py:452-480`. 5.916 bloqueios/dia = 2º maior gate. Brain deve monitorar distribuição. |
| **large caps bloqueadas em final_gate_fail com cascade=True — CORRETO** | BTC/ETH/DOGE: exp < final_min_exp mesmo com cascade. SUI $14.4k liq e XRP $168k liq hoje = zero movimento (large caps absorvem liq). EXP gate é proteção estrutural. SS não opera em large caps por design. | 

---

## 5. Estado do DNA — Gates Ativos

Veja `SQUEEZE_SNIPER_DNA.md` para lista completa. Destaques críticos:

- **F-13** `rsi_1h_warmup`: bloqueia entrada se rsi:1h = 50.0 artificial (uptime < 600s)
- **F-14** `mae_guard_late`: sai se duration ≥ 240s E pnl < -3% E mfe < 3%
- **F-15** `volume_quality_spike`: bloqueia se cvd_change_pct/(trades_1m+1) ≥ 2.0
- **F-18 + D-E1** `ema_4h_bearish`: bloqueia se ema_trend:4h ≤ **-2** (estendido de -4 em 13/06 · commit `1e715e5`)

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
| **Fix A — `min_oi_accel` 0.0 → -0.05** | 50 ghost signals CATIUSDT (score=100, CVD=19.76%, cvd_streak=7) bloqueados por `oi_accel=-0.014` vs threshold `0.0`. Ruído de OI flat derrubava DNA clássico do SS. `817785c` | 12/06 |
| **E1/E2 propagados ao gate final** | Bypass de cascade não cobria o gate final (`signal_engine.py:947`). LABUSDT-type com cascade continuava bloqueado. `d0ea407` | 12/06 |
| **Fix B (F-18 cascade bypass) — PENDENTE** | XLMUSDT score=93, liq=$10k, cascade=True bloqueado por ema_4h=-4. Decisão adiada para após WR de 20+ trades com Fix A + E1/E2 propagados. | 12/06 |
| **E1/E2 gate final — bypass propagado para L947** | E1/E2 bypassavam gates individuais (L787/L797) mas não o gate final (L947). LABUSDT cascade=True, liq=$10k, score=93, 142t/m bloqueado por oi_trend=0.004 < 0.015 apesar de E1 ativo. Fix: `liq_cascade or (oi_trend >= threshold)` em L949-950. `d0ea407` | 12/06 |
| **Diagnóstico score teto 77 — manter min_score=78** | 1.040 refusals score 75-77: 89% com liq=0 via cascade bypass (evento dissipado), 60% dos 60 com liq real têm LSR positivo (demand breakout). Zero candidatos com LSR < -0.3. Baixar threshold capturaria ruído. Premissa Brain (D3 garantia liq>$500) incorreta — cascade bypassa D3. | 12/06 |
| **D-URGENTE-1 — SL fill no sl_price target** | stop_loss executava no tick atual (preço pós-confirmação), não no SL target. Em altcoins ilíquidas: 1-1.3% de slippage extra = 10-13% de PnL perdido a mais por SL hit. ESPORTS -43% (esperado -30%), ENJ -34% (esperado -30%). Fix: `exit_price = sl` quando `exit_reason == stop_loss`. `paper_tracker.py` · `7ebc3b8` | 12/06 |
| **D-HIGH-1 — CVD floor -10% mesmo com cascade** | cascade=True tornava is_high_quality=True → bypassava cvd_negative_quarantine completamente. ENJ 12:52 entrou com CVD=-0.56% + cascade → -34%. ENJ 13:59 com CVD=+29% + cascade → +31%. Gate `cvd_negative_cascade_entry`: bloqueia quando cascade=True AND cvd < -10%. `signal_engine.py` · `d256018` | 12/06 |
| **D-HIGH-2 — Throttle 4h após stop_loss hit** | ESPORTS deu SL -43% às 09:52 e voltou a entrar 108min depois (dentro do throttle normal de 1h). Após stop_loss hit, cooldown estendido para 4h. `paper_tracker.py` · `d2eac09` | 12/06 |
| **D-MEDIUM-2 — CVD ≥ 950 bloqueia (dado saturado)** | TIA entrou com CVD=999.9 → squeeze_failed, MFE=0. RIF com CVD=826.9 → squeeze_failed, MFE=0. CVD capeado não discrimina momentum real. Gate `cvd_data_saturated`: bloqueia quando cvd_change_pct ≥ 950. `signal_engine.py` · `d256018` | 12/06 |
| **BTC/ETH bloqueados no gate final com cascade — CORRETO por design** | final_gate_fail em large caps (BTC 43x, ETH 22x) com cascade=True é comportamento esperado. EXP gate bloqueia porque large caps absorvem liquidação sem movimento. SUI $14.4k liq e XRP $168k liq = zero movimento pós-saída. SS não opera em large caps — EXP gate é proteção estrutural permanente. | 12/06 |
| **cvd_negative_quarantine — documentação** | Gate existente desde Sprint 3 (signal_engine.py:452-480). 5.916 bloqueios/dia = segundo maior gate. Bloqueia cvd_delta_1m < 0 quando is_high_quality=False. cascade=True → is_high_quality=True → bypassa. Vulnerabilidade resolvida por D-HIGH-1 (CVD floor). Não confundir com bug — é gate funcional. | 12/06 |

| **E3-gate-final — oi_accel bypass cascade no gate final** | ORCA oi_accel=-0.067 e XPL oi_accel=-0.055 com cascade=True bloqueados no gate final. Durante cascade, OI cai por liquidações — oi_accel negativo é consequência mecânica, não fraqueza. Mesma lógica E1/E2. `signal_engine.py:966` · `4129488` | 12/06 |
| **cvd_streak NÃO bypassa cascade — decisão permanente** | LAB bloqueado com streak=0 + cascade=True. Argumento para bypass: cascade confirma liquidação real. Argumento contra: streak=0 = CVD positivo isolado sem continuidade — exatamente o perfil squeeze_failed. Brain + Forge consenso: não bypassar. Stride é última linha de defesa de qualidade de CVD. | 12/06 |
| **cvd_streak adicionado ao ghost signal dict** | Campo ausente de todos os 1553 ghost signals — zero diagnóstico de streak possível. Adicionado como campo observacional. Gate continua lendo de `self._cvd_streak[symbol]` diretamente. `signal_engine.py` · `4129488` | 12/06 |
| **Hard Reset Paper executado** | Estado operacional zerado (risk_state, paper_opportunities, throttle_state deletados). Logs históricos preservados (paper_closed, metric_state, signals, ghosts). Soft restart aplicado. Coleta limpa iniciada com DNA novo (7 fixes ativos). | 12/06 |
| **E1/E2 gaps nos ghosts — HISTÓRICOS, não gap atual** | 37 casos E1 e 10 casos E2 com cascade=True em ghost_signals eram de 22:58 (11/06) e 00:44 (12/06) — anteriores ao restart que carregou o fix. Zero ocorrências pós-restart. ghost_signals.jsonl acumula desde o boot anterior — sempre verificar timestamps antes de diagnosticar gap. | 12/06 |
| **BTC/ETH/DOGE final_gate_fail com cascade — CORRETO** | Large caps bloqueados por exp baixo no gate final. SUI $14.4k liq e XRP $168k liq tiveram zero movimento (post4h: -2.1% e -1.8%). SS não opera em large caps — EXP gate é proteção estrutural permanente. Decisão: não bypassar exp para cascade. | 12/06 |
| **D-E1 — gate ema_4h_bearish estendido ≤ -4 → ≤ -2** | n=5 trades com ema4h=-2, WR=0%, sem exceção em 2 sessões. F-18 dificulta mas não bloqueava ema4h=-2. Uma linha: threshold -4 → -2. reason_code ema_4h_bearish existente. Critério reversão: winner com ema4h=-2 em 5+ trades. `signal_engine.py:839` · `1e715e5` | 13/06 |
| **D-E2 — gate cascade_micro_liq** | cascade=True com liq_short_1m_stable < $1000 = micro-aceleração, não colapso institucional. n=4 losers (MEUSDT $471, COAIUSDT $468, LABUSDT $41, TAOUSDT $320) -$13.65. Gate recusa antes do bloco relax_factor — limpo, sem reatribuição de variável. `signal_engine.py:715` · `1e715e5` | 13/06 |
| **PaperAnalyzer auto-apply DESABILITADO** | PA rodava a cada hora e sobrescrevia preferences.json: reinserindo blacklist (OPGUSDT/TAOUSDT/XRPUSDT) e revertendo min_rsi_5m 45→60 silenciosamente. Commit `7121fe4`. preferences.suggested.json continua sendo escrito — Brain pode ler como sinal, nunca auto-aplicar. Trades confiáveis são APENAS os pós-restart 13/06. | 13/06 |
| **preferences.suggested.json — protocolo Brain** | Brain lê no boot de cada sessão como dado adicional. Se símbolo aparecer com WR<30% em 2+ trades → Brain cruza com logs antes de propor qualquer gate. Nunca auto-aplicar. | 13/06 |

---

## 8. DNA Freeze — Ativo desde 12/06/2026

**Regra:** nenhum gate novo, nenhuma mutação de parâmetro até 50 trades fechados com o DNA de 12/06.

**Baseline do freeze:** Hard Reset Paper ~20:25 BRT · 12/06/2026. Contar trades em `paper_closed.jsonl` com entry.timestamp posterior a esse horário.

**Exceções já executadas (não reabrir):**
- B-49 Opção A: silence_window 21:05 → 21:30 BRT · `signal_engine.py:314` · `d594966`
- F-19: `_post_trade_pending` reconstruction — já estava implementado (`e451f19`), soft restart ativou. Log esperado: "F-19: X trade(s) reinseridos" no próximo boot com trades recentes.

**O que Brain monitora até 50 trades:**
- WR geral — baseline esperado > 50%
- Fix A: WR trades com `oi_accel` entre -0.05 e 0.0 — reversão se WR < 45% em 20+
- B-34 bypass: WR trades com `lsr_bypass_active=True` — reversão se WR < 50% em 20+
- D-HIGH-1: nenhum winner legítimo bloqueado por `cvd_negative_cascade_entry`
- Alpha decay 4h/12h/24h completo aparecendo em `paper_closed.jsonl` pós-F-19

**Fix B (F-18 bypass cascade para ema4h=-4):** aguarda WR de 20+ trades com Fix A ativo. Brain decide após análise. Nota: D-E1 estendeu o bloqueio para ema4h≤-2 — Fix B (bypass cascade) seria somente em ema4h=-4 que agora não é mais alcançável sem revisão do critério.

**D-E3 (ema1h=6 + ema4h≤2 bloqueante):** monitoramento ativo. Após 20+ trades limpos pós-restart 13/06, Brain verifica se ema1h≥4+ema4h≤2 persiste com WR<35%. Se sim → formaliza com evidência para Forge.

**Dados confiáveis para análise:** apenas trades coletados após restart dos commits `bc4093f` + `7121fe4` + `1e715e5` (13/06/2026). Trades anteriores foram coletados com PaperAnalyzer potencialmente corrompendo o DNA — são suspeitos para teses que dependem de DNA específico.

| **Throttle max_hold (8ª sessão)** | RIFUSDT -24% max_hold → voltou 1.5h depois → -20.79% stop_loss = -44% mesmo símbolo. Bug: `extend_cooldown()` só disparava em stop_loss. Fix: `main.py:442` → `in ("stop_loss", "max_hold")`. `95c1cfa` | 13/06 |
| **D-E4 cancelado (8ª sessão)** | Brain propôs gate ema1h==0 bloqueante. Forge derrubou: ema1h=0 tem 4 winners históricos incluindo ESPORTSUSDT +96%. Discriminador real é liq, não ema1h. D-E2 já cobre o subgrupo perigoso (cascade + liq<$1k). | 13/06 |
| **B-60 — ema1h=6 dreno estrutural** | n=36 trades, WR=33%, PnL=-159% acumulado. overextension_double (D6) só cobre ema4h=6 AND ema1h=6. ema4h≤4 + ema1h=6 passa livre. Análise após 30 trades do Freeze. | 13/06 |
| **LSR paradoxo confirmado** | Losers têm LSR trend médio -0.213 vs winners -0.024. cascade + LSR muito negativo + liq baixa = absorção institucional, não squeeze. Sinal de armadilha, não força. Monitorar com mais dados. | 13/06 |
| **DNA Freeze v2 — 30 trades** | Baseline: restart pós-commit `95c1cfa` · 13/06 noite. Monitorar: squeeze_failed % (> 25% → B-55), ema1h=6 WR, throttle confirmação. | 13/06 |

---

## 8. DNA Freeze v2 — Ativo desde 13/06/2026 · 8ª sessão

**Regra:** nenhum gate novo, nenhuma mutação de parâmetro até **30 trades fechados** pós-restart `95c1cfa`.

**Baseline:** restart após commit `95c1cfa` · 13/06/2026 noite.

**O que Brain monitora:**
- **squeeze_failed %** — se > 25% → problema é timing → B-55 (ring buffers sub-minuto) é próxima sprint
- **ema1h=6 WR** — n=36 histórico, WR=33%, -159% PnL. Padrão persiste?
- **throttle max_hold** — confirmar log de ativação
- **ema1h=0** — D-E4 cancelado. Mas monitorar: se ema1h=0 + cascade=False persistir com WR=0% em 10+ trades → revisar com nova evidência

**Diagnóstico do círculo (confirmado 8ª sessão):** adicionamos gates de seleção para um problema de timing. squeeze_failed com MFE=0 = bot entrou no setup certo mas o squeeze não confirmou em 90s. Nenhum gate de entrada resolve isso. B-55 (ring buffers 10s/20s/30s confirmando que o preço JÁ está subindo antes de entrar) é o ponto de saída do círculo.

| **Throttle D-HIGH-2 inoperante desde 12/06 — fix bbad06e** | Dois bugs no mesmo bloco main.py ~L432: (1) batch — só `history[-1]` lido quando múltiplos fecham juntos; (2) symbol field — lido de `entry.symbol` (inexistente) em vez de `trade["symbol"]` (raiz) → `last_symbol=""` sempre → `extend_cooldown` nunca chamado. Evidência direta: VELVET SL 05:05 → re-entry 08:01 (-8.5% evitável). Fix: iteração de todos os trades novos + campo correto. `main.py` · `bbad06e` · 14/06 |
| **squeeze_failed = 44% em 9 trades limpos** | Análise profunda 14/06: 4/9 squeeze_failed com MFE=0 em 90s exatos. Padrão confirma diagnóstico Sprint 8: timing problem, não seleção. Nenhum gate resolve. B-55 (ring buffers 10s/20s/30s) confirmado como próxima sprint pós-Freeze. | 14/06 |

*BRAIN_CONTEXT.md v2.7 · Forge é guardião · 14/06/2026 — Sessão 10ª: análise profunda 9 trades (WR 22%) · throttle D-HIGH-2 bug duplo confirmado e corrigido (bbad06e) · squeeze_failed=44% confirma B-55 como próxima sprint · DNA Freeze v2 continua (30 trades).*
