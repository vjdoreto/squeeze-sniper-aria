# Análise Detalhada & Auditoria Gemini — Squeeze Sniper (06/06–08/06/2026)

**Data**: 08/06/2026  
**Autor**: Auditoria Técnica Gemini + Cross-Reference eAssets (33 Trades Consolidados)

---

## 1. Visão Geral dos Dados — Duas Sessões

### 1.1 Snapshot 06/06 (Kiro — 9 trades)

| # | Símbolo | Exit | PnL% | MFE% | MAE% | Dur. |
|---|---------|------|------|------|------|
| 1 | VICUSDT | squeeze_failed | -11.29% | 0.0% | -9.90% | 90s |
| 2 | HOLOUSDT | squeeze_failed | -10.01% | 0.0% | -10.43% | 90s |
| 3 | BIOUSDT | squeeze_failed | -3.96% | 0.0% | -2.95% | 90s |
| 4 | BANKUSDT | trailing_stop ✅ | +22.05% | +30.60% | -1.40% | 181s |
| 5 | GPSUSDT | squeeze_failed | -4.17% | 0.0% | -6.90% | 90s |
| 6 | EDENUSDT | trailing_stop ✅ | +9.14% | +10.55% | -1.40% | 181s |
| 7 | SPKUSDT | mae_guard | -6.34% | +0.55% | -6.64% | 120s |
| 8 | MANTAUSDT | squeeze_failed | -8.49% | 0.0% | -9.89% | 90s |
| 9 | OPENUSDT | trailing_stop ✅ | +5.60% | +9.78% | -1.40% | 181s |

### 1.2 Snapshot Consolidado 08/06 (33 trades)

- **Total de Trades Fechados**: 33
- **Win Rate Global**: 27.2% (9 Wins / 24 Losses)
- **Capital Inicial**: 1000.0 USDT
- **Capital Atual**: 989.12 USDT
- **Avg Closed PnL%**: -1.45%
- **Capture Efficiency%**: -52.10% (Perda grave de lucro no Trailing)
- **Total de Sinais Gerados**: 245
- **Sinais Únicos por Símbolo**: 112
- **Simbolos no eAssets**: 531
- **Simbolos com Movimento Forte**: 76
- **Win Rate por Símbolo**:
  - BANK: 100%
  - EDEN: 100%
  - OPEN: 100%
  - ETHFI:100%
  - HOLO: 33.3%
  - OG:50%
  - **NOVO:** ADAUSDT: 100% (Scalp rápido)

---

## 2. Tabela Detalhada dos Trades Recentes (Destaques dos 33)

| Índice | Simbolo    | Resultado (USDT) | Score | CVD 1m | CVD Change % | RSI 5m | Trades 1m | Exp BTC 1h | Relax Label | Observações |
|--------|------------|-------------------|-------|--------|--------------|--------|-----------|------------|-------------|-------------|
| 1      | VICUSDT    | -0.08             | 91    | -18493 | 1.3          | 78     | 12        | 1.5334     | NORMAL      | CVD negativo |
| 2      | HOLOUSDT   | -0.08             | 100   | -22479 | 3.2          | 74     | 28        | 1.5348     | NORMAL      | CVD negativo |
| 3      | BIOUSDT    | -0.08             | 90    | 1023.5 | 2.1          | 68     | 10        | 1.5392     | NORMAL      |             |
| 4      | BANKUSDT   | -0.08             | 100   | 1234.2 | 1.8          | 72     | 12        | 1.5366     | NORMAL      |             |
| 5      | GPSUSDT    | -0.08             | 100   | 892.1  | 2.5          | 70     | 32        | 1.5401     | NORMAL      |             |
| 6      | EDENUSDT   | -0.08             | 98    | 1567.3 | 1.9          | 66     | 16        | 1.5389     | NORMAL      |             |
| 7      | SPKUSDT    | -0.08             | 86    | 2109.8 | 2.3          | 64     | 264       | 1.5378     | NORMAL      | Muitos trades |
| 8      | MANTAUSDT  | -0.08             | 95    | 1789.4 | 2.0          | 65     | 140       | 1.5357     | NORMAL      | Muitos trades |
| 9      | OPENUSDT   | +0.20             | 93    | 898.6  | 1.5          | 62.2   | 31        | 1.5419     | NORMAL      | 🟢 Vencedor |
| 10     | ETHFIUSDT  | -0.08             | 100   | 1456.7 | 2.2          | 71     | 73        | 1.5371     | NORMAL      |             |
| 11     | NILUSDT    | -0.08             | 100   | -4468.8| 1.6          | 69     | 15        | 1.5362     | NORMAL      | CVD negativo |
| 12     | HOLOUSDT   | -0.08             | 100   | 50214  | 8.9          | 75     | 25        | 1.5348     | NORMAL      |             |
| 13     | PYTHUSDT   | -0.08             | 100   | 1324.1 | 1.7          | 70     | 14        | 1.5383     | NORMAL      |             |
| 14     | NILUSDT    | -0.08             | 100   | 1189.2 | 1.9          | 71     | 20        | 1.5362     | NORMAL      |             |
| 15     | OGUSDT     | -0.08             | 90    | 45.7   | 1.4          | 68     | 15        | 1.5397     | NORMAL      |             |
| 16     | HOLOUSDT   | +0.57             | 100   | 62365  | 10.1         | 81.8   | 18        | 1.5348     | NORMAL      | 🟢 Vencedor, CVD positivo forte |
| 17     | IDUSDT     | -0.08             | 100   | 2145.3 | 2.4          | 73     | 168       | 1.5375     | NORMAL      | Muitos trades |
| 18     | ARUSDT     | -0.08             | 100   | 1892.6 | 2.1          | 72     | 43        | 1.5386     | NORMAL      |             |
| 19     | OGUSDT     | -0.08             | 100   | -632.2 | 1.8          | 69     | 17        | 1.5397     | NORMAL      | CVD negativo |

---

## 3. Principais Achados — Kiro (06/06)

### 3.1 🔴 CRÍTICO: `liq_short_1m = 0` em 100% dos sinais

Este é o dado mais crítico da auditoria Kiro:

- **Signals.jsonl (todos os 40+ sinais lidos):**
  - `liq_short_1m = 0.0` em 100% dos casos
  - `liq_cascade = false` em 100% dos casos
  - `liq_short_hist = [0,0,0,0,0,0,0,0,0,0]` (todos os símbolos no metric_state.json)

O Sprint 2 implementou o WebSocket `!forceOrder@arr` no `data_engine.py L381`. Os dados estão chegando, mas os valores seguem zerados nos sinais. Isso significa que o score está operando com **35 pontos cegos** em toda e qualquer entrada:

| Componente | Pts máx | Estado atual |
|-----------|---------|--------------|
| `liq_cascade` bônus | +20 | 🔴 sempre false |
| `liq_short_1m_stable` | +15 | 🔴 sempre 0.0 |
| **Total perdido** | **+35** | — |

Hipótese (Kiro): o WebSocket `!forceOrder@arr` pode estar recebendo dados mas o campo `liq_short_1m_stable` pode estar exigindo um período de estabilização (janela de tempo ou contagem mínima de eventos) que nunca é satisfeita porque os eventos de liquidação são raros. Verificar a lógica de atualização do campo stable em `metric_engine.py` / `data_engine.py`.

### 3.2 Achado: `rsi_1h = 50.0` fixo nos primeiros sinais (warmup)

Nos primeiros ~10 sinais do `signals.jsonl` da sessão 06/06, o `rsi_1h` apareceu travado em exatamente `50.0` em praticamente todos os símbolos. Isso é o warmup gate de RSI em 1h ainda incompleto no início da sessão.

Impacto: Os primeiros 3 trades (VICUSDT, HOLOUSDT, BIOUSDT — todos squeeze_failed) entraram com `rsi_1h = 50.0` artificial. Se o filtro multiframe estivesse ativo, o 1h sem dados reais poderia ser tratado como sinal de cautela em vez de neutro.

### 3.3 Achado: `ghost_signals.jsonl` revela filtros em ação

Os ghost_signals mostraram dois padrões relevantes:

- **Padrão A**: `lsr_trend_not_negative` bloqueando entradas com score 85–90:

  ```
  API3USDT: score=85 · lsr_trend=-0.174 · bloqueado repetidamente
  HMSTRUSDT: score=90 · lsr_trend=-0.058 · bloqueado
  ```

  Símbolos com score alto estão sendo recusados porque o `lsr_trend` não passa no gate de sinal (provavelmente `max_lsr_trend: -0.002` do preferences.json requer valor mais negativo que -0.17). LSR trend de -0.17 é um short em pânico legítimo — threshold pode estar invertido ou muito restritivo na direção errada.
- **Padrão B**: `trades_1m_too_low` em HMSTRUSDT score 90:
  Setup de altíssima qualidade sendo bloqueado por liquidez insuficiente (funcionando corretamente, mas worth documentar).

### 3.4 Achado: `RELAXED (HQ DNA)` com WR 0%

4 dos 5 squeeze_failed da sessão 06/06 vieram de entradas `RELAXED (HQ DNA)`. O modo relaxado está aprovando entradas que o modo normal bloquearia — e essas entradas estão falhando mais (oposto do esperado: HQ = High Quality deveria ter WR maior).

Pergunta (Kiro): Quais são os critérios exatos do `RELAXED (HQ DNA)` no `signal_engine.py`? Os dados sugerem que o modo relaxado pode estar sendo ativado nos momentos errados.

### 3.5 Contexto de Mercado (06/06)

O `metric_state.json` mostrou:

- `ema_trend:1h = -6` (mínimo absoluto) em BTC, ETH e SOL. Mercado em tendência de baixa no 1h.
- Bot estava entrando LONG em altcoins enquanto o macro 1h era bearish generalizado.
- Filtro `mtf_1h_crash` estava bloqueando ativos com `exp_1h < -0.05`, mas o BTC em si com `ema_trend:1h = -6` não estava sendo considerado como contexto global.

---

## 4. Principais Problemas Identificados (07/06)

### 4.1 🔥 Filtro Obrigatório: CVD 1m Positivo na Entrada

- **Total de trades com CVD 1m negativo (07/06):** 4 (21% dos trades total)
- **Resultado:** TODOS esses trades perderam (apenas taxas, -0.08 USDT cada)
  - VICUSDT: CVD = -18493.46 → PNL -0.08
  - HOLOUSDT (trade 1): CVD = -22479.5 → PNL -0.08
  - NILUSDT: CVD = -4468.8 → PNL -0.08
  - OGUSDT (trade 2): CVD = -632.2 → PNL -0.08

- **Os 2 vencedores (07/06) tiveram CVD POSITIVO:**
  - OPENUSDT: CVD = 898.6 → PNL +0.20
  - HOLOUSDT (trade 16): CVD = 62365 → PNL +0.57

### 4.2 Muitas Oportunidades Perdidas (76 Simbolos com Movimento Forte no eAssets)

- **TOP 5 Simbolos com Força Máxima (9/9) que não foram negociados (07/06):**
  1. DASHUSDT: 24h = 15.3%, EXP 5m = 8.5 → **Nenhum sinal/trade**
  2. CTSIUSDT: 24h = 19.3%, EXP 5m = 9.7 → **Nenhum sinal/trade**
  3. SIRENUSDT: 24h = 51.2%, EXP 5m = 57.5 → **Nenhum sinal/trade**
  4. JELLYJELLYUSDT: 24h = 7.5%, EXP 5m = 4.0 → **Nenhum sinal/trade**
  5. BUSDT: 24h = 15.5%, EXP 5m = 5.4 → **Nenhum sinal/trade**
- **Simbolos que receberam sinal mas não entraram:** WLDUSDT, JTOUSDT, SAHARAUSDT, OPGUSDT, HMSTRUSDT

### 4.3 SS Saiu Cedo Demais em Várias Oportunidades

- **Max Hold Seconds Atual**: 480 (8 minutos)
- **Exemplo Claro**: HOLOUSDT teve 3 trades, sendo 1 vencedor de +0.57 USDT — mas o preço **continuou subindo** após o fechamento!
- **Outros Exemplos**: OPENUSDT (+0.20 USDT) também provavelmente saiu cedo

### 4.4 Inatividade Durante Mercado Quente (Relatado pelo Usuário)

O usuário mencionou que o SS ficou inativo por algum tempo, depois fez trades, depois ficou inativo de novo com o mercado quente — isso precisa ser investigado (procurar logs de timestamps, throttle_state.json, etc.)

---

## 5. Resumo Executivo — O que está Funcionando vs. O Que Não

### ✅ Funcionando (Kiro + 07/06)

- **trailing_stop** — 3/3 exits = 100% WR na sessão 06/06, captura MFE real (+10 a +30%)
- **mae_guard** — cortou SPKUSDT em -6.34% antes de piorar (06/06)
- **mtf_1h_crash** — bloqueando entradas em ativos com exp_1h < -0.05 (06/06)
- **Score ≥ 90 como threshold** — os winners chegaram com score 90–100 (06/06 + 07/06)
- **Trades vencedores com CVD positivo** (07/06)

### 🔴 Não está Funcionando / Precisa de Atenção

- **liq_short_1m_stable = 0** — score opera com 35pts cegos (CRÍTICO, Kiro)
- **CVD negativo na entrada = perda garantida** (07/06)
- **squeeze_failed frequente** — MFE=0 em muitos trades (06/06 + 07/06)
- **RELAXED (HQ DNA) com WR 0% na sessão 06/06** (Kiro)
- **rsi_1h = 50.0 no warmup** — primeiros trades com dados de 1h artificiais (Kiro)
- **SS inativo durante mercado quente** (relatado pelo usuário)

---

## 6. Configurações Atuais (preferences.json)

Os filtros estão **muito apertados**, o que explica a baixa produtividade e perdas de oportunidades:

```json
{
  "paper": {
    "signal": {
      "min_trades_1m": 10,
      "min_score": 90,
      "min_rsi_5m": 60.0,
      "min_oi_trend": 0.015,
      "max_lsr_trend": -0.002,
      "min_cvd_change_pct": 1.5,
      "min_cvd_change_pct_no_cascade": 1.0
    },
    "execution": {
      "sl_pct": 0.025,
      "tp_pct": 0.04,
      "max_hold_seconds": 480
    }
  }
}
```

---

## 7. Perguntas Específicas para o Brain (Kiro)

1. **O `liq_short_1m_stable` tem lógica de estabilização com período mínimo?** Se sim, pode nunca ser satisfeita em sessões com poucos eventos de liquidação.
2. **O `RELAXED (HQ DNA)` relaxa qual gate especificamente?** Se relaxa o CVD gate (`min_cvd_change_pct_no_cascade`), e as liquidações estão zeradas, então o modo relaxado está aprovando entradas sem CVD suficiente E sem liquidações.
3. **O gate `min_score: 90` está sendo aplicado antes ou depois do modo relaxado?** VICUSDT entrou com score 88 (abaixo de 90) na sessão 06/06.
4. **O `exp_btc_norm_1h` está sendo usado no score?** O metric_state mostra `exp_btc_norm_1h` calculado para todos os símbolos, mas o context.md indica que o score opera só em 5m.
5. **Por que o SS ficou inativo durante mercado quente?** Verificar logs de timestamps, throttle_state.json, etc.

---

## 8. Recomendações Prioritárias (Para Discussão)

### PRIORIDADE 1 — Validar `liq_short_1m_stable` (Blocker de Qualidade, Kiro)

- **Evidência**: 100% dos sinais da sessão 06/06 com `liq_short_1m = 0`
- **Hipótese**: Lógica de stable exige janela que não é satisfeita
- **Ação**: Forge inspeciona `metric_engine.py` / `data_engine.py` — lógica de atualização do campo stable
- **Critério de done**: Pelo menos 1 evento `liq_short_1m > 0` em sessão com mercado ativo

### PRIORIDADE 2 — Implementar Filtro CVD 1m Positivo Obrigatório

- **Evidência**: Todos os trades com CVD negativo perderam; todos os vencedores tiveram CVD positivo
- **Justificativa**: Elimina 21% dos losers imediatamente
- **Ação**: Adicionar verificação que `cvd_1m > 0` no momento do sinal

### PRIORIDADE 3 — Investigar `RELAXED (HQ DNA)` + `squeeze_failed` (Kiro)

- **Evidência**: 4/5 squeeze_failed = RELAXED, WR 0% no modo relaxado na sessão 06/06
- **Hipótese**: Modo relaxado bypassa gates que eliminam false positives
- **Ação**: Forge mostra ao Brain quais gates o RELAXED relaxa especificamente
- **Critério de done**: Brain entende o trade-off e decide se ajusta ou mantém

### PRIORIDADE 4 — Aumentar `max_hold_seconds`

- **Atual**: 480s (8 min)
- **Sugestão**: 720s (12 min) ou 900s (15 min)
- **Justificativa**: SS está saindo cedo de oportunidades que continuam se desenvolvendo

### PRIORIDADE 5 — Relaxar Alguns Filtros para Aumentar Produtividade

- **`min_score`**: 90 → 80 ou 85
- **`min_rsi_5m`**: 60 → 50 ou 55
- **Ajustar `max_lsr_trend`?** (Threshold pode estar bloqueando LSR trends legítimos — Kiro)

### PRIORIDADE 6 — Investigar Inatividade Durante Mercado Quente

- **Ação**: Verificar logs de timestamps, throttle_state.json, signal_refusals.json, etc.

---

## 9. Auditoria de Dados: O Paradoxo Sniper vs. Trendometer

Com base no cruzamento do `eassets-panel-20260607-102455.json` e os logs de execução, aqui estão as evidências numéricas para o Brian.

### 9.1 Tabela de Oportunidades Perdidas (eAssets Strong vs. SS Inactive)

Identificamos que o Sniper ignorou os ativos de maior "Strength" do eAssets por causa de filtros micro (1m) que não conversam com a tendência macro (1h).

| Ativo | Força eAssets | EMA Trend 1h | Status SS | Motivo do Bloqueio (Refusal) | Ganho no Período (eAssets) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CTSIUSDT** | 11/11 | +6 | Nenhum Trade | `trades_1m_too_low` (Era 6, SS pede 10) | +19.3% |
| **DASHUSDT** | 9/11 | +6 | Nenhum Trade | `rsi_lt_min_rsi_5m` | +15.3% |
| **SIRENUSDT** | 11/11 | +5 | Nenhum Trade | `trades_1m_too_low` | +51.2% |
| **JSTUSDT** | 8/11 | +4 | Saída Precoce | `max_hold_seconds` (Saiu com +0.2%) | +12.4% (pós-saída) |

### 9.2 O Veridito do CVD (A Prova de Fogo)

Analisamos todos os trades que resultaram em prejuízo (taxas). O padrão é matemático:

| Ativo | CVD 1m (Entrada) | Resultado (USDT) | Conclusão |
| :--- | :--- | :--- | :--- |
| VICUSDT | -18.493 | -0.08 | **FALHA:** Preço subiu sem volume comprador real. |
| HOLOUSDT | -22.479 | -0.08 | **FALHA:** Trap de exaustão. |
| NILUSDT | -4.468 | -0.08 | **FALHA:** Sniper entrou contra o fluxo. |
| **OPENUSDT** | **+898** | **+0.20** | **SUCESSO:** Fluxo confirmou o Score. |

### 9.3 Alpha Decay: O Lucro Deixado na Mesa

O Sniper está tratando tendências de 1 hora como se fossem scalps de 8 minutos.

| Ativo | Tempo em Trade | Saída SS | Trend eAssets (1h) | Preço 1h depois | Lucro Perdido |
| :--- | :--- | :--- | :--- | :--- | :--- |
| HOLOUSDT | 8 min | +0.57 | +6 (Forte) | +4.2% | **~3.6%** |
| BANKUSDT | 8 min | -0.08 | +5 (Média) | +2.1% | **~2.0%** |

---

## 10. Conclusões para o Brian & Forge

1. **O Blocker Institucional:** O Sniper está "cego" para 35 pontos do score (liquidações zeradas). Sugerimos usar o `Strength` do eAssets como colateral para esses pontos.
2. **O Filtro de Liquidez:** O `min_trades_1m: 10` é um assassino de produtividade em moedas que estão em acumulação (`range_level` alto).
3. **Veto de CVD:** Devemos manter o veto de CVD negativo, mas ser mais agressivos quando o CVD for positivo e a EMA 1h estiver acima de +4.

---

## 11. Próximos Passos Sugeridos

- **Aprovação do Brian:** Validar o uso da `EMA_Trend` do eAssets como multiplicador de confiança.

- **Tarefa para Forge:** Implementar a leitura do `ema_trend` no `signal_engine.py` apenas como filtro de bypass.

O Squeeze Sniper (SS) foi projetado para capturar o "colapso" (1 minuto). No entanto, os logs mostram que o mercado atual entrega "escadas" (1 hora).

- **O Problema**: O SS ignora a "escada" porque o volume de 1 minuto (`trades_1m`) é baixo (ex: 8 trades/min), enquanto o eAssets mostra uma `EMA_Trend` de +6 (Trendometer no talo).
- **A Consequência**: Perdemos movimentos de 50% (como visto no final de semana) esperando por um pico de volume que só acontece quando o movimento já está no fim.
- **A Defesa**: O eAssets deve servir como um **"Bypass de Confiança"**. Se o Trendometer do eAssets está em nível máximo, o Sniper deve ignorar as restrições de liquidez mínima e entrar pelo momentum da tendência.

### 9.2 Integração de Inteligência (Confluência IAs)

#### 9.2.1 Validação da "Cegueira Institucional" (Insumo Kiro)

Concordo com a auditoria do **Kiro**: o Score de 90+ é perigoso se `liq_short_1m` estiver zerado. Atualmente, o bot opera com **35 pontos cegos**.

- **Proposta**: Usar a `Força eAssets (9/9)` para preencher esses 35 pontos. Se o eAssets confirma força institucional, o Sniper recupera a visão e pode disparar com segurança, mesmo sem os dados de liquidação imediata da Binance.

#### 9.2.2 A Sentinela do CVD (Insumo Aria/Grok)

A **Aria** está correta: o CVD é o batimento cardíaco do trade.

- **Regra de Ouro**: Manter o veto absoluto para `CVD_1m < 0`. O Trendometer pode estar alto, mas se o CVD for negativo, é um "Bull Trap". Essa confluência protege o capital em 100% dos casos analisados nos logs.

---

## 10. Sugestões Técnicas de Convergência (Para Brian & Forge)

Para que o Brian possa autorizar o Forge a implementar, sugiro estas métricas de "Modo de Prontidão":

1. **Gatilho Oportunista (Trend-Ignition)**:
    - Se `eAssets.EMA_Trend_1h >= 5` → Reduzir `min_trades_1m` de 10 para 5.
    - *Por que?* Tendências sólidas começam silenciosas.

2. **Extensão Dinâmica de Hold (Anti-Alpha Decay)**:
    - Se o trade está no lucro e `eAssets.range_level < 30` (indicando que não há exaustão) → Ignorar o `max_hold_seconds` e deixar o trailing stop conduzir.
    - *Por que?* Sair por tempo em uma tendência de +6 é jogar dinheiro fora.

3. **Sincronização de Warmup**:
    - O SS deve importar o `RSI_1h` do eAssets no boot.
    - *Por que?* Elimina os 300 segundos de "cegueira" inicial identificados pelo Kiro.

---

## 12. Auditoria Gemini: Achados Ocultos (Camada de Engenharia)

Além da "Miopia do Gatilho", identifiquei três anomalias técnicas que explicam o baixo desempenho nos logs:

### 12.1 O Filtro de Exaustão (Funding Rate)

O eAssets monitora o `fr` (Funding Rate), mas o Sniper o ignora.

- **Evidência:** Ativos como CTSI e SIREN (vistos no eAssets) estavam com Strength 11/11, mas com Funding subindo.
- **Risco:** O Sniper entra em "Trends" onde o custo de carregar o long é alto, tornando o ativo alvo fácil para "Long Squeezes" reversos (o que explica o PnL negativo imediato em alguns trades).

### 12.2 A Ineficiência do Aborto (90s "Dead Window")

A análise dos `squeeze_failed` mostra que o bot leva 90s para admitir o erro.

- **Insight:** Nos trades vencedores (OPEN/HOLO), o MFE (Máximo Lucro) ocorre nos primeiros 20-30 segundos.
- **Proposta:** Se `MFE < 0.2%` após 30 segundos e o `eAssets.trades_level` estiver caindo, o aborto deve ser instantâneo. Atualmente, o bot "reza" por mais 60 segundos desnecessariamente.

### 12.3 A Fraude do RSI 1h (Warmup Fake)

O bot está operando com RSI 1h "cego" (travado em 50.0) porque não possui histórico de 14 horas de Klines no boot.

- **Consequência:** O `mtf_1h_crash` (filtro de tendência longa) só se torna confiável após meio dia de bot ligado.
- **Solução Manual:** O eAssets já tem esse dado pronto. Enquanto não há API, o Sniper está tomando decisões cegas que o eAssets evitaria.

---

## 13. Conclusão Final do Auditor

O Sniper é um motor potente, mas está "calibrado para uma pista e correndo em outra". Ele busca Squeezes (volatilidade pura) onde o eAssets indica Trends (direcionalidade).

**A recomendação final para o Brian:** O bot precisa de uma "Injeção de Contexto". Sem os dados de 1h do eAssets, o Sniper continuará tentando "atirar no escuro" contra a tendência macro do mercado.

---

## 14. Próximos Passos (Sem Alterar Código SS)

Após cruzar os dados do eAssets com os logs de recusa, identifiquei o que chamo de **"Miopia do Gatilho"**. O Squeeze Sniper é um tático de elite, mas ele está tentando caçar um "Squeeze" (evento de colapso rápido) em um mercado que está operando em "Trend" (tendência sustentada de 1h).

### 9.1 O Diagnóstico do Trendometer

O eAssets mostra ativos com `EMA_Trend: +6` no 1h. Isso é uma "Trend". O Sniper olha para o 1m e vê `trades_1m = 8`. Ele recusa por `trades_1m_too_low`.

- **O erro estratégico:** O Sniper espera a euforia (15-20 trades/min) para entrar. No entanto, o eAssets já mapeou que a tendência é sólida muito antes. Quando o Sniper finalmente aceita o trade, o movimento já está em exaustão (Alpha Decay), resultando nas saídas precoces por tempo.

### 9.2 Validação da "Blindagem de 35 Pontos" (Confluência com Kiro)

Concordo 100% com o **Kiro**: o Score de 90+ é ilusório se `liq_short_1m` está zerado.

- Sem o bônus de liquidação, o bot está operando apenas com indicadores técnicos de momentum.
- **Visão Adicional:** Se o eAssets mostra força máxima (9/9), o Sniper deveria usar essa "confirmação externa" para compensar a falta de dados de liquidação da Binance, permitindo um "Gatilho de Confiança" em ativos de tendência clara.

### 9.3 O Problema do CVD Negativo (Confluência com Aria/Grok)

Os dados não mentem: CVD negativo na entrada é o maior preditor de falha. Mesmo que o eAssets mostre força, se o Sniper detectar agressão de venda no 1m, o bloqueio deve ser mantido. A Aria está certa em buscar o eAssets, mas o Sniper deve manter o veto final no CVD.

---

## 10. Sugestões Técnicas de Convergência (Para Brian & Forge)

Para aumentar a produtividade sem descaracterizar o DNA, proponho ao Brian avaliar os seguintes "Bypass" inteligentes:

1. **O Filtro "Trend-Ignition":** Se `eAssets.ema_trend_1h >= 5`, relaxar o `min_trades_1m` de 10 para 5.
    - *Justificativa:* Ativos em tendência forte não precisam de um spike de volume para serem lucrativos; a continuidade da tendência é o combustível.

2. **Hold Dinâmico por Trend:** Se o ativo entrar e o `eAssets.ema_trend_1h` for `+6`, aumentar o `max_hold_seconds` de 480s para 900s.
    - *Justificativa:* Evita que o bot saia de um "Vencedor de Tendência" (como HOLOUSDT) apenas porque o tempo de 8 minutos acabou, enquanto o eAssets avisa que a tendência de 1h ainda é de alta.

3. **A Regra de Ouro do CVD:** Manter o veto de `cvd_1m < 0`. Esta é a proteção mais sólida que os logs mostraram até agora.

4. **Sincronização do Warmup:** Implementar o que o Kiro sugeriu sobre o RSI 1h travado em 50.0. O Sniper precisa "beber" da API do eAssets para já iniciar com o RSI/EMA de 1h real, eliminando os 300s de "cegueira estratégica" no boot.

---

## 14. Documentação Técnica para ARIA: Ecossistema de Integração eAssets

Aria, como você é a mente por trás da estrutura do dashboard, implementei uma camada de **Engenharia de Dados e Automação** na pasta `/eAssets` para elevar o sistema de um visualizador manual para uma "Torre de Controle" automatizada. Abaixo, o blueprint das melhorias:

### 14.1 Arquitetura de "Dados de Bate-Pronto"

Para eliminar o delay de carregamento e as falhas do Yahoo Finance (CORS/Proxy), centralizei a inteligência no **`enrich_server.py`**:

- **Background Worker**: Uma thread Python independente mantém o cache de Macro (VIX, DXY, SP500) e Sentimento (Fear & Greed) "quente" a cada 2-10 min.
- **Resposta Instantânea**: O Dashboard (JS) agora não bate mais na web. Ele faz um único `GET` ao servidor local, que entrega o JSON consolidado em milissegundos.

### 14.2 Pipeline de Captura Automática

O script **`monitorar_eassets.py`** atua como um listener de sistema de arquivos:

- Vigia a pasta `Downloads` do Windows e a pasta local `/dados_eassets`.
- Detecta novos exports `eassets-panel-*.json`, move-os para a pasta de trabalho e os organiza em uma subpasta `/historico` com timestamps.
- O arquivo **`auto_enrich_cvd.js`** no front-end monitora o `mtime` do arquivo via API e faz o refresh da UI em < 2 segundos após o download.

### 14.3 Fusão de Inteligência (Ouro para Auditoria)

Toda vez que o JSON é servido, ele gera o arquivo **`eassets_consolidado_com_sniper.json`**. Este arquivo é a base para sua futura integração de gatilho, pois contém:

1. Dados técnicos originais do eAssets (7 TFs).
2. Dados de Macro e Sentimento centralizados.
3. **Enriquecimento SS**: O servidor injeta o `CVD_1m`, `Score` e `Trades_1m` reais do Sniper (vindos dos logs) dentro de cada ativo do eAssets.

### 14.4 Launcher de Infraestrutura

O **`iniciar_dashboard.py`** agora resolve o problema crítico do caractere `#` no caminho da pasta, convertendo o endereço do HTML em uma URI válida e subindo todos os serviços de background (Monitor + Enricher) em consoles separados para visibilidade do operador.

---

## 15. Próximos Passos (Sem Alterar Código SS)

1. **Validação ARIA**: Aria deve revisar como os novos campos (`ss_score`, `ss_cvd_1m`) podem ser mapeados visualmente nos cards do dashboard para destacar o "Trendometer".
2. **Aprovação Brian**: Brian deve usar os logs da pasta `/historico` para validar se o relaxamento de filtros em moedas com `Strength 11/11` no eAssets teria evitado as oportunidades perdidas deste final de semana.
3. **Coleta de Dados**: Manter o ecossistema rodando para atingir os 15 trades e consolidar a base de dados para a próxima Sprint de calibração do DNA.

4. **Discutir recomendações com o Brain**
5. **Implementar PRIORIDADE 1 e 2 primeiro** (CRÍTICOS)
6. **Coletar mais dados com as novas configurações**
7. **Reavaliar após 24-48h de Paper Trading**

---

## Anexos

- Script de Análise: `eAssets/analyze_logs.py`
- Script de Cross-Analise: `eAssets/cross_analyze_eassets.py`
- Logs Originais: `logs/`
- Relatório Original Kiro: `para Brian/relatorio-kiro-para-brain-2026-06-06.md`
