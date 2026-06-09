# 🎯 Estratégias Operacionais: Squeeze Sniper + eAssets

**Versão**: 1.0  
**Objetivo**: Exponencialização de capital através de fluxos institucionais e tendências de alta convicção.

---

## 1. Sniper de Ignição Pura (Pure Ignition)

*Foco: Capturar a cascata de liquidação em milissegundos.*

### Gatilhos de Entrada

* **SS Score**: Mínimo 92 pontos.
* **Liquidação Real**: `liq_short_1m` > 0 (Obrigatório). Não operamos sem "sangue" no mercado.
* **Rampa de CVD**: `cvd_1m` deve estar em crescimento parabólico nos últimos 3 ticks.
* **Atividade HFT**: `trades_1m` > 80.

### Gestão de Saída

* **Squeeze Aborted**: Se em 60 segundos o lucro não atingir 0.5%, sair a mercado (o movimento falhou em gerar inércia).
* **Trailing Stop**: Ativação imediata com callback de 0.5% para proteger o spike.

### Nota do Engenheiro

Esta é a estratégia de maior frequência. O segredo aqui é a **pureza**. Se o score for técnico (RSI/EMA) mas não houver liquidação real, o Sniper deve permanecer em standby.

---

## 2. Surfista do Trendometer (Trend Rider)

*Foco: Eliminar o Alpha Decay e surfar tendências macro de 1h/4h.*

### Gatilhos de Entrada (Confluência eAssets)

* **Trendometer eAssets**: `EMA_Trend_1h` = +6 E `EMA_Trend_4h` >= +5.
* **Força Relativa**: `EXP_BTC_1h` > 20 (A moeda está ignorando a fraqueza do BTC).
* **Filtro de Gatilho**: O Sniper pode entrar com Score reduzido (80-85), desde que o `cvd_1m` seja positivo e o `rsi_5m` não esteja em zona de exaustão (>80).

### Gestão de Saída

* **Override de Tempo**: Desativar o `max_hold_seconds`. O tempo é seu aliado.
* **Trailing Stop Largo**: Distância de 2.5% a 3%. O objetivo é não ser expulso pelo ruído de 5 minutos enquanto a tendência de 1 hora continua.

### Nota do Engenheiro

Ideal para dias como o último final de semana. Resolve o problema de sair cedo demais de ativos que subiram 50%.

---

## 3. Breakout da Mola Comprimida (Coiled Spring)

*Foco: Antecipar a explosão de ativos em acumulação lateral.*

### Gatilhos de Entrada

* **Acumulação eAssets**: `range_level_1h` > 5 (Indica energia represada).
* **Injeção de OI**: `oi_change_pct:5m` > 5% (Dinheiro institucional entrando antes do preço romper).
* **Sentimento**: `lsr_trend` caindo agressivamente abaixo de -0.5.
* **Gatilho SS**: Entrada no primeiro spike de volume (`trades_level` subindo).

### Gestão de Saída

* **Alvo Estrutural**: Take Profit parcial no topo anterior do gráfico de 4h.
* **Stop Loss**: Fixo abaixo da mínima do range de acumulação.

### Nota do Engenheiro

Esta estratégia gera menos trades, mas são os que trazem o retorno exponencial. O `range_level` do eAssets é o seu indicador principal de "prontidão".

---

## 4. Caçador da Tempestade (BTC Reset Hunter)

*Foco: Comprar a capitulação e a retomada em V.*

### Gatilhos de Entrada

* **Estado do Mercado**: BTC Reset Monitor em "RESET EXTREMO" (RSI < 25 em múltiplos TFs).
* **Seleção de Ativo**: Filtrar no painel eAssets as moedas que mantiveram `EXP_BTC` positivo ou `CVD` estável enquanto o BTC caía.
* **Momento do Tiro**: Entrada quando o BTC Reset Monitor detecta o primeiro sinal de "V RELÂMPAGO".

### Gestão de Saída

* **Trailing Stop Curto**: 1.0% após atingir 2% de lucro.
* **Alvo**: Recuperação rápida. Sair se o momentum de 5m estagnar.

### Nota do Engenheiro

Esta estratégia protege você de "operar no vácuo". Você espera o mercado limpar a sujeira para entrar apenas nos ativos que provaram força relativa durante a queda.

---

## 🛡️ Regras de Ouro Transversais

1. **Veto de Fluxo**: NUNCA ignore o CVD. Se o preço sobe e o CVD cai, é uma armadilha. O gatilho deve ser abortado.
2. **Position Sizing**: Em estratégias de **Trend Rider**, use 50% da margem padrão. Em estratégias de **Ignition Sniper**, use 100%.
3. **Ambiente Macro**: Se o **CRM (Crypto Risk Meter)** estiver acima de 75, reduza o número máximo de posições abertas para 2, independentemente da estratégia.

---
**Próximo Passo**: ARIA deve validar a viabilidade técnica de automatizar os filtros de `EMA_Trend` e `range_level` para que o Sniper saiba qual "Modo de Caça" ativar.
