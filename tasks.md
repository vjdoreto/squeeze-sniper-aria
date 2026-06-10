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

## 🚨 BLOQUEIO CRÍTICO — Consenso Brain × ARIA × Forge (10/06/2026)

> **Contexto:** Bot coletou apenas 2 trades. Forge diagnosticou dados internos do SS e concluiu erroneamente "mercado sem pressão". Doreto corrigiu: VELVETUSDT +95%, BEATUSDT +55%, AIOUSDT +25% — squeezes reais que o bot não capturou. O SS está cego a oportunidades que estão acontecendo.

### Dados confirmados pelo Forge (logs SS)
- **Score máximo atingido: 83** · threshold: 85 · 4.868 refusals por `score_below_threshold`
- **liq_short_1m = 0 e liq_cascade = false em 100% dos signals** — mesmo com F-12 ativo
- Esses dois campos valem **35 pts** do score → teto prático ~83 sem eles
- Causa provável: threshold F-16 (`max(OI × 2%, $10k)`) alto demais para os ativos monitorados
- Ghost signals: só HOMEUSDT e PARTIUSDT chegam perto do threshold — universo restrito

### Questões abertas — requerem consenso antes de qualquer fix

**Para ARIA (análise eAssets):**
- [ ] **Case VELVETUSDT +95%, BEATUSDT +55%, AIOUSDT +25%** — analisar o que os snapshots eAssets mostravam ANTES desses movimentos. Quais indicadores estavam ativos? OI, LSR, EXP_BTC, ema_trend:4h? O SS teria visto esses setups?
- [ ] Snapshot atual: quantos ativos têm OI+ · LSR- · EXP_BTC+ simultaneamente? Score teórico máximo dos melhores candidatos atinge 85?
- [ ] O mercado está gerando condições de squeeze agora ou está em regime diferente?

**Para Brain (decisão estratégica):**
- [ ] **Como desbloquear o score?** Com liq_cascade/liq_short_1m sempre zero, teto é 83. Opções:
  - A) Reduzir `min_score` para 80 (mais trades, sem confirmação real de liquidações)
  - B) Redistribuir os 35 pts de liq para componentes funcionais (CVD, trades_1m, exp_btc)
  - C) Manter 85 e corrigir o threshold do F-16 para capturar liquidações menores
- [ ] **O DNA atual está alinhado com o mercado de hoje?** LSR trend positivo + CVD negativo dominam os refusals — isso é o mercado ou o SS olhando os dados errados?
- [ ] **`min_oi_trend: 0.015` no preferences vs `0.008` do gate combo** — há duplicação de filtro?

**Para Forge (aguardando consenso):**
- [ ] Implementar decisão do Brain sobre o score após análise ARIA confirmar causa raiz

### Achado técnico Forge — causa raiz ESTRUTURAL confirmada no código (10/06/2026)

**O pipeline F-12 está ativo** — eventos chegando via `futures_multiplex_socket`. O problema são os thresholds do score calibrados para large caps:

`market_view.py` L120-125 — score contributions de `liq_short_1m_stable`:
- `> $100k` → +15 pts · `> $50k` → +10 pts · `> $10k` → +5 pts
- **Abaixo de $10k = 0 pts** (piso absoluto)

`metric_engine.py` L728 — `liq_cascade`:
- `_liq_threshold = max(oi_usd * 0.02, 10_000)` — floor de $10k por minuto por símbolo

**Eventos reais confirmados (DIAG F-12 09/06):** BTWUSDT $6.090 · VELVETUSDT $4.439 · STGUSDT $1.276 · TRUMPUSDT $438

Conclusão: para 99%+ dos ativos small/mid cap, liq_short_1m nunca atinge $10k/min → **0 pts de liq** → score teto 83 → threshold 85 nunca atingido.

**VELVET +95%, BEAT +55%, AIO +25%:** provavelmente tiveram eventos de liquidação reais abaixo de $10k/min por símbolo. O SS recebeu, acumulou, e descartou silenciosamente por threshold. Bot estava cego apesar de ter os dados.

**Proposta técnica para consenso Brain × ARIA:** reduzir thresholds proporcionalmente ao OI do ativo — mesma lógica do F-16 mas também no score. ARIA confirmar: esses 3 casos tinham liq events? Qual notional?

### Achado estrutural Forge — Radar Global é parcialmente cego (10/06/2026)

**VELVET score 12/22 com exp:5m=0.0 enquanto subia +100% — causa raiz:**

O SS declara "RADAR GLOBAL: 530+ símbolos" mas na prática:
- Boot bootstrap de klines: apenas **top 50 por volume** (`data_engine.py` L247)
- Ativos fora do top 50: precisam de ~2.5h de WebSocket para ter `exp:5m` válido (30 candles × 5min)
- OI/LSR: top 100 prioritários + rotação esporádica dos demais — dados velhos para small alts
- Critério de prioridade (`data_engine.py` L557): `top_100 OR exp:5m>0.01 OR score>=60`

**O paradoxo estrutural:** para entrar na janela de dados o ativo precisa já ter dados → nunca aquece antes de explodir.

**Resultado:** VELVET, BEAT, AIO — small/mid caps prestes a squeeze — ficam em modo "frio" com dados zerados. O SS os scanneia, gera score inválido (12/22), rejeita. +100% invisível.

**Questão para consenso (Doreto + Brain + ARIA):**
O SS foi projetado para surfar squeezes de ativos JÁ com volume alto (top 100). Ativos que ainda não explodiram são invisíveis por design. Isso é uma limitação arquitetural — não de parâmetro.

Opções:
- **A) Fix arquitetural** — expandir bootstrap + warm prioritário para qualquer ativo com OI crescente ou volume spike nas últimas 4h (requer dados do eAssets ou CMC como feed externo)
- **B) Ajuste de escopo** — aceitar que o SS opera apenas em top 100 por volume e calibrar o DNA para esse universo (abrir mão de VELVET-type)
- **C) Pivô** — se o alvo são small/mid caps, o SS precisa de redesign na camada de dados

---

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

---

## ⚠️ Nota de protocolo — 10/06/2026

ARIA implementou diretamente o commit `d8b939d` (fix T-1) sem passar por Brain → tasks.md → Forge. O código foi revisado pelo Forge e está correto — aprovado para produção. Mas o fluxo correto é: ARIA entrega achados ao Brain, Brain escreve em tasks.md, Forge implementa. Regra R-06 do AGENTS.md. Não repetir.

---

_Brain escreve demandas com evidências. Forge executa e marca como concluído com arquivo/linha._  
_Guardião do código: FORGE exclusivamente._
