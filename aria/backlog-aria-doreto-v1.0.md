# Backlog Analítico — ARIA × Doreto
_Documento vivo · atualizado conforme análises chegam_
_Criado: 11/06/2026 · Versão: 1.0_

> Este documento é nosso — ARIA e Doreto. Não é fila do Forge nem do Brain.
> É onde ARIA guarda padrões observados nos snapshots eAssets, cruzamentos com logs do SS, e hipóteses analíticas antes de decidir se viram evidência suficiente para o Brain.
> Revisamos periodicamente: incluímos, alteramos, descartamos.

---

## PADRÕES DE MERCADO — Descobertas eAssets

### A-01 — ESPORTSUSDT: FR extremo + range_level como combo T-05 × T-06
**Status:** Descoberta nova · aguarda cruzamento com logs SS · 11/06/2026
**Snapshot:** eassets-panel-20260611-061006.json

ESPORTSUSDT apresentou simultaneamente:
- **FR=+0.00439565 (0.44%)** — maior funding rate do universo candidato no snapshot
- **range_level:1h=4** — energia represada antes de breakout (tese T-05)
- **EMA:4h=+4 / 1h=+6 / 15m=+6 / 5m=+6** — alinhamento total
- **RSI:1h=59.8** — zona de ignição perfeita (40–65, não overextended)
- **+9.24% 1D** — menor movimento do Tier 2 = mais espaço para subir

É o único ativo com FR extremo + range_level alto + EMAs alinhados + RSI na zona correta simultaneamente neste snapshot. Combinação T-05 × T-06 nunca observada tão limpa em análises anteriores.

**Hipótese:** quando FR > +0.003 E range_level:1h ≥ 4 E EMA:4h ≥ 0, a probabilidade de squeeze violento é maior porque os shorts estão pagando para manter posição contra energia represada. O duplo catalisador (custo de carry + breakout de range) cria pressão de fechamento composta.

**Próximos passos:**
- Monitorar ESPORTSUSDT nos logs SS: se o bot entrar, cruzar MFE com o combo T-05×T-06
- Se SS não entrar: verificar qual gate bloqueou e se o eAssets confirma a tese mesmo sem entrada
- Quando tivermos 10+ ativos com FR > +0.003 nos logs, calcular MFE médio vs ativos com FR neutro

**Encaminhar ao Brain quando:** tivermos 5+ amostras do combo FR alto + range_level ≥ 3 nos logs do SS.

---

### A-02 — BRUSDT: padrão LSR colapso multi-TF — setup SS mais clássico
**Status:** Observação documentada · 11/06/2026
**Snapshot:** eassets-panel-20260611-061006.json

BRUSDT mostrou o setup mais limpo do universo neste snapshot:
- **LSR:1h=-21.41, LSR:5m=-39.39** — colapso de shorts em TODOS os timeframes simultâneos
- **OI:1h=+63.86, OI:5m=+47.80** — acumulação acelerando (OI:5m > OI:1h = nova aceleração)
- **EMA:4h=+4 / 1h=+6 / 15m=+6 / 5m=+6** — alinhamento
- **RSI:1h=72.3 / RSI:5m=73.6** — momentum quente sem euforia

O padrão "OI:5m crescendo mais rápido que OI:1h" merece atenção — pode indicar aceleração de entrada institucional nas últimas velas vs acumulação mais lenta. Quando OI curto prazo > OI médio prazo = demand ramp em formação.

**Hipótese para futura tese:** OI:5m > OI:1h (aceleração) + LSR colapsando em todos TFs = sinal de entrada institucional mais urgente que OI crescendo apenas no 1h.

**Próximos passos:** monitorar nos próximos snapshots se BRUSDT entra em log SS e com qual MFE. Se sim, validar se o padrão OI:5m > OI:1h precede squeezes mais fortes.

---

### A-03 — AIOUSDT: demand ramp orgânica vs squeeze de liquidação — distinção crítica
**Status:** Padrão confirmado · documentado para referência ARIA · 11/06/2026
**Referência:** BRAIN_CONTEXT.md — "Caso AIOUSDT +29% — miss por design"

Nos últimos dois snapshots (23:12 de 10/06 e 06:10 de 11/06), AIOUSDT mostrou:
- OI:1h crescendo continuamente (+50 → +185.95)
- LSR:1h colapsando progressivamente (-9.35 → -34.86)
- CVD e preço subindo de forma gradual e sustentada (+29% → +40%)

Isso é **demand ramp orgânica** — acumulação institucional construída ao longo de horas, não explosão de squeeze de liquidação em minutos. O SS foi projetado para o segundo padrão.

**Distinção operacional para ARIA:**
- **Squeeze de liquidação:** OI spike súbito + LSR colapso abrupto + preço +5-20% em < 60 min. SS captura.
- **Demand ramp:** OI crescendo gradualmente por horas + LSR caindo progressivamente + preço compondo lentamente. SS normalmente não captura (entra tarde, squeeze_failed).

**Valor para análise de snapshots:** quando ativo aparece no Tier 1 por 2+ snapshots consecutivos com OI crescendo mas sem explosão de LSR — provável demand ramp. Anotar como "backlog pós-50 trades" ao invés de candidato SS imediato.

---

### A-04 — Regime macro: expansão de ilhas EMA:4h positivas
**Status:** Monitoramento contínuo · linha de base estabelecida · 11/06/2026

Linha de base de expansão do universo operável SS:

| Data | Snapshot | Ilhas EMA:4h ≥ 0 | BTC EMA:4h | BTC EMA:1h |
|------|----------|-----------------|-----------|-----------|
| 10/06 23:12 | eassets-panel-20260610-215848 | ~28/531 (5.3%) | -6 | -6 |
| 11/06 06:10 | eassets-panel-20260611-061006 | 140/526 (26.6%) | -6 | **+4** |

**Observação:** a expansão de 5.3% → 26.6% aconteceu com BTC EMA:4h ainda -6. O que mudou foi o EMA:1h do BTC (-6 → +4) e RSI:1h (40.3 → 63.3). O macro de curto prazo do BTC foi suficiente para desbloquear 112 ilhas adicionais.

**Hipótese:** BTC EMA:1h virar positivo + RSI:1h > 55 = expansão relevante do universo SS mesmo sem BTC EMA:4h positivo. Quando BTC EMA:4h também virar positivo (ainda -6 em 11/06), o universo pode expandir para 50-60%.

**Próximos passos:** registrar ilhas a cada snapshot. Quando BTC EMA:4h virar ≥ 0, medir expansão total e comparar com taxa de sinais disparados pelo SS.

---

## CRUZAMENTOS eAssets × LOGS SS

### A-05 — SPACEUSDT: ativo volátil com histórico de slippage extremo
**Status:** Risco documentado · atenção em snapshots futuros · 11/06/2026

SPACEUSDT apareceu em Tier 2 no snapshot 06:10 de 11/06 com estrutura aparentemente forte (EXP:1h=51.5, LSR:1h=-57.59, OI:1h=+159.74). No entanto, o SS teve neste ativo o pior trade da sessão atual: saída por stop_loss com MAE -38.9% — paper simulator capturou SL com 3.94% de slippage (preço caiu abaixo do SL de 2.5% antes do check discreto).

**Nota para análises futuras:** quando SPACEUSDT aparecer em candidatos, anotar o histórico de slippage extremo. Não é exclusão automática — mas é sinal de que o ativo pode ter gaps de liquidez que o paper simulator subestima.

**Dado a monitorar:** se SS entrar em SPACEUSDT novamente, comparar MAE com outros ativos de LSR similar. Se MAE sistematicamente maior → recomendar ao Brain ajuste de sizing ou exclusão do universo.

---

## TESES EM CONSTRUÇÃO

### TA-01 — FR × MFE: diferenciação por faixa de funding rate
**Status:** 🟡 Escalado ao Brain · registrado tasks.md v2.6 · 11/06/2026 — acionamento automático: ARIA avisa Brain ao contar 30+ trades pós-commit 3616b1b com funding_rate nos logs
**Conexão:** Tese T-06 do ARIA_CONTEXT.md

Com `funding_rate` agora presente nos logs reais (commit 3616b1b, D1), ARIA pode começar a auditar a relação entre FR e MFE nos trades.

**Hipótese ARIA (mais granular que T-06):**
- FR < 0: shorts pagando longs → squeeze mais violento quando desencadeia (longs têm incentivo de ficar)
- FR 0 a +0.001: neutro → sem pressão direcional
- FR +0.001 a +0.003: longs pagando shorts → shorts têm incentivo de aguentar = squeeze mais difícil
- FR > +0.003: longs pagando muito → pressão extrema de fechamento de longs → movimento mais imprevisível

**Paradoxo a investigar:** FR muito positivo pode ser catalisador T-06 (shorts forçados a fechar) OU sinal de overextension (longs pagando caro = mercado com muita crença direcional = risco de colapso). A direção do paradoxo depende do contexto de OI — OI crescendo = acumulação; OI caindo = saída.

**Auditoria planejada:** quando tivermos 30+ trades com `funding_rate` no log, categorizar por faixa de FR e calcular MFE médio, WR, e exit_reason mais comum.

---

### TA-02 — Convergência de timeframes curtos como sinal de iminência
**Status:** Hipótese observacional · sem dados ainda · 11/06/2026

Padrão observado em BRUSDT (A-02) e historicamente em VELVETUSDT (snapshot 10/06):
quando **OI:5m > OI:1h** (aceleração de curto prazo maior que aceleração de médio prazo), o movimento pode estar entrando em fase de aceleração, não desaceleração.

Analogia: se OI:1h=+63 mas OI:5m=+47 (numa janela que deveria ser ~1/12 do 1h se linear), o ritmo de acumulação está aumentando, não diminuindo.

**Dado que o SS monitora:** `oi_change_pct` (5m) e `oi_trend` (1h). São escalas diferentes mas ARIA pode tentar calcular a relação nos próximos snapshots quando tivermos os dados lado a lado com os logs.

**Próximos passos:** nos próximos 5 snapshots, calcular OI:5m/OI:1h normalizado para candidatos Tier 1 e 2. Se ativos com OI:5m/OI:1h > 0.4 (aceleração) tiverem performance melhor nos logs → encaminhar ao Brain como candidato a novo campo no signal dict.

---

## DESCOBERTAS DE PROCESSO

### AP-01 — analyze_eassets.py: auditoria post-hoc vs análise preditiva manual
**Status:** Distinção crítica · ativa desde 11/06/2026
**Referência:** feedback-aria-analise-eassets.md em memória

O script `aria/eAssets/analyze_eassets.py` (B-48) faz **auditoria post-hoc** — cruza trades já fechados com dados do eAssets. É diferente da **análise manual ARIA** que é preditiva: identifica candidatos antes do bot entrar.

As duas complementam:
- `analyze_eassets.py` → "o bot deveria ter entrado aqui com base no eAssets?"
- Análise manual ARIA → "esses são os ativos com maior probabilidade de squeeze nas próximas horas"

**Regra operacional:** quando Doreto pede análise do snapshot, ARIA entrega análise preditiva/estrutural completa primeiro. `analyze_eassets.py` é ferramenta suplementar para cruzamento pós-trade.

---

### AP-02 — Snapshots de coleta: pasta conhecida e controle de versão
**Status:** Referência permanente · 11/06/2026

Todos os snapshots eAssets ficam em:
`c:\Apps\#5 SqueezeSniper-V4\aria\eAssets\dados_eassets\`
Formato: `eassets-panel-YYYYMMDD-HHMMSS.json`

Snapshots analisados até hoje:
| Arquivo | Data/Hora UTC | Ativos | BTC |
|---------|--------------|--------|-----|
| eassets-panel-20260610-215848.json | 10/06 23:12 | 531 | $61.173 |
| eassets-panel-20260611-061006.json | 11/06 06:10 | 526 | $62.888 |

**Nota:** snapshots anteriores a 10/06 têm CVD e RSI calculados com dados Spot (bug fde21af) — inválidos para cruzamento com signal_engine. Usar apenas snapshots a partir de 10/06 para correlações quantitativas.

---

## BACKLOG DE ANÁLISES PENDENTES

### AP-03 — Cruzamento: ghost signals × candidatos eAssets
**Status:** Pendente · possível quando B-48 (analyze_eassets.py) estiver ativo
**Origem:** Padrão ALLOUSDT (1.009 near-misses sem entrar) · 09/06/2026

O eAssets vê os candidatos mais fortes. O SS filtra e bloqueia a maioria. A pergunta é: ativos que o eAssets ranqueia alto e o SS bloqueia sistematicamente — o que acontece com eles depois?

Se ARIA cruzar ghost_signals.jsonl com os candidatos Tier 1/2 dos snapshots e o ativo foi bloqueado antes de subir muito → evidência de que o gate está sendo muito conservador para esse tipo de setup.

**Pré-requisito:** `analyze_eassets.py` implementado + pelo menos 3 snapshots com trades correspondentes.

---

### AP-04 — Snapshot diário: horário ótimo de coleta
**Status:** Observação · baixa prioridade

Os dois snapshots disponíveis são de horários diferentes do dia (23:12 e 06:10 UTC). Para análise comparativa consistente, snapshots no mesmo horário são mais úteis.

**Hipótese:** 06:00–08:00 UTC pode ser uma janela de maior desacoplamento de altcoins vs BTC (Europa acordando, Ásia ainda ativa). A comparação dos dois snapshots disponíveis sugere que o movimento mais expressivo das ilhas aconteceu nesse período.

**Sugestão para Doreto:** quando possível, tirar snapshot sempre perto do mesmo horário para facilitar comparações ARIA. Sem urgência — análise qualitativa continua funcionando com snapshots irregulares.

---

## PATH B — MOMENTUM RIDER (estudos preparatórios · Brain · 12/06/2026)

> Estes itens são observacionais puros. Nenhum gera demanda ao Forge. ARIA coleta e reporta ao Brain quando os critérios de acionamento forem atingidos.

### A-06 — Continuação E-01: ampliar para múltiplos regimes
**Status:** Ativo — coleta contínua
**Origem:** Estudo E-01 · 12/06/2026 · N=14 insuficiente (1 dia, 1 regime)
**Critério de acionamento:** 20-30 observações com regimes distintos (BTC lateral, BTC subindo, fim de semana)

Estado atual: N=14 observações, todos de 11/06/2026, regime BTC bearish melhorando intraday. Padrões encontrados são encorajadores mas insuficientes para Brain formalizar o onset detector (E-02).

Protocolo de coleta:
- Tirar snapshots 2× por dia por 3-5 dias
- Priorizar dias com regime distinto do 11/06: BTC lateral, BTC subindo forte, fim de semana
- Para cada snapshot novo, aplicar os 4 critérios Path B (ema4h>=+4, range1h>=3, exp1h>10, lsr1h<=0) e registrar price_move no snapshot seguinte (>=2h depois)

Quando atingir 20+ observações: ARIA reporta ao Brain com distribuição atualizada de move >=+5%. Se taxa mantiver >=40% → Brain define E-02 (onset detector). Se cair abaixo → Brain reavalia os critérios.

Script de análise: `aria/scripts/analyze_path_b.py` já existe — basta rodar com novos snapshots.

---

### A-07 — FR como tier do Path B: monitorar e acumular
**Status:** Ativo — acumulação de evidência
**Origem:** Estudo E-01 · 12/06/2026 · N=2 (ESPORTSUSDT) insuficiente
**Critério de acionamento:** 20+ observações com `funding_rate` registrado no momento do snapshot

Hipótese a validar:
- FR > +0.001 + lsr_trend:1h <= 0 = move esperado 10%+ nas 4-8h seguintes (Tier A)
- FR neutro (-0.001 a +0.001) + lsr_trend:1h <= 0 = move 5-8% (Tier B)

Base atual: ESPORTSUSDT × 2 (FR=+0.44% e +0.52%, moves de +12.7% e +58.5%). N muito baixo para separar tiers.

Protocolo: a cada novo snapshot que tenha candidatos Path B confirmados (4 critérios), registrar o FR no momento e o move posterior. Acumular em tabela no próximo relatório ARIA ao Brain.

Quando atingir 20+ observações: ARIA segmenta por faixa de FR, calcula MFE médio e WR por tier, reporta ao Brain para formalizar ou descartar os dois tiers. Se confirmado, Brain decide: gate separado no score Path B ou peso no sizing.

---

### A-08 — EPICUSDT-type: demanda vs resistência de shorts (LSR positivo ambíguo)
**Status:** Ativo — monitoramento
**Origem:** Exceção E-01 · 12/06/2026 · EPICUSDT +21% com lsr_trend:1h=+28.7
**Critério de acionamento:** 10+ casos de LSR positivo que sobem vs 10+ casos que ficam flat

Questão central: quando lsr_trend:1h positivo significa "longs entrando com força" (demand breakout — território B-34) vs "shorts resistindo e aguentando" (sinal negativo para Path B)?

Observação inicial:
- EPICUSDT (S3→S4): lsr1h=+28.7, move=+21.2% — longs dominando com força, movimento real
- STARUSDT (S2→S3): lsr1h=+15.8, move=−8.0% — shorts resistindo, movimento falso
- BROCCOLIF3BUSDT (S2→S3): lsr1h=+40.3, move=−0.2% — shorts muito positivos, flat
- IOUSDT (S3→S4): lsr1h=+74.3, move=−3.4% — shorts dominantes, loser

Padrão preliminar: LSR positivo extremo (>+30) sem OI crescendo = shorts resistindo = excluir. LSR positivo moderado (+15 a +30) com OI crescendo = pode ser demand = observar. N ainda insuficiente para regra.

Protocolo: nos próximos snapshots, para ativos com ema4h>=+4 + lsr1h>0, registrar: lsr1h, oi_trend:1h, move posterior. Quando tiver 10+ de cada classe, ARIA propõe discriminador ao Brain.

---

### A-09 — Manutenção do universo Path B (E-04)
**Status:** Ativo — manutenção contínua
**Origem:** Estudo E-04 · 12/06/2026
**Critério de atualização:** a cada sessão ARIA com novos snapshots

Universo atual mapeado em 11/06/2026 (base de referência):

**Tier 1 — Acumulação máxima sustentada (4/4 snaps, range_level:1h alto):**
MANTAUSDT, BROCCOLIF3BUSDT, ASRUSDT, SOONUSDT

**Tier 2 — Tendência pura sustentada (4/4 snaps, sem range alto):**
PARTIUSDT, USUSDT, STGUSDT, VELVETUSDT, AIOUSDT, BEATUSDT, BRUSDT, BANKUSDT, CRVUSDT, ARCUSDT, HMSTRUSDT, FOLKSUSDT, BTCDOMUSDT*

*BTCDOMUSDT: rever se faz sentido no Path B — não é altcoin

**Tier 3 — Candidatos fortes mas menos consistentes (3/4 snaps):**
AIOTUSDT (range 4/4), OPENUSDT (range 4/4), ZEREBROUSDT (range 3/4), ESPORTSUSDT (case model — +58% e +12%), EPICUSDT (exceção LSR — ver A-08), FHEUSDT, POWERUSDT, MORPHOUSDT, BASUSDT

**Zona Cinza — Monitorar, sem posição ainda:**
GWEIUSDT (range 4/4 mas LSR sistematicamente positivo — flat/loser em E-01), CCUSDT (range 4/4, só 2/4 snaps), BIOUSDT, MAGMAUSDT, JCTUSDT, RUNEUSDT, outros

**Excluídos:**
- SPACEUSDT — slippage extremo documentado (A-05 do backlog). Excluir independente da performance.

Protocolo de atualização:
- Símbolo que aparecer em Tier 1/2/3 por 3+ sessões consecutivas entra na lista permanente
- Símbolo que deixar de aparecer com ema4h>=+4 por 2+ sessões consecutivas desce de tier ou sai
- ARIA reporta ao Brain se houver mudança de >5 símbolos na composição do Tier 1/2

---

_Revisão periódica: sempre que ARIA e Doreto se reunirem._
_Versão atual: 1.1 · 12/06/2026_
