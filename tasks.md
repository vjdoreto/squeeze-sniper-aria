# Tasks — Fila Brain → Forge
_Atualizado: 10/06/2026 · v2.1_

---

## ✅ Concluído pelo Forge — 03/06/2026

- [x] **max_hold eliminado** — `mae_guard` + `squeeze_aborted` em `paper_tracker.py` + `live_tracker.py`
- [x] **Trailing callback adaptativo** — 50% quando MFE ≥ 3%, 75% abaixo (`paper_tracker.py`, `live_tracker.py`)
- [x] **Paridade paper ↔ live** — gates espelhados em `live_tracker.py` + `sniper.py`
- [x] **Análise de 40 trades** — `docs/RELATORIO_TRADES_2026-06-03.md`
- [x] **DrawdownManager resetado** — `logs/risk_state.json` → consecutive_losses=0, risk_multiplier=1.0
- [x] **liq_cascade $5k → $500** — `src/metric_engine.py` L700 · Sprint 1.5
- [x] **Floor margem $20** — `src/paper_tracker.py` L734 com guard `min($20, capital×10%)`
- [x] **rsi_5m e ob_imbalance no signal dict** — `src/signal_engine.py` L755-757 · logging gap corrigido
- [x] **Exits imediatos para gates de tempo** — bug 2-tick confirmation corrigido · `paper_tracker.py`
- [x] **Dashboard redesign** — logo SVG scope, glassmorphism, charts premium, anti-flicker WebSocket
- [x] **Backup automático ao encerrar** — `src/backup_session.py` + hook no `main.py`
- [x] **Kill de árvore de processos** — `taskkill /F /T /PID` no encerramento · `main.py`
- [x] **Git init + commit inicial** — a8ae357 · 95 arquivos commitados
- [x] **Roadmap v3.0 consolidado** — `docs/ROADMAP_LIVE_V4.3.0_2026-06-03.md` · Brain×Forge

**Verificado como não-bug pelo Forge:**
- [x] ~~CVD/OI chegam zerados~~ — chave correta é `cvd_change_pct:5m` (com sufixo). Dados corretos
- [x] ~~Logging aborts score=0~~ — campo `signal_score` já estava correto
- [x] ~~Throttle 49 símbolos~~ — estado desatualizado, throttle reseta a cada sessão
- [x] ~~rsi/ema_trend/ob_imbalance zerados no score~~ — logging gap, não pipeline bug. Score usa dados corretos

---

## ✅ Sprint 2 — Concluído em 04/06/2026

- [x] **WebSocket liquidações `!forceOrder@arr`** — stream global substituiu centenas de streams individuais que falhavam silenciosamente · `src/data_engine.py` L381
- [x] **Gate CVD anti squeeze_failed** — `cvd_not_confirming` bloqueia entrada sem CVD confirmado e sem liq_cascade · `src/signal_engine.py` L580 · parâmetro `min_cvd_change_pct_no_cascade: 1.0` em `preferences.json`
- [x] **Signal dict completo em paper_closed** — 22 campos persistidos (era 8) · `src/paper_tracker.py` L793
- [x] **Manifesto v2.0** — arquitetura Brain×Forge + protocolo GitHub · `docs/Engenheiro e DNA do Sniper v2.0.md`

## ✅ Sprint 3 — Concluído (05–06/06/2026)

- [x] **F-02 Toggle Paper/Live** — colapso automático de cockpit oposto · `src/web_dashboard.py` · `51be306`
- [x] **F-03 Bracket tiers Binance** — bot valida notional antes do sizing · `src/sniper.py`
- [x] **F-04 Squeezometer relatório** — snapshot agora lê max dos últimos 60min · `src/web_dashboard.py`
- [x] **F-05 PaperAnalyzer** — threshold `min_trades_for_calibration: 30` implementado · `src/paper_analyzer.py`
- [x] **F-06 Placeholders dashboard** — canvas vazio substituído por mensagem contextual · `src/web_dashboard.py`
- [x] **F-10 Warm cache de klines** — buffer salvo/recarregado no boot; RSI/EMA disponíveis desde o 1º segundo
- [x] **F-11 Ghost signals** — gate `rsi_1h_warmup` (300s warmup) eliminou sinais artificiais pós-restart
- [x] **Gate combo** — `trades_1m ≥ 10 + oi_trend ≥ 0.008 + lsr_trend ≤ -0.3` bloqueou 78%+ dos losers em n=33
- [x] **volume_quality_spike ≥ 2.0** — bloqueou 3 losers, 0 winners em n=33 · `src/signal_engine.py`
- [x] **mae_guard_late** — 240s / pnl < -3% / mfe < 3% (janela entre squeeze_aborted e trailing) · `src/paper_tracker.py`
- [x] **liq_threshold proporcional** — `max(oi_usd×0.02, $10k)` para altcoins de baixo OI · `src/metric_engine.py`
- [x] **Correlation Guard expandido** — cobertura >100 símbolos · `src/risk_manager.py`

## ✅ EA-Sprint4 — Concluído (07–09/06/2026)

- [x] **F-12 WebSocket endpoint** — `futures_multiplex_socket` em vez de `multiplex_socket` → `liq_short_1m_stable` funcional · **CONFIRMADO boot 21:27:47** · `src/data_engine.py` · `4f2df00`
- [x] **F-18 Gate ema_4h_bearish** — `ema_trend:4h ≤ -4` sem AND (AND anulava gate, WAXPUSDT -16.93%) · `src/signal_engine.py` ~753 · `9bce976`
- [x] **F-17 min_rsi_5m paper 60→45** — zona de ignição do squeeze é 40–55, não >60; BANANAS31 +17% desbloqueado · `preferences.json` · `e52f2e9`
- [x] **ema_trend:4h min candles 100→50** — gate F-18 cego para símbolos sem 100 klines 4h · `src/metric_engine.py` · `c7edbf8`
- [x] **fix fit_score_min** — `_apply_runtime_mode` sobrescrevia min_score para 20 em vez de 90 · `src/sniper.py` · `562e172`
- [x] **rsi_1h_warmup gate** — RSI:1h travado em 50.0 artificial nos primeiros 10min; gate de 600s corrigido · `src/signal_engine.py` · `d4446dd`
- [x] **Organização do projeto** — `assets/`, `aria/scripts/`, `docs/_arquivo/` criados; root limpo; logo path corrigido · `9b... (commit housekeeping)`
- [x] **Blacklist zerada** — EPICUSDT/HOLOUSDT/JTOUSDT/NILUSDT/PARTIUSDT/PROVEUSDT removidos; gates dinâmicos substituem lista estática · `preferences.json`

## ✅ EA-Sprint5 — Concluído (09–10/06/2026)

- [x] **eAssets backend refatorado** — 2 processos Flask → 1 FastAPI unificado (`server.py`); CRM/GRM/BTC Reset calculados pelos módulos Python reais · `aria/eAssets/server.py` · `a204403`
- [x] **allorigins.win removido** — Yahoo Finance via servidor local (sem proxy CORS); race condition de startup corrigida com `await _fetch_macro_once()` · `aria/eAssets/server.py`
- [x] **Dashboard HTML macro** — bloco Yahoo reescrito para consumir `/api/macro`; `AbortSignal.timeout` → `AbortController` (suporte universal) · `a204403`
- [x] **min_score 90 → 85** — threshold matematicamente inalcançável (max atingido=88, 25.307 rejeições, zero trades em 6h); KATUSDT 17x a 88pts bloqueado · `preferences.json` · `470a658`
- [x] **Análise eAssets 10/06 01:48 UTC** — top setups: JCTUSDT (EXP1h=74, LSR=-12), ZBTUSDT, AGTUSDT, BEATUSDT; BTWUSDT +20% já havia subido (LSR=+18, tarde demais)
- [x] **gitignore brain repo corrigido** — `!aria/**` deixava passar .py/.html; novo padrão `!*/` + `!*.md` (apenas markdowns) · `abfd81d`
- [x] **eAssets dashboard** — pausado; debug macro HTML pendente (baixa prioridade, DevTools necessário)

## 🔴 Sprint 5 — Em andamento (objetivo: 50+ trades válidos)

### Prioridade 1 — F-01 Persistência cockpit Live (bug UX · pendente desde Sprint 3)
- [ ] **Capital/Risco%/Alav/MaxPos/Compound não persistem** após restart → verificar `loadLiveAdvancedConfig` lê `preferences.json["live"]` no boot · `src/web_dashboard.py`
- [ ] **Saldo e Margem não atualizam em tempo real** após boot → verificar snapshot LiveTracker nos broadcasts WS · `src/web_dashboard.py` + `main.py`

### Prioridade 2 — Validação estatística
- [ ] **Coletar 50+ trades** com todos os fixes ativos (F-12 confirmado, ema_4h_bearish ativo, fit_score_min correto)
- [ ] **Auditar gate ema_4h_bearish** — verificar `signal_refusals.jsonl` para confirmar gate disparando em losers
- [ ] **Auditar tese T-01** (liq_cascade discrimina MFE) — analisar 20+ trades com `liq_short_1m > 0`
- [ ] **Auditar tese T-02** (ema_trend_4h × win rate) — cruzar `ema_trend_4h` × `exit_reason` × `mfe`
- [ ] **Auditar tese T-03** (rsi_1h > 60 → MFE 2×) — verificar dispersão de `rsi_1h` nos próximos trades

### KPIs GO/LIVE
- [ ] WR ≥ 60%, PF ≥ 1.5, MaxDD ≤ 12%, MFE ≥ 50%, nenhum loss > 8%

---

## 🟡 Sprint 6 — Liquidity Guard (pós-validação 50+ trades)

- [ ] **validate_liquidity()** — validar profundidade OB antes de entrar · `src/paper_tracker.py` → `src/sniper.py`
- [ ] **Critério:** ≥ 1 trade rejeitado por sessão com log auditável

---

## 🟢 Sprint 5 — Validação Estatística (operacional)

- [ ] **Coletar 50+ trades** com fixes ativos
- [ ] **Rodar auditoria completa** — `analyze_leaks.py`, `audit_deep_dive.py`, `audit_ghost_outcomes.py`
- [ ] **KPIs mínimos GO:** WR ≥ 60%, PF ≥ 1.5, MaxDD ≤ 12%, MFE ≥ 50%, nenhum loss > 8%

---

## 📋 Backlog — Sprint 5+

- [ ] **Dry-run live** — `auto_pilot: false`, 24h
- [ ] **Live gradual** — 3 trades reais a $0.05
- [ ] **Scale-up** — $5 → $20 → $50 → $100
- [ ] **Filtro multiframe no score** — `ema_trend:15m` e `ema_trend:1h` em `calculate_fit_score()`
- [ ] **Peso trades_1m no score** — aguarda 50+ trades com r_pb confirmado (atualmente +0.061, amostra pequena)

---

## 🔬 Pesquisa Estratégica — Próxima Geração do DNA

> Identificados pelo Forge na sessão noturna 03-04/06/2026. Discutir com Brain antes de implementar — precisam de validação nos dados antes de virar código.

- [ ] **Gate de confirmação de momentum sub-minuto** ⚠️ VALIDADO EMPIRICAMENTE — Alpha Decay de 03-04/06/2026 mostrou que os 3 trades SQUEEZE_FAILED subiram após a saída: ZAMA +2.12%, JTO +4.17%, VIC +2.97%. O DNA identificou os ativos CERTOS mas entrou cedo demais (acumulação, não ignição). Squeeze veio DEPOIS do gate de 90s. Solução: entrar só quando preço já está subindo nos primeiros 10-30s — gate de 90s nunca dispararia com MFE > 0% desde o início. — O DNA atual detecta *condições* para squeeze (5m). Falta confirmar que o squeeze *já começou* (30-60s). Ring buffers de 10s/20s/30s no AggTrade WebSocket existente: `price_change:30s`, `cvd_delta:10s`, `trades_rate:20s`. Se nenhum confirmar momentum atual → não entra, independente do score. Elimina entradas em spike que desmoronam antes do trailing posicionar. Referência: `docs/FUTURE_STUDIES_BACKLOG.md` item 2.

- [ ] **Contexto macro em tempo real — CoinMarketCap API** — Doreto tem chave CMC. Dados: `USDT.D`, `BTC.D`, `ETH.D` (dominâncias), `Fear & Greed Index`. Polling a cada 5min. Gate de entrada: se USDT.D subindo + BTC.D subindo = fuga de capital = bloquear sinais (`macro_capital_flight`). Modo standby: USDT.D sobe mas BTC.D estável = rotação interna entre alts = manter ativo. Doreto tem lógica de outro programa que já capturava esses dados via CMC. Referência: `docs/FUTURE_STUDIES_BACKLOG.md` item 3.

- [ ] **CVD cap — perda de discriminação** — CVD capeado em 999.9% frequentemente. Score não discrimina CVD 200% de CVD 1000%. Estudar escala logarítmica para CVD interno: `log10(cvd + 1) × fator`. Manter cap apenas no display do dashboard. Referência: `docs/FUTURE_STUDIES_BACKLOG.md` item 4.

- [ ] **Paridade com eassets.ai — dados sub-segundo** — eassets.ai gerencia dados de segundos em tempo real. SqueezeSniper monitora 529 símbolos mas em janelas 1m/5m. Para o gate de momentum (item acima), precisamos de janelas 10-30s. Solução: ring buffers no MetricStore alimentados pelo AggTrade WebSocket existente — sem nova conexão. Custo computacional: baixo. Referência: `docs/EASSETS_REFERENCE.md` + `docs/FUTURE_STUDIES_BACKLOG.md` item 5.

---

## 📊 Análise do Score — pendente re-run

O Brain rodou análise de discriminação com 40 trades (ver `reports/analise-score-03-06-2026.md`).  
Próximo run após 50+ trades com `rsi_5m` e `ob_imbalance` agora exportados no signal dict.

---

_Brain escreve demandas com evidências. Forge executa e marca como concluído com arquivo/linha._  
_Guardião do código: FORGE exclusivamente._
