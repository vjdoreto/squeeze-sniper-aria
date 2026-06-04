# Tasks — Fila Brain → Forge
_Atualizado: 04/06/2026 · v1.2_

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

## 🔴 Sprint 3 — Proteção de Capital (próximo)

- [ ] **Correlation Guard expandido** — cobrir 100+ símbolos além dos ~40 atuais · `src/risk_manager.py` CORR_GROUPS
- [ ] **Margem de segurança Sniper** — reinstaurar `balance < usdt_amount × 1.1` quando > $100 · `src/sniper.py`
- [ ] **Kelly floor** — verificar guard `min($20, capital×10%)` para casos kelly=0.001–0.017 bypassando o floor · `src/paper_tracker.py`
- [ ] **MAE gate 60s** _(condicional)_ — implementar só se 20+ trades confirmarem WR 78% com MAE < 2% nos primeiros 60s
- [ ] **Filtro de divergência temporal** — standby quando EXP_BTC:1m < 0 mas 15m/1h forte · `src/signal_engine.py`

---

## 🟡 Dashboard & UX — Bugs Identificados (Sprint 2)

- [ ] **Live config não persiste após restart** — Capital, Risco%, Alav., Max Pos do painel LIVE voltam ao padrão a cada reinício. Deve carregar do `preferences.json["live"]` no boot do dashboard. Arquivo: `src/web_dashboard.py` (loadLiveAdvancedConfig ou equivalente)

- [ ] **Live data não atualiza dinamicamente** — Saldo e Margem carregam na primeira conexão mas param de atualizar. Verificar se o snapshot do LiveTracker está sendo incluído nos broadcasts do WebSocket após o boot. Arquivo: `src/web_dashboard.py` + `main.py` (ws send_loop)

- [ ] **Charts do dashboard sem expressão** — Equity, Drawdown, Kelly e Win Rate ficam vazios até ter trades fechados. Considerar placeholder visual com mensagem de contexto (ex: "aguardando primeiros trades") em vez de canvas em branco.

---

## 🔵 Infraestrutura — Warm Cache de Klines (Sprint 2 ou 3)

- [ ] **Persistir buffer de klines em disco** — salvar `logs/kline_cache/{symbol}_5m.json` no shutdown e recarregar no boot. Elimina o warmup de 70min para RSI/EMA após restart ou hard reset. Cache com TTL de 24h — se mais antigo, descarta e baixa do zero. Formato: JSON ou SQLite. Banco completo é overkill para esse volume.
  - Impacto: RSI e EMA disponíveis desde o primeiro segundo após reinício
  - Origem: Forge · 03/06/2026 · identificado durante sessão noturna

---

## 🟡 Sprint 4 — Liquidity Guard

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
