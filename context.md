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
- Versão atual: v3.7 · 05/06/2026

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

*Versão: 4.6 · Última atualização: 10/06/2026*

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
