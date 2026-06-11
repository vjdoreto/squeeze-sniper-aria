# SQUEEZE SNIPER DNA
> **Guardião:** Forge (Antigravity) — atualiza a cada sprint quando o DNA sofrer mutação.  
> **Brain:** consulta, não edita.  
> **Mutações:** requerem autorização expressa de Bob Doreto.  
> **Versão:** 1.4 · 11/06/2026

---

## 1. DNA — Hierarquia de Decisão (Imutável por padrão)

### Regra de Ouro
**LONG ONLY · Margem ISOLATED · Binance Futures USDM**

Nunca abrir SHORT. Nunca usar margem cruzada. O bot é um sniper de colapso institucional — surfa a onda, não a cria.

### 5 Pilares em Ordem de Soberania

| # | Pilar | Métrica Principal | Interpretação |
|---|-------|-------------------|---------------|
| 1 | **Contexto Macro** | `exp_btc:5m` | Ativo descolando do BTC — força relativa real |
| 2 | **Fluxo Institucional** | `oi_change_pct:5m` ↑ + `lsr_change_pct:5m` ↓ | Dinheiro novo + shorts capitulando |
| 3 | **Execução HFT** | `trades_1m` + `cvd_change_pct:5m` | Robôs comprando agressivamente agora |
| 4 | **Liquidações em Massa** | `liq_short_1m_stable` + `liq_cascade` | Confirmação institucional do colapso |
| 5 | **RSI como Combustível** | `rsi:5m` | Momentum técnico — motor, não freio |

### Restrições de Segurança (Hard Rules — não contornar jamais)

| Regra | Descrição |
|-------|-----------|
| `validate_config()` | Protege contra configurações que violam o DNA |
| `DrawdownManager` | Pausa trading se DD ≥ 15% — circuit breaker real |
| `SymbolThrottler` | Máx 1 trade por símbolo por hora |
| Correlation Groups | Máx 1 posição por grupo (L1, DeFi, AI, Meme…) |
| Liquidation Guard | Proibido setar SL abaixo do preço de liquidação |
| Warmup Gate | 300s mínimo de aquecimento antes do primeiro sinal |

---

## 2. Motor de Score — `calculate_fit_score()` · `src/market_view.py`

Score 0–100. Entrada exige `score >= 90` (paper) / `score >= 90` (live).  
Penalidades podem levar a scores negativos — cap em `max(0, min(100, score))`.

| # | Componente | Campo | Pts Máx | Thresholds | Penalidade |
|---|-----------|-------|---------|------------|------------|
| 1 | **EXP_BTC Descolamento** | `exp_btc:5m` | +30 | >0.025→+30 / >0.012→+20 / >0.005→+10 | <-0.015→-15 / <-0.005→-8 |
| 2 | **CVD % Crescimento** | `cvd_change_pct:5m` | +25 | >100%→+25 / >50%→+20 / >20%→+15 / >10%→+10 / >0→+5 | <-20%→-10 |
| 3 | **OI % Crescimento** | `oi_change_pct:5m` | +20 | >1.5%→+20 / >0.8%→+15 / >0.2%→+10 / >0→+5 | <-0.5%→-8 |
| 4 | **LSR % Queda** | `lsr_change_pct:5m` | +15 | <-3%→+15 / <-1%→+10 | >+3%→-5 |
| 5 | **EXP Momentum** | `exp:5m` | +15 | >0.06→+15 / >0.03→+10 / >0.01→+5 | — |
| 6 | **Liquidações Short** | `liq_short_1m_stable` | +15 | >$100k→+15 / >$50k→+10 / >$10k→+5 | — |
| 7 | **Liq Cascade Bônus** | `liq_cascade` | +20 | True→+20 | — |
| 8 | **OI Aceleração** | `oi_accel:5m` | +10 | >0.05→+10 / >0.02→+6 / >0→+3 | <-0.05→-5 |
| 9 | **EMA Trend** | `ema_trend:5m` | +10 | ≥5→+10 / ≥3→+5 | ≤-5→-15 |
| 10 | **Range Level** | `range_level:5m` | +10 | ≥4→+10 / ≥2→+5 | — |
| 11 | **RSI** | `rsi:5m` | +10 | >65→+10 / >55→+5 | <45→-10 |
| 12 | **HFT Burst** | `last_trades_10s` vs baseline | +10 | >30 E >2× média→+10 / >15 E >1.3× média→+5 | — |
| 13 | **OB Imbalance** | `ob_imbalance` | +10 | >2.0→+10 / >1.5→+5 | <0.5→-5 |
| 14 | **Funding Rate** | `funding_rate` | +5 | <-0.0001→+5 | >0.0003→-10 |
| 15 | **Entrada Precoce** | `exp:5m` < 0.03 E `oi_change_pct:5m` > 0.5 | +5 | bônus de ignição precoce | — |
| 16 | **Penalidade Tardia** | `price_change:5m` | — | — | >2.0%→-20 / >1.5%→-10 |

**Total teórico máximo:** ~220 pts · **Cap:** 100 · **Entrada mínima:** score ≥ 90

---

## 3. Signal Dict — Campos do Sinal (27 campos)

Fonte: `signal_engine.py` · `_evaluate_signal()` · linha ~870.  
Persistido em `signals.jsonl` e `paper_closed.jsonl → entry.signal`.

| Campo | Tipo | Escala / Unidade | Fonte no Store |
|-------|------|-------------------|----------------|
| `symbol` | str | — | `d["symbol"]` |
| `price` | float | USD | `d["price"]` |
| `exp` | float | ângulo norm. | `d["exp:5m"]` |
| `oi_trend` | float | ângulo norm. | `d["oi_trend:5m"]` |
| `lsr_trend` | float | ângulo norm. | `d["lsr_trend:5m"]` |
| `oi_accel` | float | derivada 2ª | `d["oi_accel:5m"]` |
| `trades_1m` | int | nº trades/min | `d["trades_count_1min"]` |
| `exp_btc` | float | ângulo norm. | `d["exp_btc:5m"]` |
| `cvd_1m` | float | USD delta | `d["volume_delta_1min"]` |
| `liq_short_1m` | float | USD | `d["liq_short_1m_stable"]` |
| `liq_cascade` | bool | — | `d["liq_cascade"]` |
| `trades_10s` | int | nº trades/10s | `d["last_trades_10s"]` |
| `trades_level` | int | 0–4 (spike vs baseline) | `d["trades_level"]` |
| `cvd_change_pct` | float | % crescimento 5m | `d["cvd_change_pct:5m"]` |
| `oi_change_pct` | float | % crescimento 5m | `d["oi_change_pct:5m"]` |
| `lsr_change_pct` | float | % queda 5m | `d["lsr_change_pct:5m"]` |
| `relax_label` | str | NORMAL / RELAXED (CASCADE) / RELAXED (EARLY OI) | lógica interna |
| `cvd_streak` | int | ciclos CVD+ consecutivos | `_cvd_streak[symbol]` |
| `rsi_5m` | float | 0–100 | `d["rsi:5m"]` |
| `rsi_1h` | float | 0–100 (50.0 = warmup artificial) | `d["rsi:1h"]` |
| `ema_trend` | int | -6 a +6 | `d["ema_trend:5m"]` |
| `ob_imbalance` | float | ratio bid/ask | `d["ob_imbalance"]` |
| `range_level` | int | 0–5 (pressão represada) | `d["range_level:5m"]` |
| `score` | int | 0–100 | `calculate_fit_score(d)` |
| `timestamp` | float | unix epoch | `time.time()` |
| `volume_quality` | float | cvd_chg_pct / (trades_1m+1) | calculado inline |
| `exp_btc_norm_1h` | float | Z-score rolling window=14 | `d["exp_btc_norm_1h"]` |
| `ema_trend_1h` | int | -6 a +6 | `d["ema_trend:1h"]` |
| `lsr_bypass_active` | bool | — | lógica B-34 inline |
| `last_4h_candle_age_minutes` | int | 0–240 min | calculado inline |
| `funding_rate` | float | ratio | `d["funding_rate"]` |

> Campo adicional adicionado na abertura do trade: `kelly_risk_applied` (float) · `paper_tracker.py:793`.

---

## 4. Gates Ativos — Lista Completa

Executados em sequência em `_evaluate_signal()` · `src/signal_engine.py`.  
Primeiro gate que falha retorna `None` e registra em `signal_refusals.jsonl`.

### Grupo 1 — Contexto e Cooldown

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `cooldown_active` | uptime desde último sinal < cooldown_seconds (180s paper) | signal_engine.py ~535 |
| `blacklist` | símbolo na lista negra do preferences.json | signal_engine.py ~300 |
| `warmup_gate` | _warmup_samples < _min_warmup (300s equivalente) | signal_engine.py ~320 |

### Grupo 2 — Macro Contexto (P2)

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `p2_btc_dump_gate_fail` | BTC caindo >0.3%/1h E exp_btc:5m < min_exp_btc_for_btc_dump | signal_engine.py ~553 |
| `p2_alt_down_gate` | alt_pc_1h < -4.0% | signal_engine.py ~568 |
| `p2_btcdom_assassin_gate` | btc_pc_1h < -0.5% E btcdom_pc_1h > 0 | signal_engine.py ~578 |

### Grupo 3 — RSI e Momentum (P2)

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `rsi15m_too_high_vs_5m` | RSI_15m - 15 > RSI_5m (ambos não acima de 60) | signal_engine.py ~599 |
| `rsi_lt_min_rsi_5m` | rsi:5m < 45.0 (paper) | signal_engine.py ~608 |
| `rsi_1h_warmup` ⭐ **F-13** | rsi_1h == 50.0 (artificial) E uptime < 600s | signal_engine.py ~531 |

### Grupo 4 — Entrada Tardia e Volume

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `entrada_tardia` | price_change:5m > 2.0% E não liq_cascade | signal_engine.py ~624 |
| `vol_adaptive_gating` | vol_3h_avg / vol_24h < 0.7 | signal_engine.py ~390 |
| `score_below_threshold` | score < 90 (paper) | signal_engine.py ~404 |
| `cvd_abs_lt_min_vol` | abs(cvd_delta_1m) < min_vol_1m | signal_engine.py ~425 |

### Grupo 5 — CVD e Warmup

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `cvd_negative_quarantine` | cvd_delta_1m < 0 E não high_quality E não compensado | signal_engine.py ~454 |
| `warmup_metrics_none` | exp, oi_trend ou lsr_trend são None | signal_engine.py ~472 |
| `cvd_not_confirming` | não liq_cascade E cvd_change_pct < 1.0 (no_cascade) | signal_engine.py ~637 |

### Grupo 6 — Gate Combo EA-Sprint3 (sem bypass por liq_cascade)

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `trades_1m_too_low` | trades_1m < 10 | signal_engine.py ~699 |
| `oi_trend_too_weak` | oi_trend < 0.008 | signal_engine.py ~708 |
| `lsr_trend_not_negative` | lsr_trend > -0.3 | signal_engine.py ~717 |
| `volume_quality_spike` ⭐ **F-15** | cvd_change_pct / (trades_1m+1) >= 2.0 | signal_engine.py ~742 |
| `ema_4h_bearish` ⭐ **F-18** | ema_trend:4h <= -4 (sozinho — AND removido) | signal_engine.py ~753 |

### Grupo 7 — Squeeze Detection (dentro do bloco final)

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `ema_trend_bearish` | ema_trend:5m <= -3 | signal_engine.py ~820 |
| `cvd_negative` | cvd_1m < 0 E não high_quality | signal_engine.py ~828 |
| `lsr_trend_too_weak` | lsr_trend > -0.01 E não high_quality | signal_engine.py ~838 |
| `lsr_change_too_weak` | lsr_change_pct > -0.05 E não high_quality | signal_engine.py ~848 |

### Guards de Saída (paper_tracker.py + live_tracker.py)

| Exit Reason | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `squeeze_failed` | duration ≥ 90s E mfe < 0.3% E mfe ≥ 0 | paper_tracker.py ~1140 |
| `squeeze_aborted` | duration ≥ 120s E pnl < -1.5% E mfe < 0.5% | paper_tracker.py ~1150 |
| `mae_guard` | duration ≥ 120s E pnl < -2.0% E mfe < 1.0% | paper_tracker.py ~1157 |
| `mae_guard_late` ⭐ **F-14** | duration ≥ 240s E pnl < -3.0% E mfe < 3.0% | paper_tracker.py ~1163 |
| `trailing_stop` | price ≤ sl_price E sl ≥ entry_price | paper_tracker.py ~1162 |
| `stop_loss` | price ≤ sl_price | paper_tracker.py ~1167 |
| `take_profit` | price ≥ tp_price | paper_tracker.py ~1168 |
| `max_hold` | duration ≥ 480s (paper) | paper_tracker.py ~1174 |

---

## 5. Histórico de Mutações do DNA

| Data | Mutação | Evidência | Commit |
|------|---------|-----------|--------|
| 03/06/2026 | liq_cascade threshold $5k → $500 | 100% dos eventos filtrados — altcoins nunca atingiam $5k | Sprint 1.5 |
| 03/06/2026 | HFT floor $20 mínimo margem | position sizing caótico $1–$20 na mesma sessão | Sprint 1.5 |
| 03/06/2026 | mae_guard + squeeze_aborted | 13 trades max_hold @481s = -$9.15 (52% do prejuízo) | Sprint 1.5 |
| 03/06/2026 | trailing callback 50%/75% adaptativo | MFE alto sendo devolvido com callback fixo 75% | Sprint 1.5 |
| 04/06/2026 | WebSocket `!forceOrder@arr` global | streams individuais symbol@forceOrder falhavam silenciosamente | `7ac5d45` |
| 04/06/2026 | Gate CVD `cvd_not_confirming` (min 1.0% sem cascade) | squeeze_failed 10/18 trades com CVD explodindo APÓS saída | `7ac5d45` |
| 05/06/2026 | Gate combo: trades_1m ≥ 10, oi_trend ≥ 0.008, lsr_trend ≤ -0.3 | EA-Sprint3: análise discriminação winners vs losers | `d5da930` |
| 05/06/2026 | volume_quality observacional no signal dict | campo para análise futura, sem gate ainda | `3f8b6c1` |
| 05/06/2026 | exp_btc_norm_1h Z-score rolling window=14 | ARIA metric para comparação cross-ativo | `8b81a81` |
| 08/06/2026 | Fix notional liquidações: p*q → ap*z | p=0 em market orders causava notional=0 silencioso | `54225d1` |
| 08/06/2026 | Gate rsi_1h_warmup (uptime < 600s) | rsi:1h = 50.0 artificial nos primeiros 10min pós-restart | `d4446dd` |
| 08/06/2026 | mae_guard_late: 240s / pnl < -3% / mfe < 2% | janela de perda entre 120s e trailing (180s) | `eb85dce` |
| 08/06/2026 | Gate volume_quality_spike (vq ≥ 2.0) | n=33: bloqueou 3 losers, 0 winners | `7bc9aab` |
| 08/06/2026 | mae_guard_late mfe threshold 2% → 3% | BBUSDT MFE=2.98% escapou com -15.92% | `fd0a4a5` |
| 08/06/2026 | liq_threshold proporcional: max(oi_usd×0.02, $10k) | threshold fixo matematicamente impossível para altcoins de $3-5M OI | `9477fd8` |
| 08/06/2026 | ema_trend:4h no MetricStore + gate ema_4h_bearish | 3 sessões: EMA:4h=-6 na maioria dos losers | `adaed4f` |
| 09/06/2026 | Gate ema_4h_bearish: removido AND exp_btc_norm_1h < -1.5 | AND anulava gate — WAXPUSDT EMA:4h=-6, norm_1h=+1.378 → entrou → -16.93% | `9bce976` |
| 09/06/2026 | min_rsi_5m paper 60 → 45 | BANANAS31 (+17%) bloqueado com RSI=48; zona ignição squeeze é 40–55, não >60 | `e52f2e9` |
| 09/06/2026 | fix ema_trend:4h — mínimo candles 100→50 | Gate F-18 cego: campo ficava 0 para símbolos sem 100 klines 4h no buffer. ARUSDT eAssets=-6, bot via 0 | `c7edbf8` |
| 09/06/2026 | fix fit_score_min — _apply_runtime_mode lia raiz prefs (20) | PARTIUSDT entrou com score=86; toda troca de modo sobrescrevia threshold para 20 em vez de 90 | `562e172` |
| 09/06/2026 | blacklist zerada — filosfia dinâmica | EPICUSDT/HOLOUSDT/etc removidos: ativos mudam por minuto, ema_4h_bearish + spread_too_high cobrem os casos | manual |
| 09/06/2026 | **F-12 CONFIRMADO** — liq_short_1m_stable funcional | Pipeline liquidações gerando dados reais (TRUMPUSDT $438, STGUSDT $1276, BTWUSDT $6090); 42 trades anteriores com liq=0 invalidados | boot 21:27:47 |
| 10/06/2026 | **B-liq-cascade-tiers** — liq_threshold OI-based tiers | 0.02×OI sempre acima $50k para altcoins $3-5M OI → cascade nunca disparava. Tiers: OI<$1M→$500 / $1M-$10M→$2k / >$10M→$10k | `6154a7d` |
| 10/06/2026 | **B-34-bypass** — bypass gate lsr_trend_positive para demand breakouts | VELVETUSDT $69k liq_short rejeitado pelo gate lsr_trend_positive antes do score. Critérios bypass: liq>$20k AND trades_1m≥15 AND cvd>2.0 | `519b56d` |
| 10/06/2026 | **min_score 90→85** | Score máximo atingido=88; 25.307 rejeições; zero trades em 6h. KATUSDT 17× a 88pts bloqueado | `470a658` |
| 10/06/2026 | **ema_trend:1h +5 pts bônus no score** | Discrimina pullback em tendência maior (4h/1h fortes, 5m fraco) de bear pleno. BEATUSDT 4h=+6/1h=+6/5m=0 invisível ao score anterior. Não-bloqueante | `d089dce` |
| 10/06/2026 | **cvd_abs_negative gate** | CVD < -100k sem liq_cascade bloqueia entrada | `3a4...` (ver tasks.md) |
| 10/06/2026 | **Bug simétrico F-12: klines + CVD eram Spot** | `_listen_klines` e `_listen_agg_trades` usavam `multiplex_socket` (Spot). CVD e RSI de todos os trades anteriores ao restart invalidados | `fde21af` |
| 10/06/2026 | **queue_size=10000 + max_queue_size** | Overflow silencioso do WebSocket em spikes de volume | `d44e89d`+`cd7c5b3` |
| 11/06/2026 | **funding_rate no ghost signal dict** — T-09 | Campo ausente do bloco `_write_ghost_signal`; paridade com sinal real restaurada. Habilita auditoria T-06 (FR catalisador de squeeze) | `4ffd73f` |
| 11/06/2026 | **Squeezometer crítico 80→85 + nível aquecendo ≥70** | Alinhado com min_score=85. Sieve thresholds (80/60) intocados | `576b5d7` |
| 11/06/2026 | **B-28 gate silence_window_2100** | Bloqueia novas entradas 20:50–21:05 BRT (virada candle diário + funding reset). Relatório diário → 21:01 BRT | `a0f0b57` |
| 11/06/2026 | **B-47 oi_trend > 0.015 como critério VIP** | Acumulação silenciosa agora eleva ativo a prioridade de processamento. Threshold = min_oi_trend para consistência semântica | `92483e3` |

---

## 6. Parâmetros Críticos (preferences.json · estado 10/06/2026)

| Parâmetro | Valor Paper | Valor Live | Descrição |
|-----------|-------------|------------|-----------|
| `min_score` | **85** | 90 | Score mínimo para entrada — reduzido 90→85 em 10/06 (`470a658`) |
| `min_trades_1m` | 10 | 5 | Gate combo — atividade mínima |
| `min_oi_trend` | 0.015 (base) / 0.008 (gate combo) | 0.02 | OI crescendo |
| `max_lsr_trend` | -0.002 (base) / -0.3 (gate combo) | -0.002 | Shorts capitulando |
| `min_rsi_5m` | **45.0** | 70.0 | RSI mínimo 5m — zona ignição squeeze |
| `min_cvd_change_pct` | 1.5 | 2.0 | CVD confirmando com cascade |
| `min_cvd_change_pct_no_cascade` | 1.0 | 1.0 | CVD confirmando sem cascade |
| `sl_pct` | 2.5% | 2.5% | Stop loss |
| `tp_pct` | 5.0% | 8.0% | Take profit |
| `max_hold_seconds` | 480s | 480s | Tempo máximo de posição |
| `min_hold_seconds` | 180s | 180s | Tempo mínimo antes do trailing |
| `trailing_activation_delay_sec` | 180s | 180s | Delay ativação trailing |
| `trailing_stop_callback` | 75% (ou 50% se MFE≥3%) | 75% | Callback adaptativo |
| `blacklist` | `[]` | `[]` | Zerada 09/06 — gates dinâmicos substituem lista estática |

---

### Grupo B-34 — Demand Breakout Bypass (adicionado 10/06/2026)

| Reason Code | Condição | Arquivo:Linha |
|-------------|----------|---------------|
| `lsr_bypass_active` | liq_short_1m_stable > $20k AND trades_1m ≥ 15 AND cvd_change_pct > 2.0 → ignora gate lsr_trend_positive | signal_engine.py L518 · `519b56d` |

> Quando bypass ativo: `lsr_bypass_active = True` logado no signal dict para auditoria do Brain. Validação: Brain audita WR após 20+ trades com `lsr_bypass_active=True`. Se WR < 50% → reverter.

*SQUEEZE_SNIPER_DNA.md v1.4 · 10/06/2026 · Forge é guardião exclusivo · Autorização de mutação: Bob Doreto*
