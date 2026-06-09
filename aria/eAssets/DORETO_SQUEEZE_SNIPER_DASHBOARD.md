# Doreto Squeeze Sniper — Dashboard
**Documento:** Funcionamento, Conceitos e Indicadores Proprietários  
**Versão:** 1.0 · **Data:** 05/06/2026  
**Autor:** Analista Eassets — sessão "Analista de dados Eassets"

---

## 1. Visão Geral

O **Doreto Squeeze Sniper Dashboard** é uma ferramenta de análise manual de oportunidades de long em futuros perpétuos da Binance USD-M. Ele foi construído como extensão da visão do **Eassets.ai** — um screener profissional que monitora, filtra e entrega oportunidades em tempo real — adaptado para o fluxo de trabalho do operador.

### Filosofia central

> O dashboard não toma decisões. Ele filtra ruído, organiza evidências e entrega convicção para que o operador decida com clareza.

### Como usar

1. Exportar o JSON do painel Eassets (filtros aplicados pelo operador)
2. Arrastar o arquivo no dashboard
3. Ler os candidatos ordenados por DNA Score
4. Clicar no ativo para ver o detalhe completo
5. Clicar no nome do ativo para abrir o CoinGlass (`Binance_SIMBOLOUSDT`)
6. Operar manualmente os setups de alta convicção

---

## 2. Arquitetura do Dashboard

```
┌─────────────────────────────────────────────────────┐
│  HEADER — identidade + snapshot + status            │
├─────────────────────────────────────────────────────┤
│  LINHA CRIPTO — componentes CRM + gauge CRM         │
│  LINHA MACRO  — componentes GRM + gauge GRM         │
├─────────────────────────────────────────────────────┤
│  BTC RESET MONITOR — RSI multi-TF + score           │
├─────────────────────────────────────────────────────┤
│  CONTEXT BAR — resumo do painel carregado           │
│  KPI ROW — ouro / atenção / OI / EMA / LSR          │
├──────────────────────────────┬──────────────────────┤
│  CANDIDATOS (3 colunas)      │  DETALHE DO SETUP    │
│  ordenados por DNA Score     │  EMA trend multi-TF  │
│  Ouro / Atenção / Descartado │  Range level multi-TF│
│                              │  Métricas completas  │
│                              │  Price change chart  │
└──────────────────────────────┴──────────────────────┘
```

### Fontes de dados

| Dado | Fonte | Frequência |
|---|---|---|
| Ativos e métricas | JSON Eassets (manual) | A cada exportação |
| BTC price + variação 24h | Binance API pública | A cada 3min |
| BTC.D, ETH.D, USDT.D | CoinGecko API | A cada 3min |
| Fear & Greed Index | Alternative.me API | A cada 3min |
| VIX, DXY, S&P500, Nasdaq, Gold | Yahoo Finance API | A cada 3min |
| RSI BTC multi-TF | Binance klines API | A cada 60s |

---

## 3. DNA Score — O filtro principal

O **DNA Score** é o motor de classificação dos candidatos. Ele aplica os critérios do Squeeze Sniper V4 sobre os dados do Eassets e gera um score de 0 a 100 para cada ativo.

### Critérios de pontuação

| Critério | Condição forte | Pontos | Condição média | Pontos |
|---|---|---|---|---|
| OI Trend 5m | ≥ 15 | +25 | ≥ 8 | +15 |
| LSR Trend 5m | ≤ -15 | +25 | ≤ -8 | +15 |
| EXP BTC 5m | ≥ 15 | +15 | ≥ 8 | +10 |
| EMA alinhamento | 5m≥5 e 1h≥4 | +15 | 5m≥4 | +8 |
| RSI 5m | 55–75 | +10 | — | — |
| Range confluência | ≥ 6 (multi-TF) | +10 | ≥ 3 | +5 |

### Penalidades automáticas

| Condição | Penalidade | Motivo |
|---|---|---|
| EMA:1h ≤ -4 | -20 | Macro bearish — trap clássico |
| RSI:1h < 40 | -15 | Oversold no swing — tendência de baixa |
| LSR ratio > 2.0 | -10 | Dominância excessiva de longs |
| RSI:5m > 75 | -5 | Sobrecomprado no curto prazo |

### Classificação

| Score | Categoria | Ação sugerida |
|---|---|---|
| ≥ 70 | **Ouro — Alta Convicção** | Avaliar entrada com atenção plena |
| 40–69 | **Atenção** | Verificar alertas antes de entrar |
| < 40 | **Descartado** | Ignorar nesta janela |

---

## 4. CRM — Crypto Risk Meter

**Indicador proprietário Doreto.**

Mede o nível de risco do ambiente cripto em tempo real. Score 0–100 calculado a partir dos fluxos de capital e sentimento do mercado de futuros. Quanto mais alto, mais adverso o ambiente para entradas long.

### Componentes e pesos

| Componente | Peso | Lógica |
|---|---|---|
| USDT.D | **35%** | Fuga para stable = medo. > 7% = sinal de alerta |
| Fear & Greed Index | **25%** | Sentimento invertido: medo extremo = oportunidade |
| BTC variação 24h | **20%** | Tendência macro do mercado cripto |
| Funding Rate média | **12%** | Viés do mercado de futuros — calculado dos ativos do painel |
| ETH.D | **8%** | Saúde das altcoins — ETH fraco = alts sem sustentação |

### Lógica do Fear & Greed — inversão intencional

> **A lógica do FGI é invertida no CRM** em relação ao uso tradicional.

O operador opera **contra a manada**. Medo extremo (FGI < 20) significa que o mercado desalavancou, as liquidações limparam o mercado, e o terreno está fértil para reversão. Ganância extrema (FGI > 80) significa mercado alavancado demais — risco real de long trap.

| FGI | Significado tradicional | Significado para este operador |
|---|---|---|
| < 20 Medo Extremo | Alto risco | **Oportunidade** — manada desalavancada |
| 20–40 Medo | Cautela | **Zona positiva** de atenção |
| 40–60 Neutro | Neutro | Neutro |
| 60–80 Ganância | Otimismo | **Atenção** — mercado alavancado |
| > 80 Ganância Extrema | Euforia | **Risco real** — long trap iminente |

### Escala de risco

| Score | Estado | Interpretação |
|---|---|---|
| 0–30 | 🟢 Baixo | Ambiente favorável para longs |
| 31–55 | 🟡 Moderado | Atenção, mercado misto |
| 56–75 | 🟠 Elevado | Seletividade máxima |
| 76–100 | 🔴 Crítico | Evitar novas entradas |

---

## 5. GRM — Global Risk Meter

**Indicador proprietário Doreto.**

Mede o apetite de risco dos mercados financeiros globais. Quando o GRM sobe, o capital migra para ativos seguros — afetando indiretamente o cripto. A correlação entre macro global e volatilidade cripto tem crescido consistentemente desde 2022.

### Componentes e pesos

| Componente | Peso | Lógica |
|---|---|---|
| VIX | **35%** | Índice do medo do S&P500. O mais importante. |
| DXY | **25%** | Força do dólar vs cesta de moedas. Dólar forte = fuga de risco |
| S&P 500 variação | **20%** | Termômetro do apetite de risco americano |
| Gold variação | **12%** | Gold subindo + bolsas caindo = fuga dupla para segurança |
| Nasdaq variação | **8%** | Tech lidera ciclos risk-on/risk-off |

### Lógica do VIX — o mais importante

| VIX | Estado | Impacto no cripto |
|---|---|---|
| < 13 | Calmo extremo | Risco-on total — favorável |
| 13–17 | Calmo | Neutro-positivo |
| 17–22 | Atenção | Volatilidade crescendo |
| 22–28 | Nervoso | Pressão em ativos de risco |
| 28–35 | Pânico parcial | Desalavancagem iniciando |
| > 35 | Pânico total | Desalavancagem global — evitar longs |

### Lógica do Gold + DXY simultâneos

Quando **Gold sobe** e **DXY sobe** ao mesmo tempo com bolsas caindo = fuga dupla para segurança. É o sinal mais claro de saída de capital de risco. O GRM recebe bônus adicional neste cenário.

### Escala de risco

Mesma escala do CRM: 0–30 Baixo · 31–55 Moderado · 56–75 Elevado · 76–100 Crítico.

---

## 6. BTC Reset Monitor

**Indicador proprietário Doreto — conceito pouco explorado no mercado.**

Mede o nível de desalavancagem do BTC em múltiplos timeframes simultaneamente. Baseado na teoria de que mercados de cripto, por serem altamente alavancados, precisam de um processo de "limpeza" antes de novos movimentos sustentados.

### A teoria da Tempestade e Bonança

```
FASE 1 — TEMPESTADE
├── BTC RSI despenca para < threshold em múltiplos TFs
├── Liquidações em massa acima do threshold configurado
├── Altcoins caem junto — alavancagem sendo destruída
└── Manada vende com medo (FGI cai)

FASE 2 — RESET CONFIRMADO
├── RSI < threshold em N timeframes simultaneamente
├── Liquidações confirmam a intensidade
└── Mercado desalavancado = slate limpo

FASE 3 — BONANÇA
├── Ativos que resistiram melhor na queda lideram
├── EXP_BTC positivo durante a queda = força relativa
└── Reversão mais rápida e mais potente
```

### Pesos por timeframe

| TF | Peso | Significado |
|---|---|---|
| 5m | 8 | Microdesalavancagem — sinal fraco isolado |
| 15m | 12 | Desalavancagem intraday curta |
| 30m | 15 | Desalavancagem intraday relevante |
| 1h | 20 | Desalavancagem real — peso significativo |
| 4h | 25 | Limpeza estrutural — peso alto |
| 12h | 30 | Desalavancagem macro — peso muito alto |
| 1D | 35 | Reset histórico — peso máximo |

> TFs mais longos têm peso maior porque um RSI < 30 no 4h é estruturalmente muito mais significativo que no 5m.

### Multiplicador de liquidações

| Liquidações BTC 1h | Multiplicador | Interpretação |
|---|---|---|
| < 50% do threshold | 0.70 | Sem confirmação institucional |
| 50–100% do threshold | 0.85 | Confirmação parcial |
| 100–200% do threshold | 1.00 | Confirmação — reset válido |
| 200–500% do threshold | 1.15 | Confirmação forte |
| > 500% do threshold | 1.30 | Evento histórico |

### Detecção de padrão V (Reset Relâmpago)

O V é o cenário mais difícil e mais lucrativo. Ocorre quando:

```
RSI mínimo recente < threshold (tocou a zona de reset)
E RSI atual > 50 (já recuperou)
E duração < 3 candles (queda e recuperação rápidas)

→ Badge "V ↑" no card do TF
→ Bônus de +15 no RESET SCORE
→ Estado "V RELÂMPAGO" se V confirmado em 2+ TFs
```

**Diferença entre V espúrio e V real:**
- V no 5m por 3 minutos = spike de venda, não reset real
- V no 1h ou 4h = reset real e rápido — mais raro, mais poderoso

### Estados globais

| Estado | Score | Condição | Ação |
|---|---|---|---|
| ⚫ NEUTRO | 0–24 | Mercado normal | Operar normalmente |
| 🟡 RESET PARCIAL | 25–49 | TFs curtos resetando | Atenção, tempestade chegando |
| 🟠 RESET FORTE | 50–74 | TFs longos incluídos | Aguardar, bonança próxima |
| 🔴 RESET EXTREMO | 75–100 | Limpeza total | Identificar candidatos pós-reset |
| 🟢 V RELÂMPAGO | — | V em 2+ TFs | Sinal de entrada imediata |

### Parâmetros configuráveis

| Parâmetro | Padrão | Como calibrar |
|---|---|---|
| **LIQ THRESHOLD** | 10M USD | Ajustar após análise de gráfico mensal/anual. Cresce com o mercado. |
| **RSI RESET** | 30 | Ajustar conforme observação. Mercados muito alavancados podem precisar de 25. |

> **Nota importante:** O threshold de liquidações deve ser revisado periodicamente. À medida que mais capital institucional entra no cripto, os volumes de liquidação crescem — o threshold de hoje pode ser irrelevante daqui a 1 ano.

### Pós-RESET: como identificar os candidatos da bonança

Após RESET FORTE ou EXTREMO confirmado, filtrar no dashboard:

1. **EXP_BTC positivo ou menos negativo** durante a queda — o ativo resistiu
2. **OI trend voltando positivo** antes do BTC — smart money entrando antes
3. **LSR trend caindo** — shorts sendo fechados = reversão em curso
4. **Range level 5m/15m subindo** — acumulação silenciosa enquanto mercado cai

---

## 7. Integração dos indicadores

Os três indicadores proprietários funcionam em camadas:

```
CAMADA 1 — CONTEXTO GLOBAL
GRM alto → capital saindo de risco → ser mais seletivo

CAMADA 2 — CONTEXTO CRIPTO  
CRM alto → ambiente cripto adverso → aguardar ou reduzir posições
CRM baixo com FGI baixo → oportunidade contra a manada

CAMADA 3 — TIMING DE ENTRADA
RESET FORTE/EXTREMO → tempestade passou → procurar candidatos
DNA Score alto + EXP_BTC resistente → entrada de alta convicção

LEITURA IDEAL PARA LONG:
GRM moderado + CRM moderado/baixo + RESET confirmado 
+ DNA Score ≥ 70 + EXP_BTC positivo
= Setup de máxima qualidade
```

---

## 8. Limitações e calibrações futuras

### O que este dashboard **não** faz
- Não executa ordens — é ferramenta de análise manual
- Não substitui o SS para operações automatizadas
- Não garante resultado — é probabilidade, não certeza

### Calibrações pendentes
- **Pesos do DNA Score** — ajustar após 50+ trades do SS com evidência estatística
- **LIQ THRESHOLD do RESET** — calibrar após análise de histórico de 6–12 meses
- **Peso do FGI no CRM** — atualmente 25%, pode ser reduzido conforme validação
- **Threshold EXP_BTC** para identificação de resistentes pós-RESET

### Próximas evoluções planejadas
- Integração automática via API Eassets (quando disponível)
- Alertas sonoros em RESET EXTREMO e V RELÂMPAGO
- Histórico de snapshots para comparar ambientes diferentes
- Seção de candidatos pós-RESET com filtro automático de EXP_BTC

---

## 9. Glossário

| Termo | Definição |
|---|---|
| **DNA Score** | Score 0–100 baseado nos critérios do Squeeze Sniper aplicados aos dados do Eassets |
| **CRM** | Crypto Risk Meter — indicador proprietário de risco do ambiente cripto |
| **GRM** | Global Risk Meter — indicador proprietário de risco macro global |
| **RESET** | Processo de desalavancagem do BTC medido por RSI < threshold em múltiplos TFs |
| **V Relâmpago** | Padrão de queda violenta com recuperação imediata — sinal de entrada explosivo |
| **Bonança** | Período pós-RESET onde altcoins resistentes lideram a recuperação |
| **EXP_BTC** | Força exponencial do ativo vs BTC — positivo = ativo mais forte que o BTC |
| **OI Trend** | Inclinação do Open Interest — subindo = novas posições entrando |
| **LSR Trend** | Inclinação do Long/Short Ratio — caindo = shorts fechando = pressão comprada |
| **Range Level** | Nível de acumulação lateral — alto = compressão antes do movimento |
| **VIX** | Índice de volatilidade implícita do S&P500 — "índice do medo" do mercado global |
| **DXY** | Dollar Index — força do dólar vs cesta de moedas. Alto = pressão em risco |

---

*Doreto Squeeze Sniper Dashboard — documentação v1.0*  
*Construído em sessão conjunta: Doreto + Analista Eassets · 05/06/2026*  
*Todos os indicadores proprietários são de autoria de Bob Doreto*
