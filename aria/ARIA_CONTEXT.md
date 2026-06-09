# ARIA_CONTEXT.md — Squeeze Sniper
> Contexto da analista externa ARIA para retomar no Claude Code (Antigravity).
> ARIA analisa snapshots do eAssets e cruza com dados do bot — não toca código.
> Versão: 1.0 · 09/06/2026

---

## 1. Quem é ARIA

**ARIA** é o agente analítico externo do projeto Squeeze Sniper. Opera sobre snapshots do app eAssets (painel de mercado da Binance USDM) e sobre os logs de trades do bot (`signals.jsonl`, `paper_closed.jsonl`).

ARIA não implementa nada — entrega descobertas estruturadas ao Brain, que repassa ao Forge via `tasks.md`.

---

## 2. O Que ARIA Monitora

### Fontes de dados primárias
- `eassets-panel-YYYYMMDD-HHMMSS.json` — snapshots do painel eAssets (34+ símbolos, 7 timeframes)
- `logs/signals.jsonl` — todos os sinais disparados pelo bot (27+ campos por entrada)
- `logs/paper_closed.jsonl` — trades fechados com PnL real, MFE, MAE, exit_reason, entry.signal

### Campos que ARIA cruza nos trades

| Campo | Fonte | O que revela |
|-------|-------|--------------|
| `ema_trend_4h` | signal dict (adicionado 09/06) | Macro: bearish vs bullish no momento da entrada |
| `rsi_1h` | signal dict | Momentum de médio prazo |
| `rsi_5m` | signal dict | Combustível técnico da squeeze |
| `liq_short_1m` | signal dict | Liquidações reais no minuto (dados reais só a partir de 09/06) |
| `liq_cascade` | signal dict | Confirmação de colapso institucional |
| `volume_quality` | signal dict | cvd_change_pct/(trades_1m+1) — qualidade vs quantidade |
| `exp_btc_norm_1h` | signal dict | Z-score normalizado (window=14) força vs BTC |
| `cvd_streak` | signal dict | Ciclos consecutivos de CVD positivo |
| `exit_reason` | paper_closed | Qual guard terminou o trade |
| `mfe` / `mae` | paper_closed | Qualidade da entrada e da saída |

---

## 3. Descobertas Principais por Sessão

### Sessão eAssets — 03/06/2026 (mercado de sangue)
- **BTC caindo, USDT.D subindo** = dinheiro não saiu de cripto, está rodando entre altcoins
- 36/43 símbolos com EXP_BTC:1m positivo = altcoins desacoplando do BTC
- 29/43 com LSR trend < -5 = squeeze latente generalizada
- **Tier 1:** OPNUSDT (EXP_BTC:1h=151, OI=198) e MAGMAUSDT (EXP_BTC:1h=111) — anomalias institucionais
- **Tier 2:** WLDUSDT, USUSDT, INUSDT, BIOUSDT — força confirmada em 4 timeframes simultâneos

### Descoberta crítica — Divergência temporal (03/06)
ARUSDT: EXP_BTC:1m=-2.47 (fraco) mas EXP_BTC:1h=+42 (fortíssimo) → bot entrou no momento errado do movimento certo → MFE=0, max_hold, -22.59%.

**Tese ARIA:** Entrada de qualidade máxima = EXP_BTC:1m alinhando com 15m/1h já positivos. Quando 1m está fraco mas 15m/1h forte → STANDBY, não entrada.

### Análise EA-Sprint3 (05/06) — discriminação winners vs losers
- **Gate combo** (trades_1m ≥ 10 + oi_trend ≥ 0.008 + lsr_trend ≤ -0.3) discriminou 78%+ dos losers
- `volume_quality_spike ≥ 2.0` bloqueou 3 losers, 0 winners em n=33

### Análise EMA:4h (08/06) — 3 sessões de evidência
- Majoritários dos losers tinham EMA:4h = -6 no momento da entrada
- WAXPUSDT: EMA:4h=-6, entrou por falha de lógica no gate (AND anulava) → saiu -16.93%
- Gate F-18 corrigido em 09/06 para bloquear apenas com `ema_trend:4h ≤ -4` (sem AND)

---

## 4. Teses Abertas — Aguardando Dados

### T-01: liq_cascade como discriminador principal
**Hipótese:** trades com `liq_cascade = True` têm MFE e PnL significativamente maiores que os sem cascade.
**Bloqueio:** `liq_short_1m` era sempre 0 até 09/06 (endpoint WebSocket errado). Dados reais só a partir desta sessão.
**Próximo passo:** analisar primeiros 20+ trades com `liq_short_1m > 0` — distribuição por exit_reason e MFE.

### T-02: ema_trend_4h como filtro de qualidade
**Hipótese:** trades com `ema_trend_4h ≥ 0` têm win rate > 70%; com `ema_trend_4h ≤ -2` win rate < 40%.
**Bloqueio:** campo não estava no signal dict até 09/06.
**Próximo passo:** cruzar `ema_trend_4h` × `exit_reason` × `mfe` nos próximos trades.

### T-03: rsi_1h como gate de momentum
**Hipótese:** entradas com `rsi_1h > 60` têm MFE médio 2× maior que `rsi_1h < 50`.
**Bloqueio:** rsi_1h estava travado em 50.0 artificial por bug de cache (corrigido 09/06).
**Próximo passo:** validar distribuição de rsi_1h nos próximos trades — confirmar que valores reais aparecem.

### T-04: exp_btc_norm_1h como contexto macro
**Hipótese:** Z-score > +1.0 = ativo quente acima da média histórica = squeeze com mais momentum.
**Campo:** `exp_btc_norm_1h` (Z-score rolling window=14 de exp_btc:5m)
**Próximo passo:** cruzar com MFE nos primeiros 30 trades da nova sessão.

---

## 5. Formato de Entrega ARIA → Brain

Cada análise ARIA entrega:
1. **Contexto de mercado** (BTC, USDT.D, condição macro)
2. **Tier 1** — anomalias com evidência quantitativa
3. **Tier 2** — candidatos com força confirmada em múltiplos TFs
4. **Descoberta crítica** — padrão novo ou violação de tese existente
5. **Recomendação** — campo ou gate a investigar, com evidência

---

*ARIA_CONTEXT.md v1.0 · Forge é guardião · 09/06/2026*
