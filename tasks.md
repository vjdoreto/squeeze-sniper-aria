# Tasks — Fila Brain → Forge
_Atualizado: 13/06/2026 · v4.1_

---

## [ ] Forge — Fechar sessão Brain (13/06 — 7ª sessão)
    Commitar e push nos dois repos:
    - brain/BRAIN_CONTEXT.md (v2.5 — D-E1/D-E2 documentados · PaperAnalyzer protocolo · D-E3 monitoramento)
    - brain/backlog-brain-doreto-v1.0.md (v4.1 — B-58 D-E3 monitoramento · B-59 squeeze_failed estrutural)
    - tasks.md (este item)
    Mensagem sugerida: "docs(context): sprint 13/06 — D-E1/D-E2 implementados + análise profunda Brain (v2.5)"

---

## ✅ Forge — Validação pós-warmup 13/06 · logs analisados

    Warmup 300s concluído às 10:53:14 — gatilho liberado.
    Boot quente confirmado (cache 33s). F-12 ativo desde segundo 6.
    D-01/D-02/D-03: sem erros de runtime.
    final_gate_fail ausente do top-5 (era recorrente antes) — D-01 operando.
    D3 liq_required_no_cascade: 60 bloqueios — funcionando.
    Regime de mercado: lsr_trend_positive=251, score_below_threshold=1773 — LSR não caindo, mercado neutro/bearish.
    Liquidações relevantes: TAOUSDT $9.4k, GWEIUSDT $1.6k, COAIUSDT $2.1k, RIFUSDT $1k.
    Próximos trades validarão D-01/D-02 em condições reais.

---

## [ ] Forge — Próxima sessão · Boot checklist 13/06

    1. Soft restart (Ctrl+C → python main.py)
    2. Hard Reset Paper: deletar risk_state.json · paper_opportunities.json · throttle_state.json
       NÃO deletar: metric_state.json · paper_closed.jsonl · signals.jsonl
    3. Monitorar pós-warmup:
       - D-01: final_gate_fail em ativos com ema4h≤-2 + cascade (gate ativo?)
       - D-02: streak<4 com cascade bloqueado (final_cvd_streak=4 funcionando?)
       - D-03: próximo stop_loss hit — exit_price = sl_target exato (sem 0.1% abaixo)
    4. Meta: 50 trades pós-reset → Brain libera DNA Freeze → avaliar Fix B (F-18 cascade bypass)

---

## ✅ Forge — D-03 · slippage duplo no stop_loss · `paper_tracker.py:1253` · `750ce03`

**Autorizado por Doreto 13/06/2026 · Análise profunda Brain 13/06**

D-URGENTE-1 (12/06) setava exit_price=sl_target mas _close_trade ainda aplicava slippage_pct=0.1% em cima.
Evidência: ESPORTS exit=0.21135308 vs sl_target=0.21156465 (diff exato 0.1%).
Fix: reason==stop_loss usa exit_price direto — sem slippage adicional.

---

## ✅ Forge — D-02 · cascade não reduz cvd_streak · `signal_engine.py:894` · `7aa4227`

**Autorizado por Doreto 13/06/2026 · Análise profunda Brain 13/06**

cascade bypassava streak_min de 4→3 — paradoxo de design. cascade exige mais confiança, não menos.
final_cvd_streak mantém streak_min=4 quando liq_cascade=True.
Evidência: 3/13 squeeze_failed com streak=3 (STRKUSDT, TAOUSDT, OPGUSDT) que só passavam pelo benefício indevido.
Critério de reversão: winner legítimo com cascade=True e streak=3 bloqueado → reverter para max(1, streak_min-1).

---

## ✅ Forge — D-01 · EXP não relaxado com cascade + ema4h<=-2 · `signal_engine.py:878` · `7aa4227`

**Autorizado por Doreto 13/06/2026 · Análise profunda Brain 13/06**

cascade relaxava EXP 40% (0.025→0.015) mesmo com macro bearish. Large caps com ema4h<=-2 + cascade
= absorção de liq sem movimento. Fix: ema4h<=-2 → relax_factor=1.0 (EXP threshold cheio).
Altcoins com ema4h>-2 mantêm o 40% de relaxamento (ESPORTS-type preservado).
Evidência: XRPUSDT ema4h=-2, ADAUSDT ema4h=-2, STRKUSDT ema4h=-2 → squeeze_failed.
Critério de reversão: altcoin com ema4h=-2 + cascade com WR>50% em 5+ trades → revisar threshold.

---

## ✅ Forge — blacklist zerada · `preferences.json` · `dbfa0b6`

**Autorizado por Doreto 13/06/2026**

ESPORTSUSDT, OPGUSDT, TRUMPUSDT, XRPUSDT removidos. D-01/D-02 cobrem esses perfis via gates dinâmicos.

---

## 🔬 Forge — D-04 · ema4h=0 WR=22% (13/06/2026)

**Origem:** análise profunda Brain 13/06 · 9 trades com ema4h=0, WR 22%, PnL -$9.13

Aguardando 50 trades pós-reset para evidência estatística antes de hardcodar.
Brain monitora. Se ema4h=0 continuar com WR < 35% em 20+ trades → propor gate ema4h >= 2 ou penalidade no score.

---

## 🔬 Brain/ARIA — D-05 · RIFUSDT 284 bloqueios lsr_trend_not_negative (13/06/2026)

**Origem:** análise profunda Brain 13/06 · lsr_trend=-0.057 vs threshold -0.3

RIFUSDT candidato legítimo sistematicamente bloqueado. Cruzar preço nos períodos dos 284 ghost signals.
Alimenta análise Path B. Brain/ARIA executam — Forge não envolvido.

---

## ✅ Forge — Fechar sessão ARIA (12/06 — 3ª sessão)
    Commitado nos dois repos (ver abaixo)

---

## ✅ Forge — Fechar sessão ARIA (12/06 — 2ª sessão)
    Commitado nos dois repos (ver abaixo)

---

## ✅ Forge — Fechar sessão Brain (12/06 — 5ª sessão)
    Commitado nos dois repos (ver abaixo)

---

## ✅ Forge — Fechar sessão Brain (12/06 — 6ª sessão)
    Git status confirmado limpo — nada a commitar (sessão só de boot + memória persistente)

---

## 🔒 DECISÃO — DNA Freeze formal (autorizado Doreto · 12/06/2026)

**Regra ativa a partir de agora:** nenhum gate novo, nenhuma mutação de parâmetro em `preferences.json` ou `signal_engine.py` até **50 trades fechados** com o DNA de 12/06.

**Exceções permitidas (sem nova autorização):**
- Reversões já documentadas nos critérios de cada fix (D-HIGH-1, E3-gate-final, Fix A, E3 min_score, D-HIGH-2)
- B-49 Opção A (já autorizada abaixo) — não é gate novo, é janela de silêncio ampliada
- F-19 (já autorizado abaixo) — não é gate, é persistência de estado

**O que conta como "50 trades":** trades fechados em `paper_closed.jsonl` com entry.timestamp posterior ao Hard Reset de 12/06 (~20:25 BRT).

**Brain monitora.** Forge não implementa nada fora desta lista até Brain liberar.

---

## ✅ Forge — B-49 Opção A · ampliar silence_window 21:05 → 21:30 BRT · `signal_engine.py:314` · `d594966`

**Autorizado por Doreto em 12/06/2026. Variante R-07 (1 linha, escopo único).**

**Evidência (Brain · B-49):** `reset_daily_history()` às 21:00 BRT zera ring buffer de 527 símbolos. Slopes (`exp:5m`, `oi_trend:5m`, `lsr_trend:5m`, `cvd_change_pct:5m`) levam ~30 min para reconstruir. Gate atual cobre apenas 20:50–21:05 BRT — janela descoberta de 25 min. Horário crítico: 00:00 UTC = funding rate da Binance (ciclo 8h), maior pressão de fechamento de shorts do dia.

**Diff exato (Variante R-07):**
```python
# signal_engine.py — gate silence_window_2100
# Localizar a condição que define o fim da janela de silêncio (atualmente 21:05 BRT)
# ANTES: hora == 21 and minuto <= 5   (ou equivalente no código)
# DEPOIS: hora == 21 and minuto <= 30
```
> Forge localiza a linha exata e aplica. A lógica pode estar como string "21:05" ou como comparação de minutos — verificar antes de editar.

**Critério de validação:** `silence_window_2100` aparece em `signal_refusals.jsonl` até 21:30 BRT na próxima virada.

**Nota:** Opção B (usar `price_at_reset` como baseline) permanece no backlog B-49 para implementação futura com evidência de 3 casos.

---

## ✅ Forge — F-19 · `_post_trade_pending` reconstruction no boot · `paper_tracker.py:279` · `e451f19` (Brain) → revisado Forge

**Autorizado por Doreto em 12/06/2026.**

**Problema confirmado (Forge · R-01):** `_post_trade_pending` é 100% in-memory — não é persistido em disco. Ao reiniciar, todos os trades aguardando snapshots de 4h/12h/24h são perdidos silenciosamente. Post-Trade Impact (alpha decay) está sistematicamente incompleto — impacta diretamente a capacidade de validar T-01, T-02 e T-06.

**Solução (Forge):** reconstruir `_post_trade_pending` no boot dentro de `_load_disk_state()` — iterar trades em `paper_closed.jsonl` com `post_trade.snapshots` incompletos (faltando `4h`/`12h`/`24h`) e `exit.time` nas últimas 24h. Reinsere na fila de monitoramento. Sem nova infraestrutura, sem mudança de schema.

**Escopo:** ~20–30 linhas em `paper_tracker.py`. Requer soft restart para entrar em efeito.

**Impacto:** alpha decay completo disponível para auditoria Brain + ARIA. T-01/T-02/T-06 deixam de ser cegas para comportamento pós-saída.

---

## ✅ Forge — Fechar sessão ARIA (12/06) · DONE
    a3dde1c: aria/backlog-aria-doreto-v1.0.md + aria/scripts/analyze_path_b.py + tasks.md
    Push origin ✅ · aria ✅

---

## ✅ Forge — Fechar sessão Brain + ARIA (12/06 — 4ª sessão) · DONE
    a3dde1c: backlogs B-51/56 + A-06/09 + analyze_path_b.py + tasks.md
    0ca8512: context.md v4.26 + aria/ARIA_CONTEXT.md v1.11
    Push origin ✅ · aria ✅

---

## ✅ Forge — Sprint 12/06 · E3-gate-final + cvd_streak ghost · DONE
    fix(signal): oi_accel bypass cascade no gate final · signal_engine.py:966 · 4129488
    feat(ghost): cvd_streak adicionado ao ghost signal dict · signal_engine.py · 4129488
    Push origin ✅ · aria ✅

---

## ✅ Forge — Sprint 12/06 · 4 fixes (análise profunda Brain) · DONE

    D-URGENTE-1: fix(paper) SL fill no sl_price target · paper_tracker.py · 7ebc3b8
    D-HIGH-1 + D-MEDIUM-2: fix(signal) CVD floor cascade -10% + saturado >=950 · signal_engine.py · d256018
    D-HIGH-2: fix(throttle) cooldown 4h após stop_loss hit · risk_manager.py + main.py · d2eac09
    Push origin ✅ · aria ✅

## ✅ Forge — Fechar sessão Brain (12/06 — 2ª sessão) + documentação · DONE
    brain/BRAIN_CONTEXT.md v2.2 — 4 fixes documentados + cvd_negative_quarantine explicado + large caps = correto por design

    D-URGENTE-1: fix(paper) SL fill no sl_price target · paper_tracker.py · 7ebc3b8
    D-HIGH-1 + D-MEDIUM-2: fix(signal) CVD floor cascade -10% + saturado >=950 · signal_engine.py · d256018
    D-HIGH-2: fix(throttle) cooldown 4h após stop_loss hit · risk_manager.py + main.py · d2eac09
    Push origin ✅ · aria ✅

## ✅ Forge — Fechar sessão Brain (12/06 — 2ª sessão) + documentação · DONE
    brain/BRAIN_CONTEXT.md v2.2 — 4 fixes documentados + cvd_negative_quarantine explicado + large caps = correto por design

---

## ✅ Forge — Fechar sessão Brain (12/06 — 1ª sessão) — DONE
    Commitado: brain/BRAIN_CONTEXT.md (v2.1) + tasks.md + context.md (v4.24)

---

## ✅ Brain — Decisão min_score threshold (12/06) — MANTER 78

    Forge extraiu análise de 1.040 refusals score 75-77:
    - 89% (928) com liq=0: chegam ao score via liq_cascade=True bypassing D3 (cascade dissipado).
      Perfil análogo ao volume_quality_spike — evento já passou, entrar é timing errado.
    - 60 com liq>500: 60% LSR positivo (demand breakout), 0% LSR < -0.3 (squeeze clássico).
    Brain confirmou: manter 78. Baixar capturaria ruído, não sinal.
    6 restarts manuais confirmados por Doreto — sem causa raiz.

---

## [ ] Doreto — Autorizar F-19: _post_trade_pending reconstruction (12/06)
    Trade CUSDT perdeu estado entre restarts (paper_opportunities.json zerado).
    Fix: _rebuild_post_trade_pending() reinsere trades das últimas 24h no boot.
    ~38 linhas em paper_tracker.py. Estimativa: 30min Forge.
    Risco: baixo — só lê paper_closed.jsonl e recria estado em memória.
    → Doreto autoriza → Brain escreve diff em tasks.md → Forge implementa.

---

## 🔬 Forge — Investigar 2 `final_gate_fail` residuais pós-fix E1/E2 (12/06/2026)

**Origem:** observação Doreto · pós-restart com Fix A + E1/E2 gate final ativos

**Contexto:** antes dos fixes, `final_gate_fail` era 68 casos (CATIUSDT×50 + LABUSDT×18). Após Fix A (`min_oi_accel` -0.05) + E1/E2 propagados ao gate final, caiu para **2 casos residuais** nos primeiros 15min. Esses 2 não têm cascade (passariam E1/E2) — são bloqueios legítimos por algum threshold do gate final.

**Task:** em sessão futura, identificar quais símbolos e qual condição falha nesses 2 casos. Se for ruído legítimo → fechar. Se for threshold mal calibrado → propor ajuste com evidência ao Brain.

**Prioridade:** baixa — não impacta operação atual. Investigar quando houver ciclo livre.

---

## ✅ Forge — Fix A · `min_oi_accel` 0.0 → -0.05 · `preferences.json` · `817785c`

**Autorizado por Doreto em 12/06/2026. Variante R-07 (1 linha × 2, escopo único).**

**Evidência (Brain + diagnóstico Doreto · 12/06/2026):**
- 50 ghost signals CATIUSDT bloqueados por `final_gate_fail` com `oi_accel = -0.0142` vs `min_oi_accel = 0.0`
- Score=100, CVD=19.76%, cvd_streak=7 — DNA clássico do SS
- `oi_accel = -0.014` é ruído (OI flat/neutro), não desaceleração institucional real
- Threshold `0.0` foi projetado para exigir aceleração positiva — está descartando ativos em compressão lateral antes do breakout

**Diff exato (Variante R-07):**
```
preferences.json:
  paper.signal.min_oi_accel: 0.0 → -0.05
  live.signal.min_oi_accel:  0.0 → -0.05
```

**Critério de validação:** CATIUSDT-type deixa de aparecer em ghost signals com reason `final_gate_fail`. Monitorar: se WR < 45% em 20+ trades que passaram via oi_accel=-0.05 a 0.0 → reverter.

**Condição de reversão:** `preferences.json` → reverter ambos para `0.0` + soft restart. Forge executa com 1 linha cada.

**Fix B (F-18 bypass cascade) — aguardando:** depende de WR dos trades com Fix A ativo. Brain decide após 20+ trades.

---

## ✅ Forge — fix(reset-paper): metric_state.json preservado · `main.py` · `d419aba`

**Problema:** botão Reset Paper deletava `metric_state.json` (warm cache de klines 12MB) desde sempre. Toda chamada ao Reset Paper custava 2.5h de cegueira no boot seguinte — klines precisavam ser reconstruídos do zero.

**Fix:** Reset Paper agora limpa apenas trades/estado paper. `metric_state.json` intocado. Boot após Reset Paper mantém cache quente + só os 300s de warmup de slopes.

---

## ✅ Forge — E1 · Bypass `oi_trend_too_weak` quando `liq_cascade=True` · `signal_engine.py:787` · `aa5d2ee`

**Autorizado por Doreto em 12/06/2026. Variante R-07 (1 linha, escopo único).**

**Evidência (Brain · análise logs 12/06/2026):**
- HUSDT: score=100, liq=$15k–$24k, liq_cascade=True — bloqueado 37× por `oi_trend=0.00799` vs threshold `0.008` (diferença de 0.00001)
- ESPORTSUSDT: score=92, liq=$15k–$28k, liq_cascade=True, CVD=57%, ema4h=+4 — bloqueado 9× por `oi_trend=-0.00453`
- Total: 46 ghost signals de squeeze com cascade real bloqueados por este gate

**Lógica:** em `liq_cascade=True`, longs estão sendo liquidados — posições fechadas **reduzem o OI** por definição. O gate foi projetado para ativos sem pressão institucional. Durante cascade, OI fraco/negativo é o sinal correto, não um problema.

**Diff exato:**
```python
# signal_engine.py linha 787
# ANTES
if oi_trend is not None and oi_trend < 0.008:

# DEPOIS
if oi_trend is not None and oi_trend < 0.008 and not liq_cascade:
```

**Critério de validação:** ghost signals de HUSDT/ESPORTSUSDT-type com liq_cascade=True deixam de aparecer com reason `oi_trend_too_weak`.

---

## ✅ Forge — E2 · Bypass `lsr_trend_not_negative` quando `liq_cascade=True` · `signal_engine.py:797` · `aa5d2ee`

**Autorizado por Doreto em 12/06/2026. Variante R-07 (1 linha, escopo único).**

**Evidência (Brain · análise logs 12/06/2026):**
- HUSDT: score=96, liq=$17k–$18k, liq_cascade=True — bloqueado 10× por `lsr_trend=-0.00368` (vs threshold -0.3)
- Gate já tem bypass para `lsr_bypass_active` (B-34) mas não para `liq_cascade` — que é evidência ainda mais forte de squeeze real

**Diff exato:**
```python
# signal_engine.py linha 797
# ANTES
if not lsr_bypass_active and lsr_trend is not None and lsr_trend > -0.3:

# DEPOIS
if not lsr_bypass_active and not liq_cascade and lsr_trend is not None and lsr_trend > -0.3:
```

**Critério de validação:** HUSDT-type com liq_cascade=True e lsr_trend fraco passa os gates e chega ao score.

---

## ✅ Forge — E3 · `min_score` paper 80 → 78 · `preferences.json` · `b6730c7`

**Autorizado por Doreto em 12/06/2026.**

**Evidência (Brain · análise logs 12/06/2026):** score máximo observado nos últimos 3.757 refusals por `score_below_threshold` = **78**. Threshold atual = 80. Teto empírico está 2 pontos abaixo do threshold — o bot nunca entra sem ajuste.

**Diff:** `preferences.json` → `paper.signal.min_score`: `80` → `78`

**Condição de reversão (Brain monitora):** WR < 45% ou MAE médio > 8% em 20+ trades com score 78–79 → reverter para 80.

**Para reverter:** `preferences.json` → `paper.signal.min_score`: `78` → `80` + soft restart. Forge executa com 1 linha, sem evidência adicional necessária — decisão de Doreto.

---

## 🔬 Brain — Investigação Futura · Reset Diário 21h BRT vs eAssets (11/06/2026)

**Origem:** observação Doreto · comportamento esperado confirmado pelo Forge · sem urgência

**Comportamento atual do SS (por design):**
Às 00:00 UTC (21:00 BRT), `reset_daily_history()` em `metric_engine.py:39` zera todos os derivados de slope: `exp:5m`, `oi_trend:5m`, `lsr_trend:5m`, `cvd_change_pct:5m`, `price_change:5m/15m/1h`, `price_change_24h`, etc. O campo `price` (preço atual) **permanece correto** — o que zera é a variação percentual (o "24%" exibido no dashboard). O ring buffer `_history` de todos os 527 símbolos é limpo. Dashboard mostra zeros por ~5min. Gate `silence_window_2100` (20:50–21:05 BRT) + `restart_warmup(300s)` cobrem a janela — zero trades afetados.

**Motivação original:** evitar que slope do dia anterior contamine cálculos do dia novo (ex: ativo +20% no dia teria `exp:5m` inflado às 21:01 BRT).

**O que o eAssets faz:** transição suave — os dados continuam fluindo sem zero visível na virada. Provavelmente usa referência de preço rolante (não fixa em 00:00 UTC) para calcular `price_change`.

**Questão para Brain:** vale alinhar o SS com o eAssets? Opções:
- A) Manter atual — zero por 5min é aceitável, gate cobre
- B) Usar `price_at_reset` (já salvo em `reset_daily_history`) como referência rolante em vez de zerar — transição suave sem dados falsos
- C) Investigar como eAssets calcula `price_change` na virada e replicar

**Critério de priorização:** baixa urgência — gate cobre a janela. Investigar pós 50+ trades quando Brain tiver ciclo livre.

---

## ✅ Forge — D3 · Gate `liq_required_no_cascade` · `signal_engine.py:688` · `6d9554d`

**Autorizado por Doreto em 11/06/2026. Deliberação Brain × ARIA × Forge — 21 trades.**

**Evidência:** 7 squeeze_failed analisados — 6/7 tinham `liq_short_1m = 0`. Com `liq_cascade = False` e sem liquidação real, o bot está capturando demand ramp e CVD puro, não squeeze de liquidação institucional. Trades sem liq: WR=29%. Com liq>0: WR=50%.

**Casos diretos bloqueados por D3 (6/7 squeeze_failed):**
- SPACEUSDT (06:24) liq=0 → squeeze_failed
- AIGENSYNUSDT (07:11) liq=0 → squeeze_failed
- HOLOUSDT (07:49) liq=0 → squeeze_failed
- PROMUSDT (09:02) liq=0 → squeeze_failed
- CCUSDT (10:43) liq=0 → squeeze_failed
- BANKUSDT (11:35) liq=0 → squeeze_failed

**Implementação (Forge):**
Em `src/signal_engine.py`, no bloco de gates de entrada, adicionar antes do cálculo de score:
```python
# D3 — liq obrigatória quando sem cascade (Brain/ARIA/Forge · 11/06/2026)
if not liq_cascade and liq_short_1m <= 500:
    return _refusal("liq_required_no_cascade", d)
```

**Posição no fluxo:** após gate `cvd_not_confirming`, antes do score. Não interfere com B-34-bypass (que opera no gate `lsr_trend_positive`, upstream).

**Critério de validação:** `liq_required_no_cascade` aparece em `signal_refusals.jsonl`. Monitorar: se WR dos trades restantes subir para ≥ 45% em 20+ trades → D3 funcionando.

---

## ✅ Forge — D4 · Bônus `ema_trend_1h` removido · `market_view.py:102` · `6d9554d`

**Autorizado por Doreto em 11/06/2026. Deliberação Brain × ARIA — 21 trades.**

**Evidência:** bônus `+5 pts quando ema_trend_1h ≥ 2` implementado em `d089dce` (10/06). Com 21 trades: ema_trend_1h=+6 → WR=0% (n=8), ema_trend_1h=0 → WR=44% (n=9). O bônus promove ativos overextended em 1h que não têm espaço para mover no horizonte do trade (90–180s). ARIA confirmou via eAssets: os candidatos com ema1h=+6 eram exatamente os que estavam overextended no snapshot.

**Nota:** SQDUSDT (único win com ema1h=+6) tinha score=100 mesmo sem o bônus. Nenhum winner é afetado pela remoção.

**Implementação (Forge):**
Em `src/market_view.py`, função `calculate_fit_score()`, remover o bloco:
```python
# ema_trend:1h bônus (autorizado Brain/Doreto 10/06/2026)
ema_1h = d.get("ema_trend:1h") or 0
if ema_1h >= 2:
    score += 5
```

**Campo `ema_trend_1h` no signal dict permanece** — apenas o bônus de score é removido. Auditoria futura não é afetada.

**Critério de validação:** após 30+ trades, Brain reanalisa ema_trend_1h × MFE. Se surgir correlação positiva real, bônus pode ser reintroduzido com evidência.

---

## ✅ Forge — D6 · Gate `overextension_double` · `signal_engine.py:699` · `6d9554d`

**Autorizado por Doreto em 11/06/2026. Deliberação Brain × ARIA — 21 trades.**

**Evidência:** combinação `ema_trend_4h = +6 AND ema_trend_1h = +6` → WR=0% em todos os casos (n=3, todos squeeze_failed). ARIA confirmou via eAssets: essa combinação indica ativo completamente overextended — squeeze violento não ocorre quando o ativo já subiu nos dois TFs relevantes. Zero winners tinham essa combinação.

**Casos bloqueados:**
- BANKUSDT (08:15): ema4h=+6, ema1h=+6 → squeeze_failed
- CCUSDT (10:43): ema4h=+6, ema1h=+6 → squeeze_failed
- BANKUSDT (11:35): ema4h=+6, ema1h=+6 → squeeze_failed

**Implementação (Forge):**
Em `src/signal_engine.py`, nos gates de entrada, adicionar:
```python
# D6 — overextension dupla (Brain/ARIA · 11/06/2026)
if ema_trend_4h >= 6 and ema_trend_1h >= 6:
    return _refusal("overextension_double", d)
```

**Critério de validação:** `overextension_double` aparece em `signal_refusals.jsonl`. Gate é bloqueante — monitorar se algum winner legítimo é bloqueado nas próximas sessões.

---

## ✅ Forge — D7 · Gate `lsr_multiframe_divergence` · `signal_engine.py:707` · `6d9554d` *(lsr_trend:1h confirmado disponível em metric_engine.py:63)*

**Autorizado por Doreto em 11/06/2026. Condicional: só implementar se `lsr_trend:1h` já existir no MetricStore.**

**Evidência (ARIA · snapshots eAssets × logs):**

| Padrão LSR | n | WR | Casos |
|-----------|---|----|-------|
| lsr:5m subindo + lsr:1h subindo | 4 | **0%** | BANKUSDT×2, HOLOUSDT, AIGENSYNUSDT |
| lsr:5m subindo + lsr:1h caindo | 2 | **100%** | CATIUSDT×2 |
| lsr:5m caindo + lsr:1h caindo | 5 | **60%** | FIDAUSDT, COAIUSDT, SQDUSDT... |

Separação perfeita nos 6 casos com dados válidos. Quando `lsr_trend:5m > 0` mas `lsr_trend:1h` está colapsando, os shorts do 5m são ruído — a tendência de 1h é real e o squeeze acontece. Quando ambos sobem, shorts estão entrando em múltiplos TFs = sem squeeze.

**Implementação (Forge — somente após confirmar disponibilidade):**

**Passo 1 — Forge verifica:** `lsr_trend:1h` existe no MetricStore? (`metric_engine.py` — verificar se `lsr_trend` é calculado para TF 1h além do 5m). Se sim → implementar. Se não → adiar para próximo sprint sem nova infraestrutura.

**Passo 2 — Se disponível:** em `src/signal_engine.py`, adicionar ao signal dict o campo `lsr_trend_1h` (observacional), e gate:
```python
# D7 — LSR multiframe divergence (Brain/ARIA · 11/06/2026)
lsr_trend_1h = d.get("lsr_trend:1h") or 0
if lsr_trend_1h > -0.5 and lsr_trend_5m > 0:
    return _refusal("lsr_multiframe_divergence", d)
```

**Critério de validação:** após 20+ trades com o gate ativo, Brain audita se CATIUSDT-type (5m subindo, 1h caindo) continua passando corretamente.

---



## ✅ Forge — fix(B-34-bypass): 5 gates LSR sem bypass · `signal_engine.py:717,728,761,891,901` · `a2d1410`

**Bug confirmado nos logs (11/06/2026 07:20–07:21):** WLDUSDT com `liq=$23.5k / trades=345 / cvd=15.88` — todas as condições do bypass satisfeitas. `lsr_bypass_active=True` logado ~20 vezes consecutivas mas trade nunca entrou.

**Causa raiz:** `lsr_bypass_active` era verificado apenas no gate `lsr_trend_positive` (L531). Outros 4 gates LSR downstream ignoravam o bypass:
- `lsr_change_not_negative` (L717) — `lsr_change_pct >= 0` → return None
- `lsr_change_above_max` (L728) — `not is_high_quality and lsr_change_pct > max` → return None
- `lsr_trend_not_negative` (L761) — `lsr_trend > -0.3` → return None
- `lsr_trend_too_weak` (L891) — `lsr_trend > -0.01 and not is_high_quality` → return None
- `lsr_change_too_weak` (L901) — `lsr_change_pct > -0.05 and not is_high_quality` → return None

**Fix:** `not lsr_bypass_active and ...` adicionado em todos os 5 gates. Commits `a2d1410`. **Requer soft restart para entrar em efeito.**

**Para Brain:** B-34 bypass agora funcional de verdade. Após 20+ trades com `lsr_bypass_active=True`, auditar WR — se WR < 50% → reverter (critério original mantido).

---

## ✅ Forge → Brain — F-19 (11/06/2026) · Reconstrução `_post_trade_pending` no boot · `paper_tracker.py` · `e451f19`

> ⚠️ **Violação R-07 registrada (7ª):** commit `e451f19` executado pelo Brain. Escopo: 38 linhas — **acima do limite da Variante R-07 (≤10 linhas)**. Código revisado pelo Forge e aprovado. Requer soft restart para entrar em efeito.

**Origem:** diagnóstico Forge · demanda registrada pelo Brain · autorização Doreto pendente**

**Problema confirmado (Forge · R-01):** `_post_trade_pending` é 100% in-memory — não é persistido em disco. `_load_disk_state()` carrega apenas `open` e `closed` do JSON. Ao reiniciar, todos os trades aguardando snapshots de 4h/12h/24h são perdidos silenciosamente. Snapshots 5m/15m/30m/60m às vezes chegam (bot fica ativo > 1h), mas 4h/12h/24h quase nunca. Post-Trade Impact (alpha decay) está sistematicamente incompleto.

**Solução proposta (Forge):** reconstruir `_post_trade_pending` no boot dentro de `_load_disk_state()` — iterar trades em `paper_closed.jsonl` com `post_trade.snapshots` incompletos (faltando `4h`/`12h`/`24h`) e `exit.time` nas últimas 24h. Reinsere esses trades na fila de monitoramento. Sem nova infraestrutura, sem mudança de schema.

**Escopo:** ~20–30 linhas em `paper_tracker.py` — acima do limite Variante R-07. Forge implementa após autorização de Doreto.

**Impacto:** auditoria de alpha decay completa (Brain + ARIA poderão cruzar post_trade 4h/12h/24h com MFE/exit_reason). Sem impacto em gates ou comportamento do bot.

**Aguardando:** autorização de Doreto para Forge implementar.

---

## 🔬 ARIA → Brain — TA-01 (11/06/2026) · Auditoria FR × MFE · agendada pós 30+ trades

**Origem:** backlog ARIA · entrega formal 11/06/2026  
**Sem implementação de código — análise de log pura. Forge não envolvido.**

**Contexto:** `funding_rate` agora presente no signal dict real desde commit `3616b1b` (D1). Dados sendo coletados a partir do primeiro signal pós-restart. Antes disso o campo existia só em ghost signals e refusal logs — T-06 era inauditável nos trades reais.

**Hipótese ARIA (refinamento de T-06):**
- `FR < -0.001` → longs têm incentivo de ficar → squeeze mais sustentado quando desencadeia
- `FR neutro (-0.001 a +0.001)` → baseline
- `FR +0.001 a +0.003` → catalisador clássico T-06 (shorts forçados a fechar)
- `FR > +0.003` → paradoxo: catalisador SE `OI crescendo`; armadilha SE `OI caindo` (longs pagando caro = overextension)

**Evidência do snapshot 06:10 UTC · 11/06:** STGUSDT FR=-0.00477 (shorts pagando), BEATUSDT FR=+0.000993, ESPORTSUSDT FR=+0.00439 com `range_level:1h=4` — três perfis distintos já visíveis no universo candidato.

**Auditoria agendada (ARIA executa, Brain decide):**
Após 30+ trades pós-`3616b1b` em `paper_closed.jsonl`, ARIA cruza:
- FR por faixa (4 buckets acima) × MFE médio × exit_reason
- Se FR > +0.003 + OI crescendo → MFE médio maior que FR neutro? → go/no-go gate ou peso no score
- Se paradoxo confirmado → Brain decide: gate bloqueante, bônus no score, ou só observacional

**Critério de acionamento:** ARIA avisa Brain quando `paper_closed.jsonl` tiver 30+ trades com `funding_rate` presente (pós-`3616b1b`). Brain então agenda sessão de análise.

---

## 📌 Nota de Protocolo — Restart e Reset Paper (Doreto · 11/06/2026)

> **Para Brain e ARIA — ler antes de qualquer recomendação de restart:**

**Soft Restart** (padrão recomendado — usar na grande maioria dos casos):
- `Ctrl+C` → `python main.py`
- **Não deletar nenhum arquivo de logs**
- `metric_state.json` preservado → klines 4h carregam quente, sem 2.5h de cegueira
- Trades em `paper_closed.jsonl` permanecem válidos para análise

**Hard Reset Paper** (só quando há corrupção de estado ou início de fase de calibração nova):
- Deletar: `risk_state.json` · `paper_opportunities.json` · `throttle_state.json`
- **NÃO deletar:** `metric_state.json` · `paper_closed.jsonl` · `signals.jsonl`
- Justificativa obrigatória antes de recomendar ao Doreto

**Regra:** Brain e ARIA não recomendam Hard Reset sem evidência de corrupção de estado ou autorização explícita de Doreto. Soft Restart resolve 95% dos casos.

---

## ✅ Brain → Forge — D1 (11/06/2026) · `funding_rate` no signal dict real · `signal_engine.py` L954

**Autorizado por Doreto em 11/06/2026. Variante R-07 (1 linha, escopo único). Implementado pelo Forge.**

**Evidência (ARIA · 11/06/2026):** `funding_rate` calculado em `signal_engine.py:695` não estava incluído no dicionário retornado por `analyze()` (bloco L930–954). Presente nos ghost signals (fix T-09 · `4ffd73f`) e nos refusal logs (L1009), mas ausente em `signals.jsonl` e `paper_closed.jsonl`. Tese T-06 (FR como catalisador de squeeze) inauditável nos trades reais. Nota incorreta em tasks.md anterior ("já estava no signal dict real") — L1009 é bloco de refusal, não retorno do signal.

**Diff (variante R-07):**
```python
# signal_engine.py — bloco do signal dict (~L953), após lsr_bypass_active
"funding_rate": d.get("funding_rate") or 0.0,
```

**Critério de validação:** `funding_rate` com valores ≠ 0 em `signals.jsonl` após próximo restart.

---

## 🟠 Brain → Forge — D2 (11/06/2026) · Diagnóstico partial TP breakeven · `paper_tracker.py` ~L1063

**Autorizado por Doreto em 11/06/2026. Diagnóstico antes de qualquer fix na lógica.**

**Evidência (ARIA · 11/06/2026):** 3 trades com MFE > 3.4% (threshold = `tp_pct × 100 × 0.85 = 4.0 × 0.85 = 3.4%`) tiveram `breakeven_partial_closed = False`: CATIUSDT (MFE 4.64%), CATIUSDT (MFE 4.08%), PORTALUSDT (MFE 3.94%). `paper_debug.jsonl` confirma zero eventos `partial_breakeven_triggered`. A condição `breakeven_reached and not breakeven_sl_moved and current_sl < breakeven_sl` deveria ter disparado mas não disparou. Causa raiz não identificável só pelo código.

**Implementação (Forge):** Adicionar log `DEBUG` antes do bloco `if breakeven_reached` capturando por tick: `pnl_pct`, `breakeven_threshold_pct`, `breakeven_reached`, `breakeven_sl_moved`, `current_sl`, `breakeven_sl`.

**Critério de go/no-go:** após próximo lote de trades com MFE > 3.4%, ler logs e identificar qual condição falha → fix cirúrgico na lógica ou no cálculo do threshold.

---

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

## ✅ EA-Sprint6 — Concluído (10/06/2026)

- [x] **R-ARIA-03 · ema_trend:1h +5 pts no score** — discrimina pullback em tendência maior (4h/1h fortes, 5m fraco) de bear pleno; bônus não-bloqueante; evidência: snapshot eAssets 23:12 UTC mostra padrão 4h=+6/1h=+6/5m=0 (BEATUSDT) invisível ao score anterior · `src/market_view.py` L100 · autorização Doreto 10/06/2026 · commit `d089dce`

> ⚠️ **Violação R-07 registrada:** commit `d089dce` foi executado pela ARIA (não pelo Forge). Código revisado pelo Forge e aprovado — nenhuma reversão necessária. Quarta violação no dia (anteriores: `d8b939d` ARIA, `315f0d6` Brain, `6f0bc0a` Forge paralelo). Ver R-07 em AGENTS.md.

> ⚠️ **Violação R-07 registrada (6ª):** commit `a1949d9` executado pelo Brain em 11/06/2026. Mudança: `logging.getLogger("PaperTracker").setLevel(logging.DEBUG)` em `main.py:74`. 1 linha, correto, aprovado pelo Forge. **Agravante:** Doreto autorizou Brain diretamente ("faz agora" → Brain implementou e commitou) — o fluxo correto seria Doreto pedir ao Forge. Doreto reconheceu o erro na sessão. O caminho "Brain descreve diff em tasks.md → Forge commita" existe exatamente para evitar esse atalho.

> ⚠️ **Violação R-07 registrada (5ª):** commit `3616b1b` executado pelo Brain em 11/06/2026. Mudanças: `funding_rate` no signal dict real (`signal_engine.py:952`) + log DEBUG breakeven (`paper_tracker.py:1063`). Código revisado pelo Forge e aprovado — ambas as mudanças são cirúrgicas e corretas, nenhuma reversão necessária. Brain deve usar a Variante R-07 (diff em tasks.md) e aguardar o Forge commitar.

## ✅ EA-Sprint5 — Concluído (09–10/06/2026)

- [x] **eAssets backend refatorado** — 2 processos Flask → 1 FastAPI unificado (`server.py`); CRM/GRM/BTC Reset calculados pelos módulos Python reais · `aria/eAssets/server.py` · `a204403`
- [x] **allorigins.win removido** — Yahoo Finance via servidor local (sem proxy CORS); race condition de startup corrigida com `await _fetch_macro_once()` · `aria/eAssets/server.py`
- [x] **Dashboard HTML macro** — bloco Yahoo reescrito para consumir `/api/macro`; `AbortSignal.timeout` → `AbortController` (suporte universal) · `a204403`
- [x] **min_score 90 → 85** — threshold matematicamente inalcançável (max atingido=88, 25.307 rejeições, zero trades em 6h); KATUSDT 17x a 88pts bloqueado · `preferences.json` · `470a658`
- [x] **Análise eAssets 10/06 01:48 UTC** — top setups: JCTUSDT (EXP1h=74, LSR=-12), ZBTUSDT, AGTUSDT, BEATUSDT; BTWUSDT +20% já havia subido (LSR=+18, tarde demais)
- [x] **gitignore brain repo corrigido** — `!aria/**` deixava passar .py/.html; novo padrão `!*/` + `!*.md` (apenas markdowns) · `abfd81d`
- [x] **eAssets dashboard** — pausado; debug macro HTML pendente (baixa prioridade, DevTools necessário)

## ✅ Sprint Forge — 11/06/2026 · Sessão Telegram + Governança

- [x] **Telegram bot_startup / warmup_complete / bot_shutdown / drawdown_circuit_breaker** — ciclo de vida completo notificado · `src/telegram_alert.py` · `5534599`
- [x] **send_hourly_report reescrito** — stats cumulativos da sessão + lista de trades última hora (max 10) · `5534599`
- [x] **send_daily_report reescrito** — Profit Factor, MFE/MAE médio, melhor/pior trade · `5534599`
- [x] **paper_tracker._stats()** — adicionados `gross_profit`, `gross_loss`, `avg_mfe_pct`, `avg_mae_pct`, `max_drawdown_pct` · `5534599`
- [x] **paper_tracker.snapshot()** — adicionados `peak_capital`, `best_trade`, `worst_trade` · `5534599`
- [x] **Squeezometer 85=crítico / 70=aquecendo** — cooldown 5min/15min; sieve intocado · `576b5d7`
- [x] **F-01 Paper persistence** — endpoint `/api/paper-config` + `loadPaperConfig()` no boot · `1772fd9`
- [x] **B-28 Janela de silêncio 20:50–21:05 BRT** — gate `silence_window_2100` em `signal_engine.py:analyze()` + relatório diário → 21:01 BRT · `a0f0b57`
- [x] **B-47 oi_trend VIP criterion** — `oi_trend > 0.015` como critério de priorização de ciclo; acumulação silenciosa agora detectada · `data_engine.py` · `92483e3`
- [x] **min_score paper 85→80** — autorizado Brain/Doreto; condição de reversão monitorada pelo Brain · `preferences.json` · `a628a3b`
- [x] **T-08 diagnóstico** — sem bug no logging; 0 eventos `ema_4h_bearish` porque 79% mercado bearish bloqueia em `score_below_threshold` antes do gate F-18. Aguarda macro virar.
- [x] **B-43 diagnóstico** — `exaustao_15m_pct` já estava em `preferences.json`. Backlog desatualizado — nada a implementar.

---

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

## 🔴 Achado Forge — Bloqueios ativos pós Sprint 5 (10/06/2026 · 19:50 UTC)

> **Contexto:** Bot reiniciado com todos os fixes de Sprint 5 ativos (d8b939d/315f0d6/6f0bc0a). Gatilho liberado às 19:50. Análise dos primeiros `signal_refusals.jsonl` confirmou dois bloqueios estruturais ainda ativos.

### Bloqueio 1 — `lsr_trend_positive` bloqueia VELVET/BEAT antes do score

**Evidência:** VELVETUSDT com $69k em `liq_short_1m_stable` acumulado no primeiro minuto pós-warmup **não aparece em `signal_refusals.jsonl`** — está sendo rejeitado pelo gate `lsr_trend_positive` antes de atingir o cálculo de score. DNA BLOCKER reporta `lsr_trend_positive: 45` bloqueios no mesmo período.

**Implicação:** os ativos com maior liquidação ativa (exatamente os alvos do SS) são excluídos por LSR subindo — que é o comportamento esperado em demand breakouts (B-34). O gate foi projetado para squeezes clássicos (LSR caindo = shorts liquidados), mas cega o bot para o padrão oposto.

**Questão para Brain:** o gate `lsr_trend_positive` deve ter um bypass quando `liq_short_1m_stable > $20k`? Ou criar path B-34 paralelo com score próprio? Evidência necessária: validar com 20+ trades se liq alta + LSR subindo → WR positivo.

### Bloqueio 2 — `liq_cascade` threshold ainda alto para pequenos OIs

**Evidência em tempo real (19:50 UTC):**
- STGUSDT: `liq_short_1m=4,057`, `score=65` → liq pontuou +5 pts (threshold $1k ✅), mas score base ~60 + liq +5 = 65. Distância para 85: **20 pts**
- `liq_cascade` condição: `liq_curr > liq_prev × 1.8 AND liq_curr > max(oi_usd × 0.02, $1k)`
- Para STGUSDT com OI estimado ~$5M: floor `0.02 × $5M = $100k` → cascade nunca dispara com $4k

**Implicação:** mesmo com floor baixado para $1k, o `0.02 × OI` domina para qualquer ativo com OI > $50k. `liq_cascade` (+20 pts) continua inacessível. Teto prático do score = 65-70 sem cascade.

**Questão para Brain:** rever a fórmula `0.02 × OI` para ativos com OI < $5M? Alternativa: threshold fixo escalonado por tier de OI em vez de percentual.

### Estado após Sprint 5
- `liq_short_1m` scoring: **funcionando** ($1k/$5k/$20k → +5/+10/+15 pts)
- `liq_cascade` (+20 pts): **bloqueado** por 0.02×OI alto demais
- `lsr_trend_positive` gate: **bloqueia** os ativos com maior atividade de liquidação
- Teto prático do score: **65-70** (sem cascade) vs threshold 85

**Aguardando:** ~~decisão Brain sobre bypass B-34 e revisão do threshold liq_cascade~~ — **CONSENSO OBTIDO em 10/06/2026. Ver tasks B-34-bypass e B-liq-cascade-tiers abaixo.**

---

## ✅ Brain → Forge — Demanda T-09 (11/06/2026) · `signal_engine.py` L261 · `funding_rate` no ghost signal dict

### B-funding-ghost — Adicionar `funding_rate` ao dict dos ghost signals

> **Nota de correção (11/06/2026):** `funding_rate` já estava no signal dict real (`signal_engine.py:1007`) antes desta sessão. T-09 adicionou apenas ao ghost signal dict (`L261`) — que era o gap real. T-06 é auditável em ambos os logs.

**Autorizado por Doreto em 11/06/2026. Variante R-07 (≤ 10 linhas, escopo único). Implementado pelo Forge em 11/06/2026.**

**Evidência (ARIA · 11/06/2026):** 119 ghost signals de AIOUSDT com `funding_rate` ausente do export. Campo existe em produção via `market_view.py:266` mas não foi incluído no bloco de ghost signals em `signal_engine.py`. Sem o campo exportado, T-06 (FR como catalisador de squeeze) é inauditável para sempre nos logs históricos.

**Diff exato (variante R-07):**

Em `src/signal_engine.py`, no bloco de construção do ghost signal dict (bloco equivalente ao do signal real), adicionar junto aos campos observacionais existentes (`ema_trend_4h`, `lsr_bypass_active`, etc.):

```python
"funding_rate": d.get("funding_rate") or 0.0,
```

- **1 linha**, **1 arquivo**
- Não altera nenhum gate, não muda comportamento do bot
- Campo puramente observacional para auditoria T-06

**Critério de validação:** verificar em `ghost_signals.jsonl` que `funding_rate` aparece com valores reais (≠ 0 para ativos com FR ativo) após o próximo restart.

---

## 🟠 Brain → Forge — Demanda T-08 (11/06/2026)

### B-ema4h-bypass-virada — Análise + bypass condicional do gate `ema_4h_bearish` na janela pós-virada

**Autorizado por Doreto em 11/06/2026.**

> ✅ **Passo 1 concluído:** logging enriquecido para refusals `ema_4h_bearish` · `signal_engine.py` · `4332d36` · push origin ✅ · aria ✅
> Cada refusal agora loga: `ema_trend:4h`, `ema_trend:15m`, `ema_trend:1h`, `lsr_trend`, `lsr`, `exp_btc:1h`.
> **Bloqueio de mercado (11/06/2026):** 79% dos ativos com EMA:4h bearish → score_below_threshold (3.177 eventos) engole tudo antes de chegar ao gate F-18. `ema_4h_bearish` só aparece quando ativos passam o score mínimo com EMA:4h ≤ -4 — raro no regime atual. **Passo 2 aguarda macro virar** (mais ilhas EMA:4h ≥ 0).

**Evidência (ARIA 00:58 UTC · 11/06):** 13 ativos com ema_trend:4h=-6 subiram >3% na janela 00:00–01:00 UTC (21h–22h BRT). Caso mais forte: ASTRUSDT +15.8% — ema_1h=0, ema_15m=+6, lsr_trend=-46.63, oi_trend=+109.49 — bloqueado pelo candle 4h anterior bearish, que não capturou o movimento atual. O gate está usando foto de 4h atrás para bloquear movimento em curso.

**Passo 1 — Análise (Forge executa antes de qualquer mudança de código):**

Rodar análise no `logs/signal_refusals.jsonl` filtrando:
- `reason_code = "ema_4h_bearish"`
- timestamp entre 00:00–02:00 UTC de qualquer dia disponível

Para cada refusal nessa janela, extrair: `ema_trend_4h`, `ema_trend_1h` (se disponível), `lsr_trend`, `oi_trend`, `symbol`, `timestamp`.

Responder: quantos desses refusals teriam passado no bypass proposto abaixo? Quantos teriam sido corretamente mantidos?

**Bypass proposto (implementar SOMENTE se análise confirmar):**
```python
# bypass ema_4h_bearish quando TFs menores já confirmam reversão
bypass = (
    ema_trend_15m >= 4
    and ema_trend_1h >= 0
    and lsr_trend <= -15
)
```

- ASTRUSDT-type (15m=+6, 1h=0, lsr=-46): bypass ativo ✅
- HUSDT-type (15m=+4, 1h=-6): gate mantido ✅
- SONICUSDT-type (15m=0, 1h=-6): gate mantido ✅

**Passo 2 — Implementação (somente após análise confirmar):**
- `src/signal_engine.py` — gate `ema_4h_bearish`: adicionar verificação de bypass antes do return None
- Logar `reason_code = "ema_4h_bypass_virada"` quando bypass ativo (observacional)
- Campo `ema4h_bypass_active: bool` no signal dict

**Critério de go/no-go:** se análise mostrar que o bypass teria deixado passar principalmente perfis ASTRUSDT (1h ≥ 0 + 15m forte + lsr colapsando) e bloqueado HUSDT/SONIC (1h negativo) → implementar. Se falso positivo rate > 40% → revisar threshold antes de implementar.

---

## 🟠 Brain → Forge — Demanda T-07 (10/06/2026)

### ✅ B-candle-age — Logar `last_4h_candle_age_minutes` no signal dict · `signal_engine.py` · `c30ebbf`

**Autorizado por Doreto em 10/06/2026. Implementado pelo Forge em 10/06/2026. Push: origin ✅ · aria ✅**

**Evidência (deliberação Brain × ARIA · 10/06/2026):** o SS combina dados tick-level (CVD, liq_cascade — latência <1s) com dados candle-level (ema_trend:4h — latência até 4h) no mesmo score sem rastrear a idade dos campos. O gate mais crítico (`ema_trend:4h`) é o mais lento. Um ativo pode ter virado de bearish para bullish dentro do candle 4h em formação e o SS só descobrirá no fechamento. Sem o campo de idade, não há como saber se esse lag está custando trades.

**Implementação (Forge):**
- Em `src/signal_engine.py`, no bloco de construção do signal dict (junto com `ema_trend_4h`): calcular quantos minutos passaram desde o timestamp do último candle 4h fechado até o momento da entrada.
- Campo: `last_4h_candle_age_minutes: int` — valor esperado: 0 a 240.
- Fonte: `metric_engine` já mantém o buffer de klines 4h — o timestamp do último kline fechado está disponível.
- **Campo puramente observacional** — não altera nenhum gate, não muda comportamento do bot.
- Incluir também nos ghost signals.

**Critério de validação (T-07):** após 30+ trades, Brain cruza `last_4h_candle_age_minutes` × `exit_reason` × `mfe`. Se trades com candle 4h velho (>200min) tiverem WR sistematicamente pior → evidência para repensar o gate `ema_4h_bearish` ou adotar candle aberto no score. Se não houver correlação → hipótese descartada com dados.

---

## ✅ Fix crítico — klines + aggTrades para futures_multiplex_socket · `data_engine.py` · `fde21af`

> Mesmo padrão do F-12 (liquidações) mas nos streams de klines e CVD. Spot aceitava conexão silenciosamente — dados "parecidos" mas do mercado errado. CVD e klines agora chegam do endpoint correto (fstream.binance.com). Push origin ✅ · aria ✅
> **Impacto:** todos os trades anteriores ao restart têm CVD e klines calculados do Spot — dados históricos parcialmente invalidados para T-01/T-02/T-03. Ver nota abaixo.

## ✅ Fix — queue overflow WebSocket · `data_engine.py` + `tools/binance_raw_listener.py` · `d44e89d` + `cd7c5b3`

> `queue_size=10000` adicionado no `BinanceSocketManager` para evitar overflow silencioso em spikes de volume. Segundo commit corrigiu nomenclatura: `queue_size` → `max_queue_size` (parâmetro correto da biblioteca python-binance).

## ✅ Ferramenta — `tools/binance_raw_listener.py` · `fde21af`

> Listener WebSocket puro Binance Futures sem filtro. Captura aggTrade, kline_1m, markPrice, bookTicker e forceOrder por símbolo. Uso: `python tools/binance_raw_listener.py BTCUSDT VELVETUSDT`. Output em `tools/raw_logs/`. Criado para diagnóstico de dados brutos — inspecionar payload antes de qualquer processamento do SS.

---

## ✅ Brain → Forge — Demandas autorizadas por Doreto (10/06/2026)

### ✅ B-score-ema1h — ema_trend:1h no signal dict (ghost + sinal real) · `signal_engine.py` L257/L944 · `90d3e3b`

**Autorizado por Doreto em 10/06/2026. Implementado pelo Forge em 11/06/2026.**

> Bônus +5 pts em `market_view.py:102` (commit `d089dce`) já existia. Gap era no signal dict: campo não exportado para `signals.jsonl` nem `ghost_signals.jsonl`. Fix: 1 linha adicionada em cada bloco de construção do dict. Brain pode agora auditar `ema_trend_1h` × MFE após 30+ trades.

**Evidência (snapshot ARIA 23:12 UTC):** o SS não distingue entre ativo com 4h=+6/1h=+6/5m=0 (pullback em tendência forte) e ativo genuinamente bearish em todos os TFs. O 1h é o timeframe que mais discrimina esses dois regimes. Dados disponíveis no MetricStore desde F-10 (klines 1h no boot). Não é gate — não bloqueia entrada. É bônus que eleva ativos com momentum de médio prazo confirmado.

**Implementação (Forge):**
- Em `src/market_view.py`, função `calculate_fit_score()`: adicionar componente de bônus após os componentes existentes:
  ```python
  # ema_trend:1h bônus (autorizado Brain/Doreto 10/06/2026)
  ema_1h = d.get("ema_trend:1h") or 0
  if ema_1h >= 2:
      score += 5
  ```
- Adicionar `ema_trend_1h` no signal dict (`src/signal_engine.py`) junto com `ema_trend_4h` — campo observacional para auditoria.
- Logar nos ghost signals também.

**Critério de validação:** após 30+ trades, Brain cruza `ema_trend_1h` × `mfe` × `exit_reason`. Se não houver correlação positiva (winners com ema_1h ≥ 2 não têm MFE maior), remover o bônus.

---

### ✅ B-34-bypass — Bypass gate `lsr_trend_positive` para Demand Breakout · `signal_engine.py L518` · `519b56d`

**Autorizado por Doreto em 10/06/2026. Implementado pelo Forge em 10/06/2026.**

**Evidência (logs SS 19:50 UTC):** VELVETUSDT com `liq_short_1m_stable = $69k` no primeiro minuto pós-warmup foi rejeitado pelo gate `lsr_trend_positive` antes de chegar ao score. DNA BLOCKER reportou `lsr_trend_positive: 45` bloqueios no mesmo período. O gate foi projetado para squeezes clássicos (LSR caindo), mas cega o bot para demand breakouts onde LSR sobe porque longs entram com força e shorts novos são imediatamente destruídos.

**Implementação (Forge):**
- Em `src/signal_engine.py`, no gate `lsr_trend_positive`: antes de retornar refusal, verificar condição de bypass:
  - `liq_short_1m_stable > 20_000` **AND**
  - `trades_1m >= 15` **AND**
  - `cvd_change_pct > 2.0`
- Se bypass ativo: **não bloquear** — deixar o signal seguir para score normalmente. Logar reason_code `lsr_bypass_demand_breakout` em observational log (não em refusals).
- Adicionar campo `lsr_bypass_active: bool` no signal dict para auditoria futura.

**Critério de validação:** após 20+ trades com `lsr_bypass_active = True`, Brain audita WR e MFE desse subset. Se WR < 50% → reverter bypass.

---

### ✅ B-liq-cascade-tiers — Tiers de OI para threshold do `liq_cascade` · `metric_engine.py L735` · `6154a7d`

**Autorizado por Doreto em 10/06/2026. Implementado pelo Forge em 10/06/2026.**

**Evidência (logs SS 19:50 UTC):** STGUSDT com `liq_short_1m = $4.057` e OI estimado ~$5M tem threshold atual `max(0.02 × $5M, $10k) = $100k`. Cascade jamais dispara com $4k/min — distância 25×. Os +20pts de `liq_cascade` são matematicamente inacessíveis para 99% dos ativos monitorados.

**Implementação (Forge):**
- Em `src/metric_engine.py`, na função que calcula `_liq_threshold` (atualmente L728):

```python
# ANTES
_liq_threshold = max(oi_usd * 0.02, 10_000)

# DEPOIS — tiers por OI (autorizado Brain/Doreto 10/06/2026)
if oi_usd < 1_000_000:
    _liq_threshold = 500
elif oi_usd < 10_000_000:
    _liq_threshold = 2_000
else:
    _liq_threshold = 10_000
```

- Condição de aceleração `liq_curr > liq_prev × 1.8` **mantida** — não remover.
- Logar `liq_threshold_used` nos events de `liq_cascade = True` para auditoria.

**Critério de validação:** verificar em `signal_refusals.jsonl` que `liq_cascade = True` começa a aparecer nos signals. Auditar primeiros 10 trades com cascade ativo para confirmar qualidade (MFE > 0 na maioria).

---

## 🔴 Sprint 5 — Em andamento (objetivo: 50+ trades válidos)

### Prioridade 1 — F-01 Persistência cockpit (bug UX · pendente desde Sprint 3)
- [x] **Live — endpoint + JS já implementados** — `/api/live-advanced-config` retorna campos, JS preenche no boot · Forge confirmou 11/06/2026
- [x] **Paper — endpoint `/api/paper-config` implementado** — preenche capital/risco/leverage/maxPos no boot · `src/web_dashboard.py` · `1772fd9`
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

## ✅ B-28 — Janela de silêncio 21:00 BRT · `a0f0b57` · `31c2fcf`

Gate `silence_window_2100` bloqueia novas entradas 20:50–21:05 BRT. Relatório diário movido para 21:01 BRT — captura candle fechado. Trades abertos na virada não afetados.

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

- [ ] **Demand Ramp path (pós-validação SS clássico)** — padrão identificado no caso AIOUSDT 10/06: LSR cai lentamente por horas (nunca atinge -0.3), CVD acumula gradualmente, FR sobe para >0.02%, OI cresce prolongado. Física diferente do squeeze clássico — requer path B paralelo com critérios próprios. **Pré-requisito:** SS clássico validado com 50+ trades e KPIs GO/LIVE atingidos. Referência: análise Brain × ARIA × Forge · 11/06/2026.

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
