# 🎯 Squeeze Sniper — Contexto Mestre do Projeto

> **Instruções de uso:** Cole este documento no início de qualquer conversa nova com o Claude para retomar o projeto do zero sem perder contexto. Atualize a seção "Estado atual" sempre que houver evolução relevante.

---

## 🤖 Sobre o projeto

- **Dono:** Doreto
- **Projeto:** Bot de trading algorítmico — *Squeeze Sniper*
- **Exchange alvo:** Binance Futures (USDM)
- **Estágio atual:** Avançado, em modo paper trading / (testnet vamos validar em um próximo estágio se vamos seguir ao testnet ou ao LIVE com capital muito baixo)
- **Objetivo:** Exponencializar capital capturando long squeezes — colapsos de liquidação institucional em futuros da Binance

---

## 🔄 Estrutura de sessões de trabalho

O projeto roda em **2 sessões paralelas do Claude** com objetivos complementares:

| Sessão | Ambiente | Foco |
|--------|----------|------|
| **Brain** `Agente Brain — Squeeze Sniper · Estratégia & Evolução` | Claude.ai (trabalho / mobile) | Estratégia, análises, ideias, documentação, cruzamento de dados |
| **Forge** | Laptop pessoal (Antigravity) | Implementação, polimento de código, testes, calibrações, revisões |

> O **documento mestre** é a ponte entre as duas sessões. Deve ser atualizado e compartilhado sempre que houver evolução relevante em qualquer uma delas.

### 🤝 Protocolo de colaboração Brain × Forge (ratificado pelo Forge — 03/06/2026)

**Regra 1 — Quem escreve o quê**
- Brain escreve em `tasks.md`: demandas + evidências nos logs
- Forge executa e marca como concluído com arquivo/linha alterado
- Sem essa separação vira duplicação e ruído

**Regra 2 — Prioridade de conflito**
- Se Brain sugere algo que contradiz o código que Forge conhece por dentro → Forge investiga primeiro
- Só implementa com evidência confirmada
- Exemplo aplicado: achados #3 e #4 do Brain foram descartados após verificação no código

**Regra 3 — Contexto mestre versionado**
- `context.md` precisa ter data e versão em cada atualização
- Brain não pode passar estado desatualizado para sessões futuras
- Versão atual: v4.26 · 12/06/2026

**Fluxo contínuo:**
```
Brain (análise)                    Forge (execução)
     ↓                                    ↓
     ├── tasks.md (demandas+evidências) ──► executa
     │                                    │
     ◄── tasks.md (concluído+arquivo) ────┤ marca done
     │                                    │
     └── context.md versionado ───────────┘ memória compartilhada
```

---

## 🏗️ Arquitetura de integração Brain → Forge

### Backbone: dois repositórios GitHub

**Repositório privado — código do bot:**
`https://github.com/vjdoreto/squeeze-sniper` (privado)
```
squeeze-sniper/
├── context.md          → documento mestre (sempre atualizado)
├── tasks.md            → fila de demandas Brain → Forge
├── src/                → código do bot (guardado pelo Forge)
├── docs/               → manifesto, DNA, roadmap
└── .gitignore          → bloqueia: .env, backups/, logs/
```

**Repositório público — colaboração Brain × Forge:**
`https://github.com/vjdoreto/squeeze-sniper-brain` (público)
```
squeeze-sniper-brain/
├── context.md          → espelho do documento mestre
├── tasks.md            → espelho da fila de tarefas
└── reports/            → análises do Brain por data
```
- Contém **apenas MDs** — zero código, zero dados sensíveis
- `.gitignore` bloqueia tudo exceto `.md` — proteção permanente
- Sincronizado pelo Forge após cada sessão junto com o repo privado
- Conectado ao **Claude Projects (Brain)** para acesso automático ao contexto

**Fluxo de trabalho:**
1. Brain gera análise ou demanda → escreve em `tasks.md`
2. Forge lê as tasks, implementa e commita o código
3. Forge traz resultado de volta ao Brain (diff / código / logs)
4. Brain analisa, documenta e atualiza `context.md`
5. Forge commita em ambos os repos — privado (código) e público (MDs)

### Fase 2 — Automação via Claude API (futuro)
Quando evoluir para agentes conversando de verdade:
- Script Python no Forge lê `tasks.md`
- Chama Claude API com o contexto completo
- Escreve resposta/resultado de volta no repositório
- Brain lê e dá continuidade estratégica

### Fase 3 — Terceiro agente (planejado)
A ser definido — expansão natural do sistema Brain + Forge.

---

## 🧠 Estratégia central

O bot funciona como um **sniper de long squeezes**: identifica o momento em que posições compradas alavancadas estão sendo forçadas a fechar (liquidação em cascata), gerando uma avalanche de ordens de venda e busca frenética por liquidez.

A ideia é **embarcar junto com os grandes players** nesse movimento, aproveitando o momentum do colapso institucional como uma sardinha que surfa a onda dos tubarões.

### Lógica de entrada (confluência de sinais)
Todos ou a maioria destes sinais devem estar ativos simultaneamente para o motor disparar:

| Indicador | Condição para entrada |
|-----------|----------------------|
| OI (Open Interest) | Subindo — novas posições entrando |
| LSR (Long/Short Ratio) | Caindo — shorts dominando / longs sendo fechados |
| EXP_BTC (força vs BTC) | Positivo — ativo ganhando força contra o BTC |
| HFT Activity | Alto — presença de alta frequência detectada |
| Trades/min | Alto — atividade intensa no ativo |
| RSI | Forte (acima de 60–70) |
| CVD (Cumulative Volume Delta) | Subindo — pressão compradora líquida |
| Liquidações em massa | Subindo — confirmação do colapso |

---

## 📊 Motor de score (Squeezometer)

- O bot calcula um **score de 0 a 100** para cada ativo em tempo real
- Score ≥ 90 dispara entrada (baseado nos trades analisados: QNTUSDT score 90, NEARUSDT score 95)
- O DNA do trade é registrado no log: `EXP | OI_trend | BTC_rel | Trades/1m | LSR_trend | LSR_chg`
- Existe um **Squeezometer global** (0–100) que mede atividade institucional geral do mercado — alertas disparam acima de 80

---

## 📱 App de referência analisado

Foi analisado o JSON `eassets-panel-20260602-182316.json` de um app de rastreamento de mercado (não faz trades automáticos) que Doreto usa como inspiração.

### Estrutura do JSON
- **34 símbolos** monitorados na Binance USDM
- **7 timeframes simultâneos:** 1m, 5m, 15m, 30m, 1h, 4h, 1D
- **Setup:** `Doreto` (configuração personalizada)

### Campos cobertos pelo app de referência

| Campo | Descrição |
|-------|-----------|
| `price` | Último preço negociado |
| `price_change` | Variação % no período |
| `fr` | Funding rate (%) |
| `oi` | Open Interest em USD |
| `oi_trend` | Ângulo normalizado da tendência do OI (exponencial) |
| `lsr` | Long/Short Ratio dos top traders |
| `lsr_trend` | Ângulo normalizado da tendência do LSR |
| `exp_btc` | Ângulo normalizado da tendência de preço pareada com BTC |
| `exp` | Ângulo normalizado da tendência de preço em USD |
| `rsi` | RSI padrão |
| `trades` | Número de trades no período |
| `trades_minute` | Frequência de trades por minuto (normalizada) |
| `trades_second` | Frequência de trades por segundo (normalizada) |
| `range_level` | Força de acumulação antes do breakout (0 = sem acumulação) |
| `trades_level` | Spike de atividade vs baseline recente por timeframe |
| `ema_trend` | Score de alinhamento de 4 EMAs: -6 a +6 |

> **Observação:** OI e LSR só estão disponíveis no timeframe **5m** neste JSON. Os demais timeframes não têm esses campos.

### Campos que o Squeeze Sniper tem e o app NÃO tem (diferenciais)
- CVD (Cumulative Volume Delta)
- Liquidações em massa em tempo real ⚠️ *(coleta de dados para os cálculos ainda é duvidosa no Squeeze Sniper — precisa de atenção especial ou correções na lógica)*
- Detecção direta de HFT

---

## 🔍 Gaps identificados no bot (vs app de referência)

### 1. Confluência multiframe ausente ou incompleta
O app avalia cada ativo em 7 timeframes simultaneamente. O bot provavelmente usa 1–2 timeframes para decidir a entrada. Adicionar alinhamento multiframe ao score pode reduzir falsos positivos drasticamente.

### 2. `ema_trend` não implementado
Score de -6 a +6 baseado no alinhamento de 4 EMAs (fast, slow, very slow, ultra slow). É um filtro de tendência poderoso que o app usa e o bot não tem.

### 3. `range_level` não implementado
Mede acumulação antes do breakout. Um valor alto antes da squeeze indica pressão represada — entrada de maior qualidade.

### 4. `trades_level` por timeframe
Spike de atividade normalizado por baseline recente em cada timeframe. Mais robusto que contar trades brutos.

---

## 📈 Análise dos trades (paper trading — 02/06/2026)

### Resumo da sessão
- **Equity inicial:** $1.000 USDT
- **Equity final:** $1.000,07 USDT
- **Trades:** 17 total (14W / 3L)
- **Win rate:** 82,35%
- **Lucro líquido:** ~$0,07 — praticamente zero apesar do bom win rate

### Problemas críticos identificados *(já sendo tratados na sessão Antigravity)*

#### ❌ Problema 1 — Fees comendo o lucro inteiro
Margem de entrada de $10 por trade (1% da banca de $1k) é pequena demais. As fees de $0,08–$0,40 por trade consomem todo o ganho em movimentos pequenos.

**Exemplo real:**
- SAHARAUSDT: PnL +0,29% mas pagou $0,40 de fee — trade de graça para a exchange
- BANKUSDT: PnL +0,02% ($0,00) com $0,08 de fee — prejuízo real

**Solução:** Aumentar margem por trade para $30–50 (3–5% da banca).

#### ❌ Problema 2 — Trailing saindo cedo demais
O trailing stop está ativando antes do movimento principal terminar.

| Trade | MFE (máx favor) | Capturado | Perda de captura |
|-------|----------------|-----------|-----------------|
| BIOUSDT | 4,75% | 3,34% | -1,41% |
| ENAUSDT | 6,00% | 4,59% | -1,41% |
| VICUSDT | 4,94% | 1,42% | -3,52% |

**Solução:** Trailing só ativa após X% de lucro, com distância maior nos primeiros segundos.

#### ❌ Problema 3 — MAE alto em vários trades
| Trade | MAE (máx adverso) | Observação |
|-------|------------------|------------|
| VICUSDT | -24,63% | Entrada prematura ou sinal incompleto |
| BANKUSDT | -15,51% | Stop muito folgado |
| GPSUSDT | -3,81% | Qualidade WEAK |

**Suspeita:** Entradas com confluência parcial (sinal disparou sem todos os indicadores confirmados).

#### ❌ Problema 4 — Squeezometer zerado na maior parte da sessão
O Squeezometer ficou em 0/100 durante quase toda a sessão, com apenas 2 alertas pontuais (80 e 81). Pode indicar cálculo incorreto ou threshold muito alto.

### Trades de qualidade WEAK identificados
- GPSUSDT: PnL -0,39% | MAE -3,81% | MFE apenas 1,01%
- QNTUSDT: PnL -0,04% | MAE -0,35% | MFE 1,62% — saiu em 1m23s

---

## 🔬 Análise eAssets — 03/06/2026 · 17h05 (mercado de sangue)

### Contexto de mercado
BTC sangrando · USDT.D forte (saída de capital) · BTC.D estável · Universo: 43 símbolos Binance USDM

### Descoberta principal — altcoins desacoplando do BTC

| Métrica | Valor | Interpretação |
|--------|-------|---------------|
| EXP_BTC:1m positivos | 36/43 (84%) | Altcoins ganhando força vs BTC |
| EMA trend máxima (6/6) | 31/43 (72%) | Tendência altista intacta na maioria |
| Candidatos squeeze (OI+ · LSR- · EXPBTC+) | 36/43 | Pressão institucional generalizada |
| RSI médio do universo | 53.8 | Neutro — sem euforia, sem pânico |
| LSR tendência forte negativa (<-5) | 29/43 | Shorts dominando — squeeze latente |

> Mercado de sangue no BTC = paraíso para o SS. O dinheiro não saiu de cripto — está rodando dentro do universo altcoin gerando liquidações em cascata.

### Tier 1 — Anomalias explosivas detectadas

| Símbolo | EXP_BTC:1m | EXP_BTC:1h | OI trend | LSR trend | Trades/1m |
|---------|-----------|-----------|----------|-----------|-----------|
| OPNUSDT | 23.75 | 151.01 | 198.85 | -104.24 | 6.584 |
| MAGMAUSDT | 2.84 | 111.89 | 52.33 | -42.04 | 2.728 |

### Tier 2 — Força multiframe confirmada (4 TFs alinhados)
WLDUSDT · USUSDT · INUSDT · BIOUSDT — todos com EXP_BTC positivo em 1m, 5m, 15m e 1h simultaneamente.

### 💡 Lição crítica — filtro de divergência temporal (novo conceito)

**O problema identificado:** ARUSDT perdeu -22.59% hoje (MFE = 0, max_hold). No snapshot de 17h05, o ARUSDT tinha EXP_BTC:1m = -2.47 (fraqueza pontual) mas EXP_BTC:1h = +42, OI = 21, LSR = -16. O bot entrou no 1m fraco sem considerar que o TF maior estava fortíssimo — entrou na hora errada do movimento certo.

**A solução — modo standby por divergência de timeframe:**

```
SE EXP_BTC:1m < 0
E EXP_BTC:15m > 10 E EXP_BTC:1h > 15
ENTÃO:
  → NÃO entra
  → Marca ativo em STANDBY
  → Aguarda EXP_BTC:1m virar positivo
  → Entrada executada com confluência completa
```

Este é o padrão de entrada de qualidade máxima — momentum de curto prazo alinhando com tendência maior intacta. Eliminaria a maior parte dos trades com MFE = 0 registrados na sessão de hoje.

---

## 📋 Estado real do sistema — verificado pelo Forge (03/06/2026)

> Divergências identificadas entre context.md e código real. Fonte: veredito do Forge após leitura do context.md v2.6.

| Item | Context.md dizia | Estado real | Ação |
|------|-----------------|-------------|------|
| Repo structure | `squeeze_sniper/` e `logs/` como subpastas | Tudo na raiz com `.gitignore` bloqueando `logs/` e `backups/` | Atualizado nesta versão |
| HFT Penalty floor | Pendente | ✅ Implementado — `$20` com guard `min($20, capital × 10%)` | ✅ |
| MAE de -1.40% nos winners | Brain identificou como padrão suspeito | É o `trailing_stop_distance_pct = 1.5%` funcionando corretamente — não é bug | Documentado |
| Filtro divergência temporal | Documentado no Brain, não implementado | Confirmado pelo Forge como válido — vai para Sprint 2 após dados dos fixes atuais | Sprint 2 |
| Score opera só em 5m | Identificado como gap | Confirmado pelo Forge — limitação real | Sprint 3 (backlog) |

### Implementações do Sprint 1.5 — executadas pelo Forge

| Implementação | Arquivo | Linha |
|--------------|---------|-------|
| `rsi_5m` exportado no signal dict | `signal_engine.py` | L755 |
| `ob_imbalance` exportado no signal dict | `signal_engine.py` | L757 |
| `liq_cascade` threshold $5k → $500 | `metric_engine.py` | L700 |
| `mae_guard` + `squeeze_aborted` | `paper_tracker.py` | — |
| Trailing callback adaptativo 50%/75% | `paper_tracker.py` | — |
| HFT floor $20 com guard | `paper_tracker.py` | L734 |
| DrawdownManager resetado | `logs/risk_state.json` | — |
| Git inicializado — commit a8ae357 | repo `vjdoreto/squeeze-sniper` | 95 arquivos |

### Insight validado pelo Forge — divergência temporal ARUSDT

O Brain identificou: ARUSDT com EXP_BTC:1m negativo mas 1h fortíssimo = entrou no momento errado do movimento certo. O Forge confirmou: é exatamente o padrão dos max_hold com MFE=0 de hoje. O filtro de divergência temporal está documentado para Sprint 2.

---

## 🔬 Análise forense dos logs — 03/06/2026

> Análise de 20 arquivos de log: paper_closed.jsonl (40 trades), signals.jsonl (67), signal_refusals.jsonl (22.196), liquidation_history.jsonl, throttle_state.json, risk_state.json e demais.

### ⚠️ Achado #1 — Liquidações zeradas — PARCIALMENTE CORRETO (veredito Forge)

```
liq_short_1m  = 0 em 67/67 sinais
liq_cascade   = False em 40/40 trades
liquidation_history.jsonl = 1 linha com value=0.0
```

**Veredito Forge:** Pipeline de liquidações está funcional. Os valores foram zero porque o mercado estava quieto hoje — sem eventos acima do threshold atual de $5k. **Fix real:** baixar threshold de `liq_cascade` de $5k para $500 no Sprint 1.5 para capturar eventos menores e validar a coleta.

### ~~🔴 Achado #4 — bug de logging~~ — INCORRETO (veredito Forge)

~~O evento `paper_open_abort_weak_score` loga `score=0` mas o campo correto é `signal_score`.~~

**Veredito Forge:** Campo `signal_score` já estava sendo logado corretamente. Brain leu o campo errado no debug. Nada a fazer.

### ✅ Achado #2 — DrawdownManager ativo com risco ×0.5 — CONFIRMADO E AGRAVADO (veredito Forge)

`risk_state.json`: `consecutive_losses=3` (Forge confirmou: eram 4), `risk_multiplier=0.5`, `trading_paused=false`. **Já resetado pelo Forge** — `consecutive_losses=0`, `risk_multiplier=1.0`. Próxima sessão começa com margem cheia.

### ~~🔴 Achado #5 — Throttle encolhendo o universo~~ ⚠️ ESTADO DESATUALIZADO (veredito Forge)

~~49 símbolos bloqueados no `throttle_state.json` ao final da sessão.~~

**Veredito Forge:** Brain leu estado desatualizado. Throttle é resetado automaticamente a cada nova sessão. Sem problema real.

### 🎯 Preditores reais de qualidade — descobertos nos dados brutos

Estes são os únicos diferenciadores estatisticamente relevantes encontrados entre winners e losers:

| Preditor | Winners | Losers | Diferença | Ação |
|----------|---------|--------|-----------|------|
| `trades_1m` | 95.5/min | 58.2/min | +37.4 | Adicionar peso explícito no score |
| `MAE inicial` | -4.5% | -8.8% | +4.3% | MAE gate nos primeiros 60s |
| `Duração` | 199s | 354s | -155s | Stop por tempo após 240s |
| `score` | 96.4 | 95.7 | 0.7pts | **Inútil como preditor** |

**Win rate por MAE inicial:**
- MAE < 2%: **WR 78%** (9 trades)
- MAE < 5%: **WR 61%** (23 trades)
- MAE < 8%: WR 57%

**Conclusão:** Trades rápidos com MAE baixo e alto trades_1m ganham. O score não distingue nada disso.

### 🎯 As 3 ações mais impactantes (em ordem)

1. **Corrigir pipeline de liquidações** — `liq_short_1m_stable` sempre zerado. Investigar `SymbolStore` no `data_engine.py`. Com liquidações reais, o score passa a diferenciar squeezes verdadeiras de falsas.
2. **Adicionar trades_1m como peso explícito no score** — o único indicador que diferencia winners de losers nos dados reais. Ativos com >80 trades/min têm WR significativamente maior.
3. **Resetar DrawdownManager antes de nova sessão** — `consecutive_losses=3`, `risk_multiplier=0.5` ainda ativo. Deletar ou resetar `logs/risk_state.json` antes de rodar nova sessão limpa.

---

## 🔄 Cruzamento Brain × Forge — 03/06/2026

### Relatório do Forge (40 trades analisados)

| Métrica | Valor |
|---------|-------|
| Total trades | 40 |
| Win Rate | 42.5% (17W / 23L) |
| PnL total | -$1.74 |
| PnL winners | +$8.46 |
| PnL losers | -$10.20 |
| Profit Factor | 0.83 |
| Avg MFE | +5.19% |
| Avg MAE | -6.98% |
| Captura MFE | -24.2% (negativo — lucro devolvido) |

### Causa raiz confirmada — max_hold (Forge)

13 trades × 481s exatos × WR 0% = -$9.15 (52% de todo o prejuízo). Sem os 13 max_hold: WR seria 62.96% e PnL +$7.41. O sistema é rentável quando o trailing funciona.

### ✅ Fixes já implementados pelo Forge

| Fix | Arquivo | Descrição |
|-----|---------|-----------|
| `mae_guard` | paper_tracker.py | Sai se PnL < -2% e MFE < 1% após 120s |
| `squeeze_aborted` | paper_tracker.py | Sai se PnL < -1.5% e MFE < 0.5% após 120s |
| Trailing callback adaptativo | paper_tracker.py | 50% quando MFE ≥ 3%, 75% abaixo |
| Paridade paper → live | live_tracker.py + sniper.py | Mesma lógica no live |

**Projeção pós-fixes:** WR ~68% · PnL +$9–11 por sessão similar

### 🔴 Descoberta nova e crítica do Forge — Score não discrimina

Score médio winners: ~96 · Score médio losers: ~96 · Diferença: **0.7 pontos**

O score atual é inútil como preditor de qualidade de trade. Melhorar o score é mais urgente que qualquer ajuste de parâmetro. O Brain identificou o porquê: `liq_short_1m_stable` e `liq_cascade` (35pts potenciais) podem estar zerados.

### Contribuições exclusivas do Brain — para implementar no Forge

1. **Filtro de divergência temporal** — EXP_BTC:1m negativo mas 15m/1h forte = modo standby, não rejeição. Seria entrada de qualidade máxima quando 1m alinhar
2. **Mercado de sangue é oportunidade** — 84% dos ativos positivos vs BTC mesmo com BTC caindo. O SS não precisa de bull market
3. **Validar liq_short_1m_stable** — se zerado, o score está cego no indicador mais importante do DNA (WebSocket forceOrder existe mas campo estável não rastreado no data_engine)

### Roadmap consolidado — ROADMAP_LIVE_V4.3.0 (commit 943570c · 03/06/2026)

Documento autoritativo único — reconciliação Forge × Brain. Arquiva versão v4.2.5.

| Sprint | Objetivo | Status |
|--------|----------|--------|
| 1 | Validação v4.2.5 — análise 40 trades | ✅ Concluído |
| 1.5 | Fixes críticos pré-coleta (Brain → Forge) | ✅ Concluído |
| 2 | Correlation Guard + margem segurança + Sprint 2C/2D | 🔄 Próximo |
| 3 | Liquidity Guard | ⏳ Pendente |
| 4 | 50+ trades — validação estatística | ⏳ Pendente |
| 5 | Dry-run live | ⏳ Pendente |
| 6 | Live gradual ($0.05) | ⏳ Pendente |
| 7 | Scale-up $5 → $100 | ⏳ Pendente |

**O que o Brain adicionou com valor real (aceito pelo Forge):**
- Sprint 1.5 — fixes críticos, todos executados hoje
- Sprint 2D — filtro de divergência temporal EXP_BTC:1m vs 15m/1h
- Sprint 2C — MAE gate 60s (condicional — só após 20+ trades confirmarem)

**O que o Forge filtrou do Brain (descartado com justificativa):**
- CVD/OI zerados — não era bug, logging gap
- Logging de aborts — não era bug
- Throttle — estado desatualizado
- MAE gate 60s obrigatório — amostra de 9 trades insuficiente

**KPIs mínimos para GO ao LIVE (Sprint 4):**
- ≥ 50 trades coletados
- Win Rate ≥ 60%
- Profit Factor ≥ 1.5
- Max Drawdown ≤ 12%
- Captura MFE ≥ 50%
- Nenhum trade com loss > 8%

**Próximo passo imediato:** coletar 20+ trades com regime atual (mae_guard, sizing $20, liq_cascade $500) → trazer logs ao Brain para análise → se padrões confirmados → Sprint 2.

---

## 🔧 Sprint 12/06/2026 — 4ª Sessão: Estratégia Path B + Backlogs (v4.26)

### Sessão Brain × ARIA × Doreto — estratégia e backlogs

Sessão sem código. Foco em análise estratégica e planejamento.

**Brain — B-51 a B-56 adicionados ao backlog:**
- B-51: RIFUSDT-type (lsr_trend flat com CVD explosivo) — evidência inicial
- B-52: absorvido por B-56
- B-53: proposta de DNA freeze (coleta forçada 50 trades)
- B-54: questão estrutural — o Squeezometer discrimina?
- B-55: ring buffers sub-minuto reafirmados como prioridade pré-Live
- B-56: Path B Momentum Rider — proposta formal Forge × Doreto, definição de 4 critérios, checklist de pré-requisitos, E-01/E-04 absorvidos

**ARIA — E-01 e E-04 concluídos:**
- E-01 (validação edge Path B): 28% bruto → 60% com 4º critério (lsr_trend:1h ≤ 0). N=14, 1 dia. Case model: ESPORTSUSDT +12.7%/+58.5%.
- E-04 (universo candidato): ~40 símbolos mapeados em Tier 1-3. Zero instáveis.
- A-06/A-07/A-08/A-09 adicionados ao backlog ARIA para continuidade.
- Script `aria/scripts/analyze_path_b.py` disponível para novos snapshots.

**Decisão estratégica registrada:** Path B entra em desenvolvimento apenas após Path A atingir 50+ trades com WR ≥ 55% e PF ≥ 1.3. Estudos ARIA continuam em paralelo.

---

## 🔧 Sprint 12/06/2026 — Análise Profunda + 8 Fixes (v4.25)

### Origem
Brain realizou análise profunda dos 27 trades do dia (WR 33%, PnL -25.15 USDT). Dois eventos catastróficos (ESPORTS -43%, ENJ -34%) distorceram o P&L. Brain identificou 4 bugs/gaps críticos + 4 melhorias.

### Fixes implementados (todos commitados e em produção)

| Fix | Commit | Descrição |
|-----|--------|-----------|
| D-URGENTE-1 SL fill correto | `7ebc3b8` | exit_price = sl (não tick). Slippage artificial 10-13% PnL por SL eliminado |
| D-HIGH-1 CVD floor cascade | `d256018` | cascade não bypassa CVD < -10%. ENJ loser (cvd=-0.56%) seria bloqueado |
| D-MEDIUM-2 CVD saturado | `d256018` | cvd_change_pct ≥ 950 → gate cvd_data_saturated. TIA/RIF-type bloqueados |
| D-HIGH-2 Throttle 4h pós-SL | `d2eac09` | SL hit → extend_cooldown 4h. ESPORTS não voltaria 108min depois |
| E3-gate-final oi_accel cascade | `4129488` | oi_accel bypassed por cascade no gate final. ORCA/XPL-type desbloqueados |
| cvd_streak no ghost dict | `4129488` | Campo adicionado para auditoria Brain |

### Decisões permanentes registradas
- **Large caps com cascade=True → final_gate_fail CORRETO**: EXP gate protege SS de BTC/ETH/SUI/XRP. Liq de $14-168k absorvida sem movement. Design, não bug.
- **cvd_streak não bypassa por cascade**: streak=0 + cascade = spike isolado de CVD, não momentum sustentado. Gate correto.
- **cvd_negative_quarantine**: gate Sprint 3 renomeado. is_high_quality=True quando cascade=True → bypassa completamente. Brain monitora distribuição.
- **ema4h=-2 aguarda**: 4 trades WR=0% insuficiente. Monitorar 15+ trades antes de gate/penalidade.

### Hard Reset Paper executado
Estado limpo após todos os fixes. Coleta nova a partir de agora com DNA correto.
Arquivos deletados: risk_state.json · paper_opportunities.json · throttle_state.json
metric_state.json preservado (klines quentes).

### Critérios de reversão ativos
- D-HIGH-1: winner bloqueado por cvd_negative_cascade_entry → revisar threshold -10%
- E3-gate-final: WR < 40% em 10+ trades via bypass → reverter
- D-HIGH-2: símbolo relevante preso indevidamente no throttle 4h → revisar

---

## ⚙️ Operações do bot — procedimentos conhecidos

> Seção em construção — será expandida quando o código chegar ao Brain. O que está documentado aqui é o conhecimento operacional atual de Doreto.

### Reinicialização graciosa (restart)
Necessária após implementações do Forge via GitHub. Sequência conhecida:
1. Desligamento gracioso do bot (aguardar fechamento de posições abertas)
2. Fechar a janela do browser após X segundos (parâmetro a confirmar no código)
3. Reiniciar o programa

> ⚠️ Pendente: confirmar o tempo exato de espera e se há lógica de cancelamento de ordens pendentes antes do fechamento.

### Coleta limpa de dados (reset de sessão)
Necessária quando se quer iniciar uma nova sessão sem contaminação de dados anteriores. Sequência conhecida:

1. **backup_session** (nome a confirmar) — salva os dados da pasta `logs/` antes de limpar
2. **Limpar Paper Tracker** — comando no dashboard que zera os dados de paper trading
3. **HARD RESET** — limpa praticamente tudo (logs, estado, dados acumulados)

> ⚠️ Pendente: confirmar nomes exatos dos comandos e scripts, e se há dependências entre eles (ex: backup obrigatório antes do hard reset).

### Recomendação Forge — hard reset vs zerar paper_closed (04/06/2026)

**Não fazer hard reset — apenas zerar o paper_closed.**

O hard reset limpa também o histórico de klines, métricas acumuladas e o warmup gate (300s). Os primeiros minutos ficam cegos — sem baselines de OI, sem CVD histórico, sem trends. Os primeiros sinais após o reset têm qualidade inferior.

**O que fazer para coleta limpa:**
1. Dashboard → Limpar Paper Tracker (zera paper_closed.jsonl + posições abertas)
2. Verificar risk_state.json — confirmar consecutive_losses=0

`signals.jsonl` e `signal_refusals.jsonl` podem ficar — acumulam histórico e não afetam o comportamento do bot.

**Hard reset faz sentido quando:** há corrupção de estado, métricas completamente erradas, ou você quer iniciar uma nova fase de calibração do zero.

### Integração GitHub — restart (fluxo futuro Forge + Brain)
Quando a integração estiver ativa, o fluxo de deploy será:
1. Forge commita nova implementação no GitHub
2. Bot recebe sinal de atualização
3. Executa desligamento gracioso
4. Fecha browser após X segundos
5. Reinicia com novo código
6. Brain recebe confirmação e monitora primeiros trades

---

## 🧬 Análise do código — 03/06/2026

### Arquivos recebidos
`config.py` · `bot_state.py` · `market_view.py` · `metrics_snapshot.py` · `risk_manager.py` · `sizing_utils.py` · `main.py` · `data_engine.py` · `live_tracker.py` · `paper_tracker.py` · `signal_engine.py` · `sniper.py` · `web_dashboard.py`

### Motor de score — `calculate_fit_score()` em `market_view.py`

| Componente | Pts máx | Campo | Observação |
|-----------|---------|-------|------------|
| EXP_BTC descolamento 5m | +30 | `exp_btc:5m` | Maior peso — DNA principal |
| CVD % crescimento 5m | +25 | `cvd_change_pct:5m` | Combustível |
| OI % crescimento 5m | +20 | `oi_change_pct:5m` | Dinheiro novo |
| Cascata de liquidação bônus | +20 | `liq_cascade` | ⚠️ Coleta duvidosa |
| LSR % queda 5m | +15 | `lsr_change_pct:5m` | Shorts em pânico |
| EXP momentum 5m | +15 | `exp:5m` | Força do preço |
| Liquidações short 1m | +15 | `liq_short_1m_stable` | ⚠️ Coleta duvidosa |
| HFT burst 10s | +10 | `last_trades_10s` | Atividade HFT |
| OI aceleração 5m | +10 | `oi_accel:5m` | Aceleração do OI |
| EMA trend 5m | +10 | `ema_trend:5m` | Alinhamento médias |
| Range level 5m | +10 | `range_level:5m` | Pressão represada |
| RSI 5m | +10 | `rsi:5m` | Combustível técnico |
| OB Imbalance | +10 | `ob_imbalance` | Desequilíbrio livro |

> Total teórico: 200pts · Cap: 100 · **Score opera apenas em 5m — sem validação multiframe**

### 🔴 Bug crítico confirmado — HFT Penalty destruindo o sizing

A função `calculate_dynamic_risk_with_hft()` aplica penalidade linear quando `trades_1m < 15`:

```python
risk_pct = base_risk * (trades_1m / min_hft_threshold)  # min_hft = 15
```

**Impacto real nos trades de hoje:**
- 1 trade/min → risco 0.33% → margem $3.33
- 3 trades/min → risco 1.00% → margem $10.00
- 4 trades/min → risco 1.33% → margem $13.33

Isso explica o position sizing caótico de $1–$20 na mesma sessão. A penalidade foi criada para evitar squeezes falsos em ativos sem liquidez, mas está massacrando o sizing de ativos legítimos que passaram no score.

**Soluções propostas (Forge decide):**
- Opção A: Remover `calculate_dynamic_risk_with_hft()` do sizing — HFT já é componente do score (+10pts)
- Opção B: Reduzir `min_hft_threshold` de 15 para 5
- Opção C: Adicionar `min_margin_floor = 20.0 USDT` — nunca abrir posição menor que $20

### 🔴 Risco crítico — Score inflado sem dados reais de liquidação

Com `liq_short_1m_stable` e `liq_cascade` possivelmente zerados (coleta duvidosa), o bot perde 35pts potenciais do score. Um ativo com score 100 pode ser na realidade ~65pts de indicadores técnicos sem confirmação institucional real.

### 🔴 Filtro multiframe ausente no score

`calculate_fit_score()` opera exclusivamente com dados 5m. Os campos de 15m e 1h existem no `market_view.py` mas não são usados no score. O filtro de divergência temporal identificado pelo Brain não existe no código.

### 🟡 Kelly sem dados suficientes nas primeiras sessões

`calculate_kelly_risk()` só ativa após 10 trades fechados. Antes usa `base_risk_pct` fixo. Com win rate de 41%, o Kelly vai reduzir risco automaticamente nas próximas sessões.

### 🟡 DrawdownManager pode estar ativo

Com 10 losses hoje, certamente ativou redução de 50% (3+ losses seguidos). Estado salvo em `logs/risk_state.json` — verificar antes de nova sessão.

### 🟢 O que está sólido

- `validate_config()` protege o DNA do bot contra configurações inválidas
- `DrawdownManager` com circuit breaker real (DD >= 15%)
- `SymbolThrottler` — máx 1 trade por símbolo por hora
- Grupos de correlação — máx 1 posição por grupo (L1, DeFi, AI, Meme etc.)
- Cache de score com TTL de 2s — thread-safe com RLock
- Arquitetura bem separada em módulos — base sólida para evoluir

---

## 📈 Análise dos trades (paper trading — 03/06/2026)

### Resumo da sessão
- **Equity inicial:** $1.000,00 USDT
- **Equity final:** $996,30 USDT
- **Trades:** 19 total (7W / 10L) — *relatório horário mostrou 17, mas foram identificados 19 no log*
- **Win rate:** 41,18% — queda crítica vs 82% do dia anterior
- **Prejuízo líquido:** -$3,70
- **Position sizing:** caótico — variou de $1,00 a $20,00 por trade sem padrão

### 🚨 Problema novo e crítico — `max_hold`
8 dos 10 losses foram fechados por `max_hold` (tempo máximo de posição esgotado). Desses, vários com MFE = 0.00% — o mercado foi contra imediatamente após a entrada e nunca voltou.

| Trade | Score | PnL | MFE | MAE | Motivo |
|-------|-------|-----|-----|-----|--------|
| INJUSDT | 96 | -9,86% | 0,66% | -10,38% | max_hold |
| RENDERUSDT | 100 | -6,82% | 0,39% | -8,12% | max_hold |
| ZROUSDT | 98 | -5,32% | 0,00% | -7,30% | max_hold |
| UNIUSDT | 100 | -3,82% | 0,00% | -2,42% | max_hold |
| AWEUSDT | 100 | -13,85% | 0,00% | -12,47% | max_hold |
| ZAMAUSDT | 98 | -5,44% | 0,36% | -4,04% | max_hold |
| NEARUSDT | 100 | -7,78% | 4,59% | -9,72% | max_hold |
| KAITOUSDT | 100 | -3,44% | 0,32% | -3,12% | max_hold |
| ARUSDT #2 | 88 | -22,59% | 0,00% | -25,18% | max_hold |

> Score 100/100 com MFE = 0 é um sinal de **falso positivo no motor de confluência** — os indicadores alinharam mas o movimento não aconteceu. O sinal provavelmente está disparando cedo demais ou em condição de mercado lateral.

### ✅ Padrão dos trades vencedores
Os trades limpos têm MAE baixo e MFE alto — o mercado foi a favor imediatamente:

| Trade | Score | PnL | MFE | MAE |
|-------|-------|-----|-----|-----|
| ARUSDT #1 | 95 | +12,14% | 15,91% | -1,40% |
| SUSHIUSDT | 100 | +7,99% | 12,56% | -1,40% |
| FILUSDT #2 | 100 | +5,61% | 8,53% | -4,49% |
| WLDUSDT | 93 | +4,56% | 5,97% | -4,98% |

> MAE de -1,40% repetindo nos melhores trades — pode ser o floor do trailing stop inicial. Trades com MAE ≤ 5% tendem a vencer; MAE > 8% tendem a perder.

---

## 📊 Análise dos trades — 04/06/2026 (18 trades)

### Resumo da sessão
- **Equity:** $1.000 → $993.55 · PnL -$6.45
- **Trades:** 18 total (5W / 13L)
- **Win Rate:** 27.8%
- **squeeze_failed:** 10 trades · WR 0% · -$9.52 — causa raiz
- **trailing_stop:** 7 trades · WR 71% · +$3.97 — continua funcionando
- **squeeze_aborted:** 1 trade · WR 0% · -$0.92

### squeeze_failed — o novo max_hold

Padrão idêntico ao max_hold da sessão anterior, só mais rápido. 10 trades · 90s exatos · 8/10 com MFE=0. Sem eles: WR 62.5% e PnL +$3.07.

O bot não está entrando tarde — está entrando no momento errado do movimento certo. O CVD explodiu DEPOIS da saída nos squeeze_failed:
- PUMPUSDT: cvd_1m = +4.7M após saída
- JSTUSDT: +183k · HEIUSDT: +41k

O sinal dispara no setup (OI subindo, LSR caindo) mas sem CVD confirmando agressão ainda.

### Alpha Decay — como é calculado

Cada coluna é calculada a partir do **preço de saída**, independente:
- **Variação Atual** = do preço de saída até agora (acumulado)
- **Após 5m** = variação nos 5 minutos imediatamente após a saída
- **Após 15m** = variação nos 15 minutos após a saída

Sem sobreposição entre TFs.

### Regressão no signal dict

`paper_closed.jsonl` desta sessão tinha apenas 8 campos no sinal (vs 22 no `signals.jsonl`). O signal completo existia na avaliação mas estava sendo truncado na serialização do trade fechado. **Fix implementado pelo Forge** (fix #3).

### sl_tp_guard — não é bug

`paper_ratio_sl_tp_guard_applied` ativou em 11/18 trades (61%). É o guard de ratio SL/TP mínimo 1:2.5. Quando TP calculado resulta em ratio < 2.5x, o sistema ajusta automaticamente para cima. Funcionando como projetado.

### Paradoxo do post_trade

Os snapshots pós-saída coletam `rsi_5m`, `cvd_1m`, `liq_short`, `oi_chg` — exatamente o que falta no sinal de entrada. O sistema mede os dados certos no momento errado.

### exp_btc como diferenciador pós-saída
- Winners: exp_btc 5m após saída = -0.026 (momentum esgotando — saiu certo)
- Losers: exp_btc 5m após saída = +0.002 (momentum continuou — entrou cedo)

---

## 🔧 Sprint 2 — fixes implementados (04/06/2026)

| Fix | Arquivo | Linha | Descrição |
|-----|---------|-------|-----------|
| WebSocket liquidações | data_engine.py | L381 | `!forceOrder@arr` global substituiu centenas de streams individuais que falhavam silenciosamente |
| Gate CVD anti squeeze_failed | signal_engine.py | L580 | `cvd_not_confirming` bloqueia entrada quando `cvd_change_pct < min_cvd_change_pct_no_cascade` sem liq_cascade |
| Signal dict completo | paper_tracker.py | L793 | 22 campos persistidos no paper_closed.jsonl — Brain terá dados completos |

**Parâmetro adicionado:** `min_cvd_change_pct_no_cascade: 1.0` em `preferences.json`

**Commit:** `7ac5d45` — context v3.0 + Manifesto v2.0 + Sprint 2 concluído

**Manifesto:** atualizado para v2.0 em `docs/Engenheiro e DNA do Sniper v2.0.md` com seções de Arquitetura Brain × Forge e GitHub.

### O que monitorar na próxima sessão
1. `liq_short_1m > 0` em algum sinal — fix #1 funcionou
2. Refusals `cvd_not_confirming` nos logs — fix #2 filtrando
3. Signal dict com 22 campos no `paper_closed.jsonl` — fix #3 ativo
4. squeeze_failed < 5/20 — gate CVD funcionando

---

## ⏳ Pendências — próximos passos

### ✅ Concluído pelo Forge — 03/06/2026
- [x] **max_hold eliminado** — `mae_guard` + `squeeze_aborted` implementados em `paper_tracker.py` e `live_tracker.py`
- [x] **Trailing callback adaptativo** — 50% quando MFE ≥ 3%, 75% abaixo — implementado
- [x] **Paridade paper → live** — fixes espelhados em `live_tracker.py` + `sniper.py`
- [x] **Análise de 40 trades** — relatório completo gerado pelo Forge
- [x] **Código do bot recebido e analisado** — Brain analisou 13 arquivos + 20 logs em 03/06/2026

### 🔴 CRÍTICO — confirmado pelos logs brutos
- [x] **Threshold liq_cascade** — ✅ baixado de $5k para $500 em `metric_engine.py` L700 · Sprint 1.5 executado
- [ ] **Resetar `logs/risk_state.json`** — DrawdownManager ativo com `risk_multiplier=0.5` (3 losses consecutivos). Deletar antes de nova sessão limpa para não herdar penalidade
- [x] **rsi_5m e ob_imbalance no signal dict** — ✅ exportados pelo Forge em `signal_engine.py` L755/L757 · próxima análise do Brain terá esses dados

### 🔴 Urgente — confirmado pelo código
- [ ] **Score não discrimina** — diferença de 0.7pts entre winners (96.4) e losers (95.7). Adicionar `trades_1m` como peso explícito — único preditor real encontrado nos dados (95 vs 58 trades/min)
- [x] **HFT Penalty floor** — ✅ implementado $20 com guard `min($20, capital × 10%)` em `paper_tracker.py` L734
- [x] ~~**Throttle encolhe universo**~~ — ⚠️ estado desatualizado · throttle é resetado automaticamente a cada sessão

### ✅ Sprint 3 — Brain EA-Sprint3 concluído (05/06/2026)

| Task | Descrição | Status | Commit |
|------|-----------|--------|--------|
| F-01 | Persistência cockpit Live | 🟡 Parcial — saldo/margem real-time pendente | `88104c3` |
| F-02 | Toggle Paper/Live colapso automático | ✅ | `51be306` |
| F-03 | Bracket tiers Binance no sizing | ✅ `_get_notional_cap()` | `88104c3` |
| F-04 | Squeezometer zerado relatórios horários | ✅ `squeeze_peak_1h` | `51be306` |
| F-05 | PaperAnalyzer threshold 30+ trades | ✅ `min_trades_for_calibration=30` | `96fb14e` |
| F-06 | Gráficos placeholder "aguardando trades" | ✅ | `51be306` |
| F-10 | daily_reset_window 21:00 BRT | ✅ Completo — 588 refusals confirmam. Relatório 20:50 BRT correto | — |
| F-11 | ghost_signals.jsonl near-misses | ✅ Score≥85, 22 campos incl. volume_quality + exp_btc_norm_1h | `b02700f` |
| EA-01 | min_trades_1m 2 → 10 | ✅ | `d5da930` |
| EA-02 | Gate combo trades_1m/oi_trend/lsr_trend | ✅ reason_codes individuais | `d4b01b0` |
| EA-03 | volume_quality no signal dict | ✅ `cvd_change_pct / (trades_1m + 1)` | `3f8b6c1` |
| EA-04 | exp_btc_norm_1h Z-score ARIA window=14 | ✅ metric_engine + signal_engine | `8b81a81` |

**Confirmação Forge — klines 1h BTC:** disponíveis no boot via `data_engine.py` L259/342. EA-06 pode ir no Sprint 3 sem nova infraestrutura.

**Parâmetros em produção — estado 05/06/2026:**

| Parâmetro | Valor atual | Obs |
|-----------|-------------|-----|
| `paper.signal.min_trades_1m` | **10** | Elevado de 2 (EA-Sprint3) |
| `paper.signal.min_cvd_change_pct_no_cascade` | **1.0** | Anti squeeze_failed |
| `paper.signal.min_cvd_change_pct` | **1.5** | Com cascade |
| `paper.signal.min_score` | **90** | Score mínimo entrada |
| `paper.signal.min_oi_trend` | **0.015** | Base (gate combo usa 0.008) |
| `paper.signal.max_lsr_trend` | **-0.002** | Base (gate combo usa -0.3) |
| `paper.execution.tp_pct` | **0.04** | TP 4% |
| `paper.execution.sl_pct` | **0.025** | SL 2.5% |
| `paper.execution.max_hold_seconds` | **480** | Máx 8 min |
| `paper.execution.partial_tp_breakeven_pct` | **0.35** | Fecha 35% no breakeven |
| `min_trades_for_calibration` | **30** | PaperAnalyzer só calibra ≥30 trades |

**Gates hard ativos (EA-Sprint3, sem bypass liq_cascade):**
- `trades_1m < 10` → `trades_1m_too_low`
- `oi_trend < 0.008` → `oi_trend_too_weak`
- `lsr_trend > -0.3` → `lsr_trend_not_negative`

**Campos observacionais novos no signal dict (sem gate):**
- `volume_quality` = `cvd_change_pct / (trades_1m + 1)`
- `exp_btc_norm_1h` = Z-score rolling window=14 de exp_btc:5m

**Paridade Paper ↔ Live:** ✅ Completa.

**Próximo passo:** aguardar 20+ trades com EA-Sprint3 ativo → logs ao Brain → análise discriminação gates + campos novos → Sprint 3 restante.

### 🟡 Sprint 3 — Pendente

- [ ] **F-01 saldo/margem real-time** — snapshot LiveTracker nos broadcasts WebSocket
- [ ] **Correlation Guard expandido** — 100+ símbolos · `src/risk_manager.py`
- [ ] **Margem de segurança Sniper** — `balance < usdt_amount * 1.1` quando > $100
- [ ] **MAE gate 60s** _(condicional)_ — só após 20+ trades confirmarem WR 78%
- [ ] **Filtro divergência temporal** — standby EXP_BTC:1m < 0 mas 15m/1h forte
- [ ] **Kelly floor** — verificar guard `min($20, capital×10%)` para kelly baixo
- [ ] **EA-06** — definir com Brain (infra 1h disponível)

### 🟢 Backlog — Sprint 4+

- [ ] **Liquidity Guard** — profundidade OB antes de entrar
- [ ] **50+ trades paper** — validação estatística GO/LIVE
- [ ] **Dry-run live** — `auto_pilot: false` 24h
- [ ] **Filtro multiframe no score** — `ema_trend:15m` e `ema_trend:1h`
- [ ] **Gate momentum sub-minuto** — ring buffers 10s/20s/30s AggTrade
- [ ] **Macro CMC** — USDT.D + BTC.D + Fear&Greed polling 5min

---

## 💡 Insights e observações relevantes

1. **Win rate não é o problema isolado** — foi 82% ontem e 41% hoje. O mercado lateral gera falsos positivos no motor. Consistência é o desafio real.
2. **A estratégia tem edge comprovado** — quando o sinal está certo (MAE baixo imediatamente), os ganhos são expressivos: +12%, +8%, +5,6%.
3. **O bot já está à frente do app de referência** em dados críticos (CVD, liquidações, HFT) — o gap é na inteligência de confluência multiframe.
4. **MAE alto = entrada prematura** — trades com MAE > 8% logo após entrada quase sempre perdem. Esse pode ser o filtro mais simples e eficaz a implementar.
5. **Score alto não garante direção** — scores 96–100 geraram losses com MFE = 0. O score precisa incorporar confirmação de momentum, não só confluência estática.
6. **`max_hold` é um sintoma, não a causa** — o bot está entrando em ativos que não se movem. O filtro de entrada precisa ser mais seletivo.
7. **MAE de -1,40% nos melhores trades** — esse valor se repete e pode ser o floor do trailing stop. Vale investigar se é um parâmetro hardcoded no código.
8. **Liquidações em massa são um diferencial crítico** — mas só se a coleta estiver correta. É o indicador que mais separa o Squeeze Sniper do app de referência e precisa de validação urgente.
9. **Mercado de sangue é o cenário ideal para o SS** — quando BTC cai e USDT.D sobe, o dinheiro não some, migra entre altcoins gerando liquidações em cascata todos os dias. O SS não precisa de bull market — precisa de volatilidade e desacoplamento.
10. **Filtro de divergência temporal é a próxima evolução mais importante** — EXP_BTC:1m negativo com 15m/1h positivos = ativo em compressão antes da squeeze. Entrar após o 1m alinhar é a entrada de qualidade máxima. Isso endereça diretamente o problema de MFE = 0 registrado hoje.

---

---

### 🔧 Sprint Forge — 09/06/2026 (continuação v4.0)

**B-35 — `mtf_1h_crash_threshold` configurável** · commit `d101ec8`

Gate `mtf_1h_crash` bloqueava entradas quando `exp_1h < -0.05` (hardcoded). Threshold movido para `preferences.json` para que Brain possa calibrar sem tocar no código.

| Arquivo | Mudança |
|---------|---------|
| `preferences.json` | `mtf_1h_crash_threshold: -0.05` em `paper.signal` e `live.signal` |
| `config.py` | Campo `mtf_1h_crash_threshold: float` em `BotConfig` + `load_config` |
| `src/signal_engine.py` | Parâmetro no construtor + `self.mtf_1h_crash_threshold` substituindo hardcode |
| `main.py` | Passagem `mtf_1h_crash_threshold=cfg.mtf_1h_crash_threshold` |

Valor atual: `-0.05` (paper e live idênticos). Brain calibra via JSON.

---

---

### 🔧 Sprint Forge — 09/06/2026 (fix RSI)

**fix(RSI) — `actual_window` 15 → 28** · commit `5dfbe93`

COMPUSDT aparecia com RSI:5m = 100 no dashboard (TradingView mostrava 56). Causa: janela de cálculo de apenas 15 candles — sequências de alta sem nenhuma perda retornam `avg_loss = 0 → RSI = 100` matematicamente correto, mas inútil. Aumentar para 28 (2× período padrão) dilui picos curtos.

Arquivo: `src/metric_engine.py:389` — `min(15, len(closes))` → `min(28, len(closes))`.

Não é dado corrompido nem buffer insuficiente — é limitação do cálculo simples (não Wilder smoothing). Correção conservadora que melhora fidelidade sem mudar a fórmula.

---

---

### 🔧 Sprint Forge — 10/06/2026 (bug simétrico F-12 + queue overflow + listener raw)

**fix(data): klines e aggTrades para futures_multiplex_socket** · commit `fde21af`

Bug simétrico ao F-12: `_listen_klines` e `_listen_agg_trades` usavam `multiplex_socket` (Spot) em vez de `futures_multiplex_socket` (Futuros). CVD e klines de **todos os trades anteriores** ao restart desta sessão foram calculados com dados do mercado Spot — inválidos para análise de Futuros. Teses T-01 a T-04 só podem ser validadas com trades coletados a partir desta correção.

Arquivo: `src/data_engine.py` — 2 linhas (L401 e L508).

**feat(tools): `tools/binance_raw_listener.py`** · mesmo commit `fde21af`

Listener WebSocket puro Binance Futures sem filtro. Captura por símbolo: `@aggTrade`, `@kline_1m`, `@markPrice`, `@bookTicker`. Stream global: `!forceOrder@arr`. Output: `tools/raw_logs/raw_YYYYMMDD_HHMMSS.jsonl`. Uso: `python tools/binance_raw_listener.py BTCUSDT VELVETUSDT STGUSDT`.

**fix(ws): `queue_size=10000` no BinanceSocketManager** · commit `d44e89d`

Overflow silencioso em spikes de volume — fila padrão insuficiente.

**fix(ws): `queue_size` → `max_queue_size`** · commit `cd7c5b3`

Nome correto do parâmetro na biblioteca `python-binance`. Fix de nomenclatura aplicado em `data_engine.py` e `tools/binance_raw_listener.py`.

---

### 🔧 Sprint Forge — 09/06/2026 (fix F-12 causa raiz)

**fix(F-12) — causa raiz definitiva do `liq_short_1m = 0`** · commit `ed54d36`

O stream `!forceOrder@arr` (liquidações de futuros) estava conectando no endpoint **Spot** (`stream.binance.com`) via `bsm.multiplex_socket()`. O servidor Spot aceitava a conexão silenciosamente mas nunca entregava eventos de futuros — por isso `"Liquidation WebSocket: Conectado"` nunca aparecia nos logs e `DIAG F-12 payload bruto` nunca logava.

Correção: `bsm.multiplex_socket()` → `bsm.futures_multiplex_socket()` (endpoint `fstream.binance.com`).

Arquivo: `src/data_engine.py:400` — uma linha.

Esta era a causa raiz real desde o início — não o cálculo de notional (`ap*z`), não o threshold, não ausência de liquidações no mercado. Com este fix ativo, `liq_short_1m`, `liq_cascade` e `liq_threshold` passam a ter dados reais pela primeira vez.

---

---

### 🔧 Sprint Forge — 09/06/2026 (fixes signal dict + RSI 1h)

**fix — `ema_trend_4h` no signal dict** · commit `affec99`

`ema_trend:4h` era lido pelo gate F-18 no MetricStore mas nunca exportado no signal dict. Brain via `signals.jsonl` enxergava `ema_trend = 0` (valor do 5m). Fix: adicionado `"ema_trend_4h": d.get("ema_trend:4h") or 0` nos dois blocos de construção do signal dict em `src/signal_engine.py` (ghost signal + sinal real).

**fix — `rsi:1h` travado em 50.0 após cache quente** · commit `270b20d`

Causa raiz: `_update_indicators` não era chamado durante o load do cache quente — apenas em `init_klines` (símbolos missing) ou `update_kline` (kline final). Para timeframe 1h, o próximo kline final demora até 60min. Se o cache foi salvo com `rsi:1h = None`, o campo ficava `None` por toda a sessão, caindo no fallback `or 50.0` do signal dict. Fix: após restaurar os klines do cache, iterar todos os símbolos/timeframes com buffer ≥ 5 candles e chamar `_update_indicators`. Arquivo: `src/metric_engine.py`.

---

---

### 🔧 Sprint Forge — 09/06/2026 (v4.5 — sessão Brain × ARIA × Forge)

**Migração Brain + ARIA para Antigravity (Claude Code)**

Agentes Brain e ARIA migrados do Claude Desktop para cá. Estrutura de pastas:
- `brain/` — BRAIN_CONTEXT.md, backlog-brain-doreto-v1.0.md (v3.4 · 47 itens)
- `aria/` — ARIA_CONTEXT.md, análises .md, indicadores .py, pasta eAssets/
- `AGENTS.md` — definição permanente dos 4 papéis e protocolos
- `tasks.md` — fila Brain → Forge

**Análise dos 4 trades de hoje (Brain × ARIA consenso)**

| Trade | Resultado | Exit | MFE | Achado |
|-------|-----------|------|-----|--------|
| ARUSDT | ❌ -$0.77 | squeeze_failed 90s | 0% | eAssets: ema_trend:4h=-6 — bot via 0 (gate F-18 cego) |
| PARTIUSDT | ❌ -$0.91 | squeeze_aborted 120s | 0.37% | Score=86 entrou (bug fit_score_min); eAssets: ema:4h=+6 ignorado |
| KATUSDT | ✅ +$0.50 | trailing 181s | 11% | Capturou só 22.8% — eAssets: EXP_BTC:1h=40.09 sinalizava múltiplas pernas |
| AIGENSYNUSDT | ✅ +$1.27 | trailing 181s | 7.28% | Captura 87% — trade modelo |

**fix(ema_trend_4h) — gate F-18 estava cego** · commit `c7edbf8`

`ema_trend_4h=0` em 3/4 trades enquanto eAssets mostrava -6 e +6 reais.
Causa: `_update_indicators` exigia `len(closes) >= 100` para calcular EMA trend.
Fix: reduzido para `>= 50`. Arquivo: `src/metric_engine.py:409`.

**Confirmação na próxima sessão:** verificar se `ema_trend_4h` aparece com valores ≠ 0 nos signals após restart.

**fix(fit_score_min) — score=86 entrava após troca de modo** · commit `562e172`

`_apply_runtime_mode` em `main.py:1498` lia `fit_score_min` da raiz do preferences.json (valor=20) em vez de `signal_node.get("min_score")` (valor=90). Toda troca de modo pelo dashboard sobrescrevia o threshold para 20.
Fix: `prefs.get("fit_score_min")` → `signal_node.get("min_score")`.

**Limpeza src/ — 10 arquivos mortos removidos** · commit `82fd193`

Scripts de auditoria one-shot nunca importados em produção. src/ agora tem 18 arquivos — todos ativos.

**B-48 adicionado ao backlog Brain**

Scripts automáticos `analyze_logs.py` (Brain) e `analyze_eassets.py` (ARIA) para substituir análise manual. Próxima sessão Brain define prioridade.

**Descoberta ARIA — EXP_BTC:1h > 30 = movimento de múltiplas pernas**

KATUSDT EXP_BTC:1h=40.09 → +17.93% em 15min pós-saída. Trailing 75% capturou só 2.51%. Tese nova: quando EXP_BTC:1h > 30, trailing atual é insuficiente. Aguarda 20+ trades para confirmar antes de virar gate/parâmetro.

**Macro eAssets 09/06/2026 23:44 UTC**
- BTC: -2.37% no dia · ema_trend:4h=-6 · rsi:1h=37.7
- 410/531 ativos com ema_trend:4h negativo (77%) — mercado bearish amplo
- 48/531 com ema_trend:4h positivo — ilhas de desacoplamento onde o SS opera

**Próximos passos (próxima sessão):**
1. Confirmar `ema_trend_4h ≠ 0` nos signals após restart com fix ativo
2. Confirmar `liq_short_1m > 0` — F-12 fixado em 09/06, ainda chegava zerado
3. Brain prioriza B-48 (scripts automáticos) no backlog
4. MTF — Sprint 5+ (pré-requisito EA-02)

---

---

## 🔧 Sprint 10/06/2026 — Sessão Forge + Brain + ARIA (v4.6)

### Diagnóstico de bloqueio (Forge)

Score máximo observado: **83**. Threshold: 85. Causa raiz dupla:
1. **lsr_trend_positive** gate cegava VELVETUSDT ($69k liq) antes do score — padrão demand breakout não reconhecido
2. **liq_cascade** (+20 pts) inacessível: `0.02×OI` floor dominante ($5M OI → floor $100k vs liq real $4k)

### Fixes implementados (todos com autorização Doreto)

| Fix | Commit | Impacto |
|-----|--------|---------|
| B-liq-cascade-tiers | `6154a7d` | OI-based tiers: <$1M→$500 / $1M-$10M→$2k / >$10M→$10k |
| B-34-bypass | `519b56d` | Bypass lsr_trend_positive quando liq>$20k + trades≥15 + cvd>2.0 |
| ema_trend:1h +5 pts bônus | `d089dce` | Discrimina pullback em tendência maior de bear pleno |
| AGENTS.md variante R-07 | `5f79921` | Brain/ARIA podem entregar diff pronto; Forge commita |

> ⚠️ `d089dce` foi commitado pela ARIA (violação R-07 #4). Código revisado e aprovado pelo Forge. Registrado em tasks.md.

### Análise ARIA — snapshot eAssets 10/06 23:12 UTC

Macro bearish: 79.1% dos 531 ativos com EMA:4h negativo. Apenas 28 ilhas de desacoplamento — universo exato do SS. Teses novas:
- **T-05**: range_level:1h ≥ 4 + EMA:4h ≥ 0 + EXP_BTC:1h > 5 → MFE médio 1.5× maior (campo não no pipeline SS — backlog)
- **T-06**: FR > +0.001 em ativo forte = catalisador de squeeze. `funding_rate` já no signal dict — ARIA pode auditar agora

### Estado ao final da sessão

- Bot aguardando restart para carregar os 3 fixes (`6154a7d`, `519b56d`, `d089dce`)
- Sem trades ainda (hard reset manual executado por Doreto — logs limpos, state preservado)
- Warmup concluído às 20:28:41 — bot ativo
- MDs todos atualizados, commits prontos para push

---

### 🔧 Sprint Forge — 11/06/2026 (B-score-ema1h + dashboard frontend)

**feat(B-score-ema1h): ema_trend_1h no signal dict** · commit `90d3e3b`

Campo ausente dos dois blocos de construção do signal dict em `signal_engine.py`. O bônus +5 pts em `market_view.py:102` (R-ARIA-03) já existia — gap era que `ema_trend_1h` não era exportado para `signals.jsonl` nem `ghost_signals.jsonl`. Fix: 1 linha adicionada em cada bloco (L257 ghost, L944 sinal real). Brain pode agora auditar `ema_trend_1h` × MFE após 30+ trades.

**fix(F-01): saldo/margem live — estado ⏳** · commit `2c15bfd`

`live.balance` chega como `{}` vazio nos primeiros broadcasts pós-boot. A condição anterior exibia `$0.00` falso. Fix: verificar `totalWalletBalance != null && > 0` antes de sobrescrever o display; mostrar `⏳` em cinza como estado intermediário honesto.

**feat(dashboard): ghost near-miss table + badge ema_trend_1h** · commit `9db0525`

- Painel Ghost Signals expandido com tabela dos últimos 10 near-misses (score ≥ 70), ordenados por hora. Colunas: símbolo / score / `ema_trend_1h` / `funding_rate` / motivo / hora. FR > 0.0015% em vermelho (catalisador T-06 visível em tempo real).
- Badge `1h:+N` na coluna Símbolo das posições paper abertas — verde se `ema_trend_1h ≥ 2`, cinza caso contrário. Dado vem de `entry.signal.ema_trend_1h`.

### 🔧 Sprint Forge — 11/06/2026 (T-09 + análise AIOUSDT)

**feat(ghost): `funding_rate` no ghost signal dict** · commit `4ffd73f`

Campo ausente do bloco `_write_ghost_signal` em `signal_engine.py:261`. Já existia no sinal real (L998) — bug de paridade silencioso. Corrigido: 1 linha adicionada. Habilita auditoria da tese T-06 (FR como catalisador de squeeze) nos `ghost_signals.jsonl` históricos. Sem impacto em gates ou comportamento do bot.

**Análise de caso — AIOUSDT +29% (imagens TradingView + CoinGlass · 10/06 23:56 UTC)**

AIOUSDT subiu +29% e o SS não entrou. Diagnóstico Forge: **miss por design correto**. O movimento foi uma **demand ramp orgânica** — CVD acumulando por horas, OI crescendo gradualmente, FR escalando até 0.0547% (extremo). Padrão diferente do squeeze de liquidação que o SS foi projetado para capturar. O DNA funcionou como esperado. Imagens salvas em `Estudo Imagens (TV e Coinglass)/`. Demand ramp documentado como backlog estratégico em `tasks.md` — Brain decide pós 50+ trades se vale um path separado.

### 🔧 Sprint Forge — 11/06/2026 (Governança + B-28 + B-47)

**F-01 Paper persistence** · commit `1772fd9` — Endpoint `/api/paper-config` lê `preferences.json["paper"]` e preenche `initialCapitalInput`, `riskPctInput`, `leverageInput`, `maxPosInput` no boot do cockpit.

**Squeezometer 85/70** · commit `576b5d7` — 85=crítico (5min cooldown), 70=aquecendo (15min cooldown). Sieve thresholds intocados. Alinhado com min_score=85.

**B-28 Janela de silêncio** · commits `a0f0b57`/`31c2fcf` — Gate `silence_window_2100` em `signal_engine.py:analyze()` bloqueia novas entradas 20:50–21:05 BRT. Relatório diário movido de 20:50 para 21:01 BRT (candle já fechado). Trades abertos na virada não afetados.

**B-47 OI como critério VIP** · commit `92483e3` — `oi_trend > 0.015` adicionado ao critério VIP de priorização em `data_engine.py`. Resolve o paradoxo estrutural onde ativos em acumulação silenciosa (caso AIOUSDT-type) ficavam no lote rotativo com latência. Threshold = `min_oi_trend` de preferences — consistência semântica.

**T-08 / B-43 diagnósticos** — T-08: sem bug; 0 eventos `ema_4h_bearish` porque mercado 79% bearish engole tudo antes do gate F-18 via `score_below_threshold`. Aguarda macro virar. B-43: já estava implementado em preferences.json — backlog desatualizado.

### 🔧 Sprint Forge — 11/06/2026 (Telegram + paper_tracker)

**feat(telegram):** alertas de ciclo de vida completo · commit `5534599`

Gaps identificados: bot subia/caía silenciosamente, relatórios diário/horário ruins, sem aviso de circuit breaker ou warmup. Implementado:

| Alerta | Quando dispara |
|--------|---------------|
| `bot_startup` | Após `state.restart_warmup()` — modo, capital, min_score, warmup iniciando |
| `warmup_complete` | Após 300s de warmup — gatilho liberado |
| `drawdown_circuit_breaker` | Quando DrawdownManager pausa trading (DD ≥ 15%) |
| `bot_shutdown` | No `finally` do main — motivo + resumo W/L/WR/uptime |
| `send_hourly_report` (reescrito) | Stats cumulativos da sessão + lista de trades da última hora (max 10) |
| `send_daily_report` (reescrito) | Profit Factor, MFE/MAE médio, melhor/pior trade, uptime |

**paper_tracker:** adicionados ao `_stats()`: `gross_profit`, `gross_loss`, `avg_mfe_pct`, `avg_mae_pct`, `max_drawdown_pct`. Adicionados ao `snapshot()`: `peak_capital`, `best_trade`, `worst_trade`.

**min_score paper 85→80** · commit `a628a3b` · autorizado Brain/Doreto 11/06/2026. Cenário A+B confirmado (stream F-12 ok, volume baixo 01h UTC + 73% bearish → teto ~83 sem liq_cascade). Condição de reversão: WR<45% ou MAE>8% em 20+ trades score 80–84. Paper reset executado por Doreto no restart.

### 🔧 Sprint Forge — 11/06/2026 (D1 · D2 · F-19 · R-07 governança)

**D1: `funding_rate` no signal dict real** · commit `3616b1b` (Brain — violação R-07 #5, aprovado Forge)

`funding_rate` presente em ghost signals mas ausente em `signals.jsonl` e `paper_closed.jsonl`. 1 linha adicionada em `signal_engine.py:954`. **Validado:** SQDUSDT primeiro signal pós-restart com `funding_rate=0.00005` — T-06 agora auditável nos trades reais.

**D2: PaperTracker setLevel DEBUG para breakeven diag** · commit `a1949d9` (Brain — violação R-07 #6, aprovado Forge)

`logger.debug()` em `paper_tracker.py` silenciado pelo nível INFO global. Fix: `logging.getLogger("PaperTracker").setLevel(logging.DEBUG)` em `main.py:74`. Próximo trade com MFE > 3.4% vai gerar ticks `PAPER-BREAKEVEN-DIAG`.

**F-19: Reconstrução `_post_trade_pending` no boot** · commit `e451f19` (Brain — violação R-07 #7, aprovado Forge)

`_post_trade_pending` era 100% in-memory — snapshots 4h/12h/24h perdidos a cada restart. Fix: `_rebuild_post_trade_pending()` chamado no boot, lê `paper_closed.jsonl`, reinsere trades das últimas 24h com snapshots incompletos. 38 linhas em `paper_tracker.py`. Alpha decay agora sobrevive a restarts.

**Governança R-07:** 7 violações registradas nesta sessão. Brain e ARIA continuam implementando e commitando diretamente. Doreto reconheceu ter autorizado erroneamente em algumas ocorrências. Todos os códigos revisados e aprovados pelo Forge. Padrão registrado em tasks.md e memória persistente.

**Backlogs formalizados:** `aria/backlog-aria-doreto-v1.0.md` criado com 9 entradas (padrões A-01 a A-04, teses TA-01/TA-02, descobertas AP-01 a AP-04). Equivalente ao backlog do Brain como fonte de demandas — ambos alimentam `tasks.md` via autorização de Doreto.

**Estado ao reiniciar (pré-restart):**
- `paper_closed.jsonl`: 13+ trades (inclui SQDUSDT trailing_stop +$1.12, MFE 10.12%)
- D1 validado · D2 + F-19 aguardam restart para entrar em efeito
- Meta: 50 trades para validação estatística T-01 a T-04

---

### 🔧 Sprint Forge — 12/06/2026 (Fix A + E1/E2 gate final + investigação final_gate_fail)

**Diagnóstico: `final_gate_fail` bloqueava 50+ sinais válidos**

Doreto reportou 50 casos de `final_gate_fail` nos ghost signals — todos CATIUSDT score=100, ema4h=+4, lsr=-1.14, CVD=19.76%. Forge investigou e identificou dois problemas distintos:

**Fix A — `min_oi_accel` 0.0 → -0.05** · commit `817785c` · `preferences.json` (paper + live)

`min_oi_accel=0.0` exigia OI acelerando. CATIUSDT com oi_accel=-0.0142 (ruído, essencialmente flat) bloqueava score=100. Threshold -0.05 libera desaceleração mínima, mantém proteção para desaceleração real.

**Fix E1/E2 gate final — bypass propagado para L947** · commit `d0ea407` · `signal_engine.py:949-950`

E1/E2 bypassavam `oi_trend_too_weak` e `lsr_trend_not_negative` nos gates individuais (L787/L797) mas não propagavam para o gate final (L947). LABUSDT: cascade=True, liq=$10k, score=93, 142t/m — morria em L949 por oi_trend=0.004 < 0.015 apesar de E1 ativo. Fix: `liq_cascade or (oi_trend >= final_min_oi_trend)` e `liq_cascade or (lsr_trend <= max_lsr_trend)`. E1/E2 agora completos end-to-end.

**Resultado pós-fix:** `final_gate_fail` caiu de 68 para 2 casos nos primeiros 15min pós-restart. Os 2 residuais são sem cascade — bloqueios legítimos. Registrado em tasks.md para investigação futura (baixa prioridade).

**Estado ao encerrar sessão (12/06/2026 · ~00:45 BRT):**
- Bot rodando em paper, gatilho liberado às 00:41:17 BRT
- Zero trades ainda — mercado bearish, score_below_threshold dominante
- Candidatos com cascade ativo: STGUSDT, ESPORTSUSDT, PLAYUSDT — aguardando score >= 78
- Todos os fixes ativos: E1/E2/E3 (`aa5d2ee`), Fix A (`817785c`), E1/E2 gate final (`d0ea407`)
- F-18 bypass cascade: decisão pendente — aguarda dados reais com os fixes ativos

**Diagnóstico sessão Forge 12/06 (investigação zero trades):**
- 1 trade real capturado: CUSDT 22:20:43 BRT, score=100, lsr_trend=-0.4345 — pipeline funcionou. Estado perdido por restart (sem persistência).
- Score ceiling empírico = 77 (1.388 refusals score_below_threshold em 14.056 entradas, avg=67.6). Threshold=78 está 1pt acima do máximo empírico.
- Macro bearish (79% EMA:4h negativo) impede liq_cascade (+20pts) e liq_short_1m (+15pts) de acumular — causa raiz é regime de mercado, não bug de código.
- LABUSDT 18 final_gate_fail em 00:24-00:25 BRT: eram pre-fix (d0ea407 commitado às 00:34:59 BRT). Fix correto e ativo desde restart 00:36:17.
- XPLUSDT score=96 bloqueado por lsr_trend_not_negative com liq=0: funciona por design.
- Pendente Brain: decidir se baixa min_score 78→76 (258 candidatos em faixa 75-77) ou aguarda regime.
- Pendente Doreto: autorizar F-19 (_post_trade_pending reconstruction) para trade persistence entre restarts.

---

## 🔧 Sprint Forge + Brain — 12/06/2026 (análise score 75-77 · decisão min_score)

### Análise Forge — distribuição candidatos score 75-77

Brain solicitou investigação dos candidatos score 75-77 (reason=score_below_threshold) para decidir se baixa min_score 78→76.

**n=1.040 refusals score 75-77 hoje (não 258 como estimado inicialmente):**

| Score | n |
|-------|---|
| 75 | 1.010 |
| 76 | 150 |
| 77 | 10 |

**Distribuição liq_short_1m:**
- liq=0: **928 (89%)** — chegaram ao score via liq_cascade=True bypassing D3
- liq $500–$2k: 32 (3.1%)
- liq $2k–$10k: 20 (1.9%)
- liq > $10k: 16 (1.5%)

**Premissa Brain corrigida:** os 928 com liq=0 não "passaram D3 com liq>$500". D3 funciona corretamente (623 bloqueios `liq_required_no_cascade` confirmados hoje). Chegaram ao score porque `liq_cascade=True` bypassa D3 — cascade ativo mas liq_short_1m=0 no tick (evento já dissipado, +20pts de cascade fantasma no score).

**Dos 60 candidatos com liq>$500:**
- LSR trend < -0.3 (squeeze clássico): **0 de 60 (0%)**
- LSR trend positivo (demand breakout): 36 (60%)
- OI trend >= 0.015 (forte): 19 (32%)
- Símbolos: XMRUSDT $40k, HUSDT $13k, XPLUSDT $17k — todos com lsr_trend neutro/positivo

**Hipóteses Brain:**
- H1 (liq baixa por margem mínima): **confirmada** — mecanismo diferente do esperado, mas perfil de risco idêntico
- H3 (bug de dado frio): descartada

### Decisão Brain — manter min_score = 78

Baixar para 76 capturaria: (89%) cascades dissipados com liq=0 no tick — mesmo padrão do `volume_quality_spike` já bloqueado; (11%) demand breakouts com LSR positivo sem confirmação de squeeze. Nenhum candidato com perfil de squeeze clássico (LSR < -0.3) na faixa 75-77. Decisão correta e suportada pelos dados.

### Outros achados da sessão
- 6 restarts entre 19h e 00:36h: **confirmados como manuais** por Doreto (ciclo de deploy). Sem causa raiz a investigar.
- CUSDT: trade perdido por restart — estado in-memory não persistido. F-19 (reconstrução `_post_trade_pending`) aguarda autorização Doreto para cobrir esse cenário futuro.

*Versão: 4.25 · Última atualização: 12/06/2026*

---

## 🔧 Sprint Forge — 12/06/2026 (governança R-07 + comando Fechar Sessão · `026418f` · `23aa2aa`)

**Violação R-07 #8 — Brain commitou `acf986c`** ("commit de governança", só `.md`). Reforço aplicado:
- `AGENTS.md` — histórico atualizado, deixa claro que nenhuma categoria de commit justifica Brain/ARIA executar `git commit`
- `brain/BRAIN_CONTEXT.md` — aviso no topo, visível no próximo boot
- `aria/ARIA_CONTEXT.md` — aviso com histórico completo das 5+ violações

**Comando "Fechar Sessão" adicionado ao CLAUDE.md** — protocolo por agente:
- **Forge:** executa commits, push origin + aria, atualiza context.md + tasks.md, confirma ao Doreto
- **Brain:** atualiza MDs localmente + escreve bloco padronizado em `tasks.md` pedindo ao Forge commitar. Nunca executa `git commit`
- **ARIA:** atualiza MDs localmente + escreve achados em `tasks.md` para Brain revisar. Nunca executa `git commit`

---

## 🔧 Sprint Forge — 12/06/2026 (fix Reset Paper + metric_state · `d419aba`)

**Problema:** botão Reset Paper deletava `metric_state.json` (warm cache de klines 12MB) desde sempre. Cada clique em Reset Paper custava 2.5h de cegueira no boot seguinte — klines de 527 símbolos reconstruídos do zero.

**Fix:** `main.py` — Reset Paper agora limpa apenas trades/estado paper. `metric_state.json` intocado. Confirmado em produção: log de `23:43:28` sem linha `metric_state.json resetado` após Reset Paper.

**Impacto:** Reset Paper agora é operação segura. Boot pós-reset mantém cache quente + apenas 300s de warmup de slopes.

---

## 🔧 Sprint Brain × Forge — 12/06/2026 (E1 · E2 · E3 · bypass liq_cascade)

### Gates desbloqueados para liq_cascade=True

Brain analisou logs pós-boot e identificou 46 ghost signals de ativos com `liq_cascade=True` bloqueados por gates projetados para ativos sem pressão institucional.

| Task | Commit | Mudança |
|------|--------|---------|
| **E1** | `aa5d2ee` | `signal_engine.py:787` — bypass `oi_trend_too_weak` quando `liq_cascade=True`. HUSDT bloqueado 37× por `oi_trend=0.00799` vs threshold `0.008` (diferença 0.00001). Durante cascade, OI fraco é sinal correto — longs liquidados reduzem OI por definição. |
| **E2** | `aa5d2ee` | `signal_engine.py:797` — bypass `lsr_trend_not_negative` quando `liq_cascade=True`. HUSDT bloqueado 10× com liq=$17k–$18k. `liq_cascade` é evidência mais forte que `lsr_bypass_active` — recebia tratamento inferior ao B-34. |
| **E3** | `b6730c7` | `preferences.json` — `min_score` paper 80 → 78. Score máximo observado em 3.757 refusals = 78. Teto empírico 2pts abaixo do threshold — bot nunca entrava. Reversão se WR < 45% ou MAE > 8% em 20+ trades score 78–79. |

Soft restart executado por Doreto após commits. Warmup 300s concluído — gatilho ativo com E1/E2/E3 em efeito.

---

## 🔧 Sprint Forge — 11/06/2026 (sessão tarde · reset limpo + B-49)

### Estado ao iniciar sessão

Hard reset manual executado por Doreto antes do boot: todos os arquivos de `logs/` deletados manualmente exceto `metric_state.json` (12MB). Boot quente confirmado — `🔥 Cache carregado (idade: 46s)`, klines intactos, zero cegueira.

**Confirmações no boot:**
- F-12 pipeline funcional imediatamente: HUSDT $22.5k, VELVETUSDT $4.5k em liquidações
- Warmup 300s concluído às 20:31 BRT — gatilho liberado
- Todos os gates D3/D4/D6/D7 ativos (commit `6d9554d`)
- DNA BLOCKER top: `score_below_threshold` dominante, `liq_required_no_cascade` (D3) operando

### Esclarecimento comportamento reset diário 21h BRT

Confirmado como **comportamento esperado** (não bug): `reset_daily_history()` em `metric_engine.py:39` zera os derivados de slope (`price_change_24h`, `exp:5m`, `oi_trend:5m`, `lsr_trend:5m`, etc.) mas preserva o campo `price` atual. O percentual de variação fica zero por ~5min até o ring buffer reconstruir. Gate `silence_window_2100` + `restart_warmup(300s)` cobrem a janela — zero trades afetados.

**Divergência com eAssets:** eAssets faz transição suave sem zeros visíveis na virada. Investigação futura registrada como **B-49** em `brain/backlog-brain-doreto-v1.0.md` · commit `c7aaea9`.

### B-49 — Janela cega 21:05–21:30 BRT (Brain backlog)

Tese: `silence_window` cobre 20:50–21:05 BRT (15 min) mas slopes levam ~30 min para reconstruir após o reset. Bot opera com dados incompletos na janela 21:05–21:30 BRT. Coincide com ciclo de funding rate Binance (00:00 UTC) — janela de maior pressão de fechamento de shorts. Critério para task: 3+ casos confirmados nos logs. Opção preferida: usar `price_at_reset` (já salvo) como baseline do novo dia — transição suave sem zeros, alinhado com eAssets.

### Procedimento de reset documentado

Esclarecido com Doreto os 3 níveis:
- **Soft Restart:** `Ctrl+C → python main.py` — zero deletions, boot quente
- **Reset Paper:** botão dashboard — limpa trades/estado, preserva `metric_state.json` e logs históricos
- **Hard Reset:** botão dashboard — zera estado institucional em memória + reinicia warmup, **não deleta `metric_state.json`** (confirmado no código `main.py:2217`)

Deleção manual de `logs/` exceto `metric_state.json` = Hard Reset + deep_clean manual. Equivalente ao botão Hard Reset com deep_clean=True.

---

## 🔧 Sprint Forge — 11/06/2026 (infraestrutura Python 3.14 + freeze metric_state)

### Diagnóstico de freeze — metric_state.json 12MB bloqueando event loop

**Causa raiz:** `store.save_state()` em `data_engine.py:861` era chamado a cada 60s **diretamente no event loop** — serializar e gravar 12MB de JSON bloqueava o loop inteiro por vários segundos. Com 527 símbolos monitorados o arquivo cresceu indefinidamente até o bot parar de responder.

**Fix:** `store.save_state()` → `threading.Thread(target=store.save_state, daemon=True).start()` · commit `8fc133d`

### fix(shutdown): RecursionError Python 3.14 no _stop_watcher · commit `c104337`

**Causa raiz:** Python 3.14 mudou `Task.cancel()` para propagar recursivamente para tasks filhas (novo mecanismo de eager task groups). O `_stop_watcher` cancelava todas as tasks e depois fazia `asyncio.gather(*all_tasks)` nelas — o gather chamava cancel de novo → recursão de 990 níveis → `RecursionError`.

**Fix:** removido o `asyncio.gather` de dentro do `_stop_watcher`. O gather principal em `main.py:2490` já aguarda todas as tasks — o gather duplicado era desnecessário.

**Nota:** o bot continuava rodando após o RecursionError (main gather absorvia com `return_exceptions=True`) — mas o shutdown nunca completava corretamente.

### fix(vscode): interpreter path com # na pasta · `.vscode/settings.json`

Caminho absoluto `C:/Apps/#5 SqueezeSniper-V4/.venv/...` rejeitado pelo VS Code (interpreta `#` como fragmento de URL). Alterado para caminho relativo `.venv/Scripts/python.exe`.

### Estado ao encerrar sessão

- Bot rodando em paper mode com logs limpos (metric_state.json preservado, restante zerado)
- Todos os fixes de 11/06 ativos (D3/D4/D6/D7/F-19/B-34-fix/shutdown gracioso)
- Meta: 50+ trades para validação estatística T-01 a T-04

---

## 🔧 Sprint Forge — 11/06/2026 (infraestrutura + fix shutdown gracioso)

### fix(shutdown): EXIT via dashboard não encerrava graciosamente · commit `f2f6caf`

**Problema:** ao clicar EXIT no dashboard, o bot reiniciava em vez de encerrar. O `finally` (Telegram bot_shutdown, backup, kill_process_tree) não executava corretamente.

**Causa raiz — 3 bugs combinados em `main.py`:**
1. `asyncio.gather(..., return_exceptions=False)` — propagava `CancelledError` abortando o fluxo antes do `finally`
2. Ordem errada dos `except`: `except Exception` vinha antes de `except asyncio.CancelledError` — o segundo nunca era alcançado
3. `_stop_watcher` cancelava as tasks mas não aguardava o cancelamento propagar antes de retornar

**Fix:**
- `return_exceptions=True` no gather principal
- `except asyncio.CancelledError` movido para antes de `except Exception`
- `_stop_watcher` faz `await asyncio.gather(*all_tasks, return_exceptions=True)` após cancelar — aguarda todas as tasks antes de sair

**Impacto:** shutdown gracioso agora executa corretamente via dashboard (Telegram notificação, backup automático, kill_process_tree). Requer soft restart para entrar em efeito.

### fix(vscode): configurações de ambiente corrigidas

- `python.defaultInterpreterPath`: `${workspaceFolder}` substituído por caminho absoluto — `#` no nome da pasta quebrava a resolução da variável
- `tasks.json`: `runOn: folderOpen` removido do watcher de testes — `ptw` não instalado causava erro ao abrir o projeto

---

## 🔧 Sprint Brain × ARIA × Forge — 11/06/2026 (análise 12 trades + D1/D2)

### Auditoria dos 12 trades pós-restart (Brain + ARIA)

| KPI | Valor | Meta GO/LIVE |
|-----|-------|---|
| WR | 4/12 = 33.3% | ≥ 60% |
| PnL total | -$10.75 USDT | positivo |
| PnL sem SPACEUSDT | -$2.70 USDT | — |
| MFE médio | +2.41% | — |
| MAE médio | -8.00% | — |

**Exit reasons:**
- `trailing_stop`: 4/6 (67% WR) — funciona quando o squeeze acontece
- `squeeze_failed`: 0/4 (0% WR) — principal dreno, entradas sem confirmação de momentum
- `stop_loss`: 0/1 — SPACEUSDT -38.9% por slippage simulado em micro-cap (preço caiu 3.94% vs SL 2.5% — gap de tick em paper trading, não bug de código)
- `max_hold`: 0/1 — AIGENSYNUSDT, mae_guard_late bloqueado por MFE=4.21% > threshold

**Fee pressure identificada (ARIA):** 2/6 trailing_stops fecharam abaixo do breakeven após fees ($0.16/trade = 0.8% de margem). HOLOUSDT e BASEDUSDT saíram com PnL negativo. Trailing disparando perto do entry + fees = loss sistemático. A monitorar com mais amostras.

**ARIA corrigiu erro próprio:** reportou WR 50% e PnL -$7.40 inicialmente por usar `live.pnl_usdt` em vez de `exit.pnl_usdt`. Brain corrigiu com evidência via `quality.win`. ARIA aceitou.

### B-34 bypass — análise de por que não dispara (Forge)

SXTUSDT (score 100), OPGUSDT (score 95), AIOUSDT (score 100) bloqueados por `lsr_trend_positive`. Diagnóstico via `signal_refusals.jsonl`:

- `trades_1m` e `cvd_pct`: todas as condições passam facilmente
- `liq_short_1m`: **único gargalo** — SXTUSDT $119, OPGUSDT $0, AIOUSDT $13.175 máx — todos abaixo do threshold de $20k

Conclusão: esses ativos estão em demand ramp orgânica (CVD forte sem liquidação sustentada), não squeeze de liquidação. Threshold $20k está correto para o padrão que o DNA cobre. `liq_short_1m_stable` reflete acúmulo por janela completa de 1m — picos pontuais não contam.

### Fixes implementados nesta sessão

| Fix | Commit | Descrição |
|-----|--------|-----------|
| **D1 — funding_rate no signal dict real** | `3616b1b` | 1 linha em `signal_engine.py:954` — habilita T-06 auditável em trades reais. Validado: SQDUSDT primeiro signal pós-restart com `funding_rate=0.00005` ✅ |
| **D2 — log diagnóstico breakeven partial TP** | `3616b1b` | log DEBUG em `paper_tracker.py:1063` — 3 trades com MFE > 3.4% (CATIUSDT x2, PORTALUSDT) tiveram `breakeven_partial_closed=False` sem motivo visível. Causa raiz aguarda logs do próximo lote |
| **F-19 — reconstrução `_post_trade_pending` no boot** | `e451f19` | `_rebuild_post_trade_pending()` em `paper_tracker.py`. Validado: 15 trades reinseridos no boot atual ✅ |
| **fix(B-34-bypass) — 5 gates LSR sem bypass** | `a2d1410` | Bug: `lsr_bypass_active=True` só ignorava o gate `lsr_trend_positive` (L531). Outros 4 gates downstream nunca checavam o bypass. Evidência: WLDUSDT liq=$23.5k trades=345 cvd=15.88 — bypass logado 20+ vezes mas nunca entrou. |
| **D3 `liq_required_no_cascade`** | `6d9554d` | liq_cascade=False AND liq≤$500 → recusa. 6/7 squeeze_failed tinham liq=0, WR=0%. CVD sem liq = demand ramp. `signal_engine.py:688` |
| **D4 bônus ema_trend_1h removido** | `6d9554d` | ema1h≥2 dava +5pts. ema1h=+6 WR=0% n=8. Campo preservado no signal dict. `market_view.py:102` |
| **D6 `overextension_double`** | `6d9554d` | ema4h≥6 AND ema1h≥6 → recusa. n=3 WR=0%, todos squeeze_failed. `signal_engine.py:699` |
| **D7 `lsr_multiframe_divergence`** | `6d9554d` | lsr:5m>0 AND lsr:1h>-0.5 → recusa. Shorts em 2 TFs = sem squeeze. `signal_engine.py:707` |

### Violação R-07 #5

Brain implementou e commitou D1+D2 diretamente (commit `3616b1b`). Forge revisou e aprovou — código correto. Violação registrada em `tasks.md` e em memória persistente. Regra: Brain para no diff em `tasks.md`, commit é sempre do Forge.

### Regra de restart adicionada a tasks.md (Doreto · commit `594b76f`)

Soft Restart é o padrão. Hard Reset Paper só com justificativa ou autorização explícita de Doreto. Regra no topo de `tasks.md` — primeiro item visível para todos os agentes.

---

## 🔧 Sprint EA-Sprint4 — Fixes F-12 a F-15 (08/06/2026)

### F-12 — liq_short_1m zerado (diagnóstico + fix notional)

**Commits:** `54225d1`

**Problema raiz identificado:** `notional = float(o["p"]) * float(o["q"])` — `p` pode ser `0` em ordens de mercado, gerando `notional=0` silencioso. Corrigido para usar `ap` (average price) × `z` (cumulative fill qty) com fallback para `p*q`.

**Logging adicionado:**
- `data_engine.py`: INFO para cada evento do stream `!forceOrder@arr` (antes era DEBUG — invisível)
- `metric_engine.py`: INFO quando `update_liquidation` acumula valor não-zero
- `metric_engine.py`: INFO quando `reset_1m_volume` copia `liq_short_1m_stable > 0`

**Como verificar:** Procurar nos logs por `F-12 liq_accum:` e `F-12 liq_stable:`. Se nenhuma linha aparecer, o stream `!forceOrder@arr` não está recebendo eventos.

### F-13 — Gate RSI 1h no warmup

**Commits:** `d4446dd`

**Problema:** `rsi:1h` fica em `50.0` artificial nos primeiros ~10min após restart (buffer de klines não completou). O score e sinal usavam esse valor falso sem saber.

**Fix:** Gate `rsi_1h_warmup` em `signal_engine.py` — se `rsi_1h is None or rsi_1h == 50.0` E `uptime < 600s`, registra refusal e retorna None. `_start_time` adicionado ao `__init__` da `SqueezeIgnition`.

**Parâmetro de observação:** `signal_refusals.jsonl` vai mostrar `rsi_1h_warmup` nos primeiros 10min de cada sessão.

### F-14 — max_hold disparando antes do mae_guard

**Commits:** `eb85dce`

**Problema duplo:**
1. `duration_s` não existia no JSONL — scripts de análise do Brain liam 0 (o campo correto era `live.duration_sec`)
2. Janela de perda entre mae_guard (120s, pnl < -2%) e trailing (ativa em 180s): trades a -1.8% aos 120s escapavam ambos e chegavam ao max_hold em -8%+

**Fixes:**
- Alias `duration_s` adicionado em `live.update()` em `paper_tracker.py` e `live_tracker.py`
- Late mae_guard a 240s: `pnl < -3.0% E mfe < 2.0%` → exit `mae_guard_late` (imediato, paridade paper + live)

### F-15 — Gate volume_quality_spike >= 2.0

**Commits:** `7bc9aab`

**Evidência:** 33 trades — winners vq médio=0.535, losers vq=1.502. Threshold 2.0 teria bloqueado NILUSDT(4.67), STGUSDT(16.20), MEGAUSDT(6.61) — todos losers — sem bloquear nenhum winner.

**Fix:** Gate após o gate combo EA-Sprint3 em `signal_engine.py`. Reason_code: `volume_quality_spike`. Fórmula: `cvd_change_pct / (trades_1m + 1)`.

### Parâmetros e gates ativos (estado 08/06/2026)

| Gate | Condição | Reason code |
|------|----------|-------------|
| trades_1m_too_low | trades_1m < 10 | `trades_1m_too_low` |
| oi_trend_too_weak | oi_trend < 0.008 | `oi_trend_too_weak` |
| lsr_trend_not_negative | lsr_trend > -0.3 | `lsr_trend_not_negative` |
| **volume_quality_spike (novo)** | vq >= 2.0 | `volume_quality_spike` |
| rsi_1h_warmup (novo) | rsi_1h == 50.0 E uptime < 600s | `rsi_1h_warmup` |
| mae_guard_late (novo) | dur >= 240s E pnl < -3% E mfe < 2% | `mae_guard_late` |

---

## 🔧 Sprint EA-Sprint4 — Diagnósticos + Pacote F-16 a F-18 (08/06/2026 — sessão 2)

### Diag F-12 — payload bruto !forceOrder@arr

**Commit:** `4129502`

Log dos primeiros 3 eventos por sessão antes de qualquer processamento. Procurar por `DIAG F-12 payload bruto (#1)` nos logs. Se não aparecer → stream não está conectando. Se aparecer mas `F-12 liq_accum:` nunca aparecer → o formato do evento não tem campo `S=BUY` como esperado.

### F-17 — late mae_guard threshold mfe 2% → 3%

**Commit:** `fd0a4a5`

Diagnóstico confirmado: BBUSDT MFE=2.98% escapou do gate (threshold era `< 2.0%`) e encerrou com -15.92% via max_hold — maior perda da amostra. Ajustado para `< 3.0%` em paper_tracker.py e live_tracker.py.

### F-16 — liq_threshold proporcional ao OI

**Commit:** `9477fd8`

Substituído threshold fixo `> 500` por `max(oi_usd * 0.02, 10_000)`:
- `oi_usd = oi_contratos * price` (calculado em tempo real no `record_snapshot`)
- $500K OI → threshold $10k (mínimo)
- $5M OI → threshold $100k
- $100M OI → threshold $2M

Ainda exige `liq_curr > liq_prev * 1.8` (aceleração de 80%).

**Nota:** F-16 só fará diferença quando F-12 estiver confirmado — se `liq_short_1m = 0` por problema de stream, o threshold proporcional não muda nada.

### F-18 — ema_trend:4h no MetricStore + gate ema_4h_bearish

**Commit:** `adaed4f`

**metric_engine.py:**
- `ema_trend:4h` inicializado em data dict para novos e existentes símbolos
- `_klines` e `_kline_volumes` incluem `"4h"` em todos os pontos de init/load/save
- `timeframes = ["5m", "15m", "1h", "4h"]`

**data_engine.py:**
- Boot: fetch `k_4h = futures_klines(interval='4h', limit=110)` por símbolo
- WS: `kline_4h` adicionado ao stream
- `kline_chunk_size` reduzido de 60→48 (48×4=192 streams/batch, limite Binance=200)

**signal_engine.py:**
- Gate `ema_4h_bearish`: `ema_trend:4h <= -4 AND exp_btc_norm_1h < -1.5`
- Evidência: 3 sessões consecutivas, EMA:4h=-6 presente na maioria dos losers

### Gates ativos (estado 08/06/2026 — v3.9)

| Gate | Condição | Reason code |
|------|----------|-------------|
| trades_1m_too_low | trades_1m < 10 | `trades_1m_too_low` |
| oi_trend_too_weak | oi_trend < 0.008 | `oi_trend_too_weak` |
| lsr_trend_not_negative | lsr_trend > -0.3 | `lsr_trend_not_negative` |
| volume_quality_spike | vq >= 2.0 | `volume_quality_spike` |
| rsi_1h_warmup | rsi_1h == 50.0 E uptime < 600s | `rsi_1h_warmup` |
| **ema_4h_bearish** | ema_4h <= -4 (AND removido — `9bce976`) | `ema_4h_bearish` |
| mae_guard_late | dur >= 240s E pnl < -3% E mfe < 3% | `mae_guard_late` |

### O que monitorar na próxima sessão
1. `DIAG F-12 payload bruto (#1)` — confirmar se stream chega e formato do evento
2. `F-12 liq_accum:` — confirmar se notional não-zero está acumulando
3. `ema_4h_bearish` em signal_refusals.jsonl — gate funcionando
4. `mae_guard_late` nos trades fechados — threshold 3% funcionando

---

## 🔧 Fixes cirúrgicos pós-EA-Sprint4 (08/06/2026 — sessão 3)

### Fix F-18 corrigido — gate ema_4h_bearish simplificado

**Commit:** `9bce976`

Segunda condição `AND exp_btc_norm_1h < -1.5` removida. Anulava o gate na prática: todos os grandes losers tinham `EMA:4h=-6` mas `norm_1h positivo`. WAXPUSDT entrou com `EMA:4h=-6, norm_1h=+1.378` → -16.93%. 3 sessões de evidência.

**Gate final:** `ema_trend:4h <= -4` → `ema_4h_bearish` → return None.

### min_rsi_5m 60 → 45 (paper)

**Commit:** `e52f2e9`

BANANAS31 (+17%, melhor winner da amostra) estava bloqueado com RSI=48. A zona de ignição do squeeze é RSI 40–55 (acumulação), não acima de 60 (euforia). Relaxamento seguro pois o gate `ema_4h <= -4` agora protege contra entradas em tendência de queda — o risco que o RSI alto pretendia cobrir já está coberto de forma mais precisa.

**Parâmetros críticos atualizados (v4.0):**

| Parâmetro | Antes | Depois | Motivo |
|-----------|-------|--------|--------|
| `paper.signal.min_rsi_5m` | 60.0 | **45.0** | Zona de acumulação 40–55 |
| Gate `ema_4h_bearish` | `<= -4 AND norm_1h < -1.5` | **`<= -4` (só)** | AND anulava o gate |

### ✅ F-12 CONFIRMADO (09/06/2026 — boot 21:27:47)

`DIAG F-12 payload bruto (#1)` apareceu 42 segundos após o boot. Pipeline funcional:
- `F-12 liq_accum:` registrando notionals reais — TRUMPUSDT $438, STGUSDT $1276, BTWUSDT $6090, VELVETUSDT $4439
- `F-12 liq_stable:` gerando valores estáveis para o signal dict
- Todos os 42+ trades anteriores a essa sessão tinham `liq_short_1m_stable = 0` — dados históricos invalidados para teses T-01/T-02/T-03

---

## 🧹 Sessão 09/06/2026 — Validação e Higiene do Projeto

### Validações confirmadas nesta sessão

| Fix | Status | Evidência |
|-----|--------|-----------|
| **F-12** WebSocket endpoint Futures | ✅ CONFIRMADO | DIAG 21:27:47, notionals reais |
| **ema_trend_4h** no signal dict | ✅ CONFIRMADO | fix candles 100→50, commit `c7edbf8` |
| **rsi:1h** real pós-cache | ✅ CONFIRMADO | gate rsi_1h_warmup fora do top-5 no 2º boot |
| **fit_score_min=90** mantido | ✅ CONFIRMADO | bug _apply_runtime_mode corrigido `562e172` |
| **boot quente** (cache 30s) | ✅ CONFIRMADO | klines com age=30s na 2ª inicialização |

### Organização do projeto executada

- `assets/` criado — logo.png e imagens movidos da raiz
- `aria/scripts/` criado — scripts de análise ARIA movidos de `aria/`
- `docs/_arquivo/` criado — scripts legados arquivados (`claude_hub.py`, `preferences.suggested.json`)
- `logo.png` path corrigido em `src/web_dashboard.py:2826` → `assets/logo.png`
- `docs/HOUSEKEEPING.md` criado — regras de higiene permanentes do projeto

### Blacklist zerada

`preferences.json → blacklist: []`

EPICUSDT, HOLOUSDT, JTOUSDT, NILUSDT, PARTIUSDT, PROVEUSDT removidos.
Filosofia: ativos mudam de comportamento por minuto. Gates dinâmicos (`ema_4h_bearish`, `spread_too_high`, `cvd_not_confirming`) cobrem os casos de forma precisa e adaptativa, sem penalizar símbolos que voltaram a se comportar bem.

### Estado atual (09/06/2026 — fim de sessão)

- Bot rodando em paper mode, todos os gates ativos, pipeline liq funcional
- 50+ trades necessários para auditoria estatística (T-01/T-02/T-03)
- F-01 (cockpit Live persistence) ainda pendente — único bug UX aberto
- Próxima pauta Brain: gate momentum sub-minuto (ring buffers 10s/20s/30s) e macro CMC

### Tuning min_score — 10/06/2026 (madrugada)

Bot rodou 6h+ sem nenhum trade. Diagnóstico via `signal_refusals.jsonl` (25.307 eventos):
- Score máximo atingido: **88** (KATUSDT 17x, STGUSDT 11x). Threshold `min_score: 90` → nunca entrava.
- Maiores bloqueadores: `lsr_trend_positive` (27%), `cvd_negative_quarantine` (26%) — ambos corretos para o mercado atual.
- `min_score` reduzido 90 → **85** em `preferences.json` · commit `470a658`. Hot reload via `_apply_runtime_mode`.
- Análise eAssets (snapshot 01:48 UTC): JCTUSDT (EXP1h=74, LSR=-12, OI=15), ZBTUSDT, AGTUSDT com melhores setups.
- BTWUSDT +20%: LSR=+18 positivo quando snapshot foi tirado → squeeze já aconteceu, bot bloqueou corretamente.

### eAssets Dashboard — refatoração concluída (09/06/2026)

Backend unificado em `aria/eAssets/server.py` (FastAPI, porta 5001) substituiu 2 processos separados.
CRM, GRM e BTC Reset agora calculados de verdade pelos módulos Python (`scripts/crm.py`, `grm.py`, `btc_reset.py`).
Yahoo Finance: `allorigins.win` removido — servidor busca direto (sem CORS).
**Pendente (baixa prioridade):** seção macro do dashboard HTML não popula no browser — debug via DevTools pendente.
ARIA ciente do estado técnico (ARIA_CONTEXT.md v1.2 seção 6).
