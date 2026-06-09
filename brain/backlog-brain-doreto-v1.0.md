# Backlog Estratégico — Brain × Doreto
_Documento vivo · atualizado conforme novas ideias chegam_
_Criado: 04/06/2026 · Versão: 1.0_

> Este documento é nosso — Brain e Doreto. Não é fila do Forge. É onde guardamos ideias, hipóteses e visões antes de decidir se viram task, se precisam de mais dados, ou se descartamos. Revisamos periodicamente: incluímos, alteramos, removemos.

---

## LÓGICA DO BOT / ESTRATÉGIA

### B-01 — Reset do BTC e capitulação por múltiplos TF
**Status:** Hipótese estratégica · aguarda volume de trades  
**Origem:** Experiência do Doreto com mercado crypto

O BTC periodicamente faz "faxina de liquidez para baixo" antes de respirar e subir. Isso acontece em ciclos de semana a semana, não só nos ciclos macro. A ideia é monitorar BTC em múltiplos TF (5m, 15m, 30m, 1h, 4h, 1d) para identificar o "modo" atual — capitulação ou recuperação — e usar isso como filtro de contexto para o Sniper.

Observação chave do Doreto: mesmo com BTC sangrando, SEMPRE tem alguma coin com EXP_BTC forte subindo em busca de liquidez e stops de shortados. O Sniper já é LONG ONLY — essa observação reforça que o filtro não deve ser "BTC caindo = não operar" mas sim "BTC caindo = filtrar ainda mais por EXP_BTC forte".

**Próximo passo:** cruzar dados de trades com contexto de BTC no momento da entrada quando tivermos 50+ trades. Verificar se há correlação entre EXP_BTC:1h negativo e losers.

---

### B-02 — Limites de margem da Binance por tier e símbolo
**Status:** Hipótese com evidência parcial → virou TASK F-03  
**Origem:** Observação do Doreto sobre seu tier na Binance

Cada símbolo tem bracket tiers que definem o notional máximo por faixa de alavancagem. O bot pode estar calculando sizing sem consultar esses limites. Já escalado para o Forge como Task F-03.

**Observação para quando os dados chegarem:** com $10k de capital e 5% de risco, a $500 de margem com 10x = $5000 notional. Verificar se símbolos menores (MEME, ZBT, etc.) têm bracket tier que limita abaixo disso.

---

### B-03 — BTC.D, USDT.D, OTHERS.D em múltiplos TF
**Status:** Parcialmente documentado no tasks.md anterior  
**Origem:** Doreto + visão macro de fluxo de capital

BTC.D e USDT.D mostram para onde o capital está indo — dolarização vs rotação para altcoins. OTHERS.D mostra força das small caps. Juntos formam um painel de contexto macro que complementa o EXP_BTC do Sniper.

Ideia: bloco "Macro Cripto" no topo do dashboard com BTC.D, USDT.D, OTHERS.D e Fear & Greed do CoinMarketCap (Doreto já tem a chave de API no `.env`).

**Próximo passo:** quando GRM (B-05) for para desenvolvimento, esses dados entram juntos.

---

### B-04 — Override manual de trade específico
**Status:** Backlog · Sprint 5+  
**Origem:** Doreto — experiência de trading manual paralelo ao bot

Quando Doreto estiver operando ao lado do Sniper e identificar que um trade aberto tem potencial de 10-40% (muito além do trailing stop atual), ele quer poder assumir controle daquele trade específico de forma manual sem interferir nos demais.

Dois modos discutidos:
- Override individual: Doreto assume 1 trade específico
- All manual: todos os trades ficam em modo manual simultaneamente

**Consideração:** em modo manual, o trailing stop e o SL automático precisam ter comportamento definido — ficam ativos? São desativados? Doreto decide na hora?

**Próximo passo:** desenhar o fluxo de UX antes de especificar para o Forge. Baixa urgência até Live com capital relevante.

---

## DASHBOARD / UX

### B-05 — GRM (Global Risk Management) no dashboard
**Status:** Backlog · prioridade média-alta para quando Live  
**Origem:** Doreto tem código de outro projeto (King Kong) com parte disso implementado

Visão do Doreto: bloco no topo do dashboard com:
- Fear & Greed Index (CoinMarketCap — chave já no `.env`)
- BTC.D, ETH, BTC em destaque
- Índices tradicionais: US500, Nikkei, DAX, China (via yfinance)

**✅ Módulo garimpado do King Kong — 04/06/2026**

`cmc_client.py` está pronto para reaproveitamento direto. Cliente assíncrono (aiohttp) com dois métodos:
- `get_quotes(symbols)` — cotações de símbolos específicos
- `get_global_metrics()` — dados globais incluindo Fear & Greed e OTHERS.D

Chave de API já existe no `.env` do Sniper. Adaptação é mínima — integrar ao `data_engine.py` e expor no dashboard.

**Próximo passo:** quando B-05 entrar em sprint, Brain prepara briefing para o Forge com o `cmc_client.py` como base. Forge não constrói do zero.

---

### B-06 — Painel dedicado por trade aberto
**Status:** Backlog · Sprint 4+  
**Origem:** Doreto — visão de UX granular por posição

Quando múltiplas posições estiverem abertas simultaneamente, um card/painel dedicado por trade com dados completos (entrada, MFE atual, MAE, SL/TP, tempo aberto, DNA do sinal) melhora muito o acompanhamento. Similar ao painel da Binance mas integrado ao dashboard do Sniper.

Ideia adicional: ao acionar modo Live, abrir nova janela do browser dedicada ao Live com esse cockpit completo.

---

### B-07 — Abrir Coinglass automaticamente no trade aberto
**Status:** Backlog · Sprint 4+  
**Origem:** Doreto tem código de outro projeto que faz isso

Quando um trade é aberto (paper ou live), o browser abre automaticamente a página do Coinglass para aquele símbolo. Doreto pode contribuir com o código base do projeto anterior.

**Próximo passo:** Doreto compartilha o trecho relevante do King Kong quando for a hora.

---

### B-08 — Gráficos do dashboard — placeholder visual
**Status:** ✅ Virou TASK F-06 · 04/06/2026  
Substituir canvas vazio por mensagem "aguardando primeiros trades". Escalado para o Forge.

---

## INFRAESTRUTURA

### B-09 — Rodar na nuvem 24h/365d
**Status:** Backlog · Sprint 6+  
**Origem:** Necessidade operacional para Live real

VPS de ~$10-20/mês (Hetzner, DigitalOcean, AWS Lightsail) resolve. Precisa de configuração de ambiente Python, variáveis `.env`, e monitoramento de uptime. Entra no planejamento quando o bot estiver em Live com capital validado.

---

### B-10 — Controle orgânico de alavancagem e sizing
**Status:** Backlog · Sprint 5+  
**Origem:** Doreto — visão de automação completa

Quando o Sniper estiver maduro (WR validado, 50+ trades, Profit Factor > 1.5), o sizing pode evoluir para se auto-calibrar dentro dos limites de risco definidos — alavancagem e tamanho de posição ajustados organicamente pelo histórico real, não só pelo Kelly estático.

**Pré-requisito:** volume de trades + WR consistente + DrawdownManager estável.

---

## DESCARTADO / FORA DE ESCOPO AGORA

### D-01 — Engenharia reversa do EAssets
Doreto usa como inspiração. Fica para outro momento — Sniper precisa de validação primeiro.

### D-02 — PC da Sarah e chave da Dani
Operacional, não técnico. Quando chegar a hora: instalar Python, clonar repo, criar chaves API da Binance. Sem data.

### D-03 — Filtros semanais/mensais de BTC
O Sniper opera dia a dia em tempo real. Filtros semanais e mensais são macros demais para o ciclo atual. Revisar quando estiver em Live estável.

---

## CONTRIBUIÇÕES DE CÓDIGO DO DORETO (projeto King Kong)

Módulos garimpados pelo Brain em 04/06/2026. Status de reaproveitamento definido por leitura real do código.

### cmc_client.py ✅ PRONTO PARA USAR
Cliente assíncrono CoinMarketCap (aiohttp). Dois métodos: `get_quotes(symbols)` e `get_global_metrics()` — Fear & Greed e OTHERS.D saem daqui. Chave de API já no `.env` do Sniper. Adaptação mínima — integrar ao `data_engine.py`. Relacionado ao B-05 (GRM) e B-03.

### telegram_client.py ✅ APROVEITAMENTO PARCIAL
Arquivo de 1050+ linhas — só as primeiras ~190 são úteis. A classe `TelegramClient` com `send_message` (aiohttp, SSL, retry, botões inline) é o que o Sniper precisa para alertas no celular. O restante é o sistema de alertas completo do King Kong (tipos, gate Redis, CSV log) — descarta. Dependência a remover: `import calibration_config as cfg` → substituir por `preferences.json`. Relacionado ao B-14 (novo item — alertas Telegram).

### multitf_confluence.py ✅ LÓGICA PORTÁVEL, ALTO VALOR
A função `compute_symbol_confluence` é pura e portável — calcula confluência em múltiplos TF (5m, 15m, 1h, 4h, 1d) usando `close`, `exp_btc`, `volume`, `trade_count`, OI, CVD e LSR com bônus derivativo. Output limpo: `mtf_side`, `mtf_confluence` (0-100), `mtf_net`. Diretamente alinhado com o DNA do Sniper. Barreira: depende de CSVs por símbolo e Redis para cache — Forge adapta para usar dados do `data_engine.py`. Relacionado ao B-01.

### regime_classifier.py ⚠️ REFERÊNCIA CONCEITUAL APENAS
Lógica de estados (breakout, compression, exhaustion, chop) é boa como arquitetura. Mas usa campos que o Sniper não tem e contradiz o DNA em um ponto crítico: RSI > 80 = avoid, enquanto no Sniper RSI alto é combustível. Não integrar diretamente — usar como referência para B-11 (saída inteligente).

### CVDTracker.py 📚 REFERÊNCIA DE ARQUITETURA
CVD com gestão de memória robusta, cleanup 48h, deque com hard cap. O Sniper tem CVD próprio. Consultar se houver instabilidade de memória no futuro.

**Próximo passo por módulo:**
- `cmc_client.py` → quando B-05 entrar em sprint
- `telegram_client.py` → quando B-14 entrar em sprint (primeiras 190 linhas)
- `multitf_confluence.py` → quando B-01 entrar em sprint (função `compute_symbol_confluence`)

---

---

## IDEIAS DO BRAIN — aguardando dados para confirmar

### B-11 — Saída inteligente por esgotamento do squeeze
**Status:** Hipótese Brain · aguarda 50+ trades  
**Origem:** Brain — análise do Post-Trade Impact (ZBT e MEME continuaram subindo após saída)

O Sniper hoje sai por trailing stop ou MAE gate — saída mecânica. Mas o squeeze tem sinais de esgotamento que o sistema já coleta e ignora na hora da saída: CVD começando a cair, OI recuando, LSR virando. A ideia é usar esses mesmos sinais da entrada como gatilho de saída antecipada — "o squeeze acabou, sai agora" antes do trailing ser acionado pela queda de preço.

**Pré-requisito:** 50+ trades com signal dict completo (22 campos) para identificar o padrão de CVD/OI no momento do esgotamento. Sem dados não tem padrão.

**Próximo passo:** quando tivermos volume, Brain cruza CVD/OI no momento da saída com resultado do trade. Se padrão confirmado, vira task para o Forge.

---

### B-12 — Filtro de qualidade do universo monitorado por tier de liquidez
**Status:** Hipótese Brain · aguarda dados distribuídos por símbolo  
**Origem:** Brain — observação de que MEMEUSDT e BTCUSDT são tratados com a mesma lógica

Símbolos com volume médio diário baixo têm spread maior, maior susceptibilidade a manipulação, e squeezes que podem ser artificiais. O score atual não diferencia um símbolo de $2M/dia de um de $500M/dia. Proposta: separar o universo em tiers de liquidez e calibrar thresholds de score diferente por tier — não para excluir small caps, mas para exigir mais confirmação deles.

**Pré-requisito:** trades suficientes distribuídos por diferentes símbolos para ver se small caps têm WR sistematicamente pior ou resultado diferente. Hoje com 4 trades não diz nada.

---

### B-14 — Alertas Telegram no trade aberto/fechado
**Status:** Backlog · Sprint 4+  
**Origem:** King Kong tinha isso implementado e funcionando

Quando um trade abre ou fecha no Sniper (paper ou live), enviar notificação via Telegram com símbolo, direção, PnL, motivo de saída. Útil especialmente em Live quando você não está olhando o dashboard — trade às 3h da manhã chega no celular.

**Módulo pronto:** `telegram_client.py` — primeiras ~190 linhas (classe `TelegramClient` + `send_message`). Depende só de `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` no `.env`. Remover dependência de `calibration_config` e substituir por `preferences.json`.

**Próximo passo:** quando entrar em sprint, Brain prepara briefing com as 190 linhas relevantes isoladas. Forge integra ao `paper_tracker.py` e `live_tracker.py`.

---
**Status:** Hipótese Brain · aguarda evidência de reentrada ruim  
**Origem:** Brain — raciocínio sobre reconstituição de liquidez pós-squeeze

Após um squeeze encerrar em determinado símbolo, o ativo precisa de tempo para reconstituir liquidez antes do próximo movimento real. Reentrar imediatamente pode ser embarcar na exaustão do squeeze anterior. Proposta: cooldown configurável por símbolo após saída — exemplo, não reentrar em AR por 15 minutos após fechar posição nele.

**Pré-requisito:** identificar nos logs casos de reentrada rápida no mesmo símbolo e verificar se o resultado foi ruim. Hoje o universo é amplo o suficiente para o Sniper raramente reentrar no mesmo símbolo rapidamente — mas vale monitorar.

### B-15 — Filtro mínimo de Tr/1m antes da entrada
**Status:** ✅ VALIDADO · threshold=50 confirmado · entra no próximo restart  
**Origem:** Análise acumulada de 3 sessões · 04-05/06/2026

Padrão confirmado em 3 sessões distintas com 25+ trades:
- Winners média Tr/1m: 240-306
- Losers/squeeze_failed média Tr/1m: 18-100
- Squeeze_failed desta noite média: 18 Tr/1m

Threshold de 50 testado na sessão de 05/06: bloquearia 5/5 squeeze_failed, zero winners perdidos. WR dos que passariam: 67% vs 25% atual.

Valor atual em memória: **2** (essencialmente desativado). Valor validado: **50**.

**BABY é o outlier documentado:** 129 Tr/1m, passou pelo filtro, pior MAE da coleta (-18.04%). Tr/1m alto é proteção de entrada, não garantia de qualidade — spike de volume sem sustentação. Conecta com EA-05 (B-19).

**Próximo passo:** no restart planejado, Forge atualiza `min_trades_1m = 50` no `preferences.json` antes de subir.

---

### B-16 — squeeze_failed em cascata durante alta volatilidade (Squeezometer 80+)
**Status:** Hipótese com evidência · aguarda confirmação em mais sessões  
**Origem:** Análise dos 10 trades de 04/06/2026

Entre 09:24 e 11:45, com Squeezometer em 80-83 (alertas de volatilidade extrema), o sistema entrou em 5 trades consecutivos todos saindo por `squeeze_failed` com MFE = 0.00%. Alta atividade institucional mas sem direcionalidade — mercado em modo de volatilidade bidirecional.

Hipótese: quando o Squeezometer está acima de 80 mas os trades individuais não decolam, o mercado está em volatilidade sem tendência definida — pior cenário para o Sniper. Paradoxalmente, Squeezometer alto pode ser sinal de cautela, não de oportunidade.

**Proposta:** avaliar se faz sentido reduzir `max_open_positions` ou aumentar threshold de score quando Squeezometer > 80 sem confirmação de `liq_cascade`. Aguarda mais dados — pode ser coincidência desta sessão.

---

### B-17 — FORM saiu squeeze_failed mas foi +1.88% em 5min depois
**Status:** Caso isolado · monitorar recorrência  
**Origem:** Post-Trade Impact de 04/06/2026

FORMUSDT saiu por `squeeze_failed` com MFE 0.02% às 10:39. Cinco minutos depois o preço subiu +1.88%, e +2.16% em 30min. O gate de 90s expulsou uma entrada que teria sido winner com mais 2 minutos de tolerância.

Isso se conecta ao B-11 (saída inteligente) e levanta questão sobre o timeout do `squeeze_failed`: 90s é muito curto para alguns ativos de menor liquidez onde o movimento demora um pouco mais para se confirmar?

**Próximo passo:** monitorar casos semelhantes. Se padrão se repetir (squeeze_failed seguido de movimento positivo no Post-Trade), revisar o timeout de 90s como hipótese para o Forge investigar.

---

### B-18 — ZBT e ID marcados "Saiu Cedo" no Post-Trade
**Status:** Observação · monitorar  
**Origem:** Post-Trade Impact de 04/06/2026

ZBT saiu por trailing_stop com +0.51% mas foi +3.00% depois. ID saiu por squeeze_failed mas foi +2.89% depois. Dois casos de "Saiu Cedo" em 10 trades.

Para ZBT o trailing capturou parte — é comportamento esperado do sistema. Para ID o squeeze_failed foi correto — o preço voltou mas isso não significa que a entrada estava certa.

Relacionado ao B-11 (saída inteligente por esgotamento). Monitorar se "Saiu Cedo" aparece sistematicamente nos trailing_stop winners — indicaria que o trailing está muito conservador para certos ativos.

---

### B-19 — EA-05: trades_second multi-TF — spike vs pressão sustentada
**Status:** Backlog · prioridade elevada para Sprint 4 · primeiro caso documentado em 05/06/2026  
**Origem:** Analista Externo EA-05 + caso BABY 05/06/2026

O eAssets usa "Trades por Segundo" para distinguir spike pontual de pressão algorítmica contínua. BABY foi o primeiro caso documentado no Sniper que justifica essa distinção: 129 Tr/1m (passaria pelo filtro de 50) mas comportamento de spike sem sustentação — pior MAE da coleta (-18.04%).

Hipótese: `trades_1m` alto pode ser spike de 1 minuto. `trades_second` no 5m mostra se a pressão é sustentada ou momentânea. Um ativo com 129 Tr/1m mas `trades_second:5m` baixo é spike — não é presença institucional contínua.

**Primeiro caso concreto:** BABY 05/06 — 129 Tr/1m, passou filtro, entrou em spike, MAE -18.04%.

**Pré-requisito:** `trades_second` já existe no signal dict? Verificar com Forge antes de sprint. Se não existe, é trabalho de MetricStore primeiro.

**Próximo passo:** quando tivermos 30+ trades, verificar se BABY tem padrão similar em outros losers com Tr/1m alto.

---

Nenhuma ação imediata — serve como validação externa da lógica do Sniper.

---

### B-20 — Queda de atividade do Sniper ao longo do tempo — inteligência ou bloqueio silencioso?
**Status:** Em observação ativa · RSI 45 implementado · 09/06/2026  
**Origem:** Experiência do Doreto — padrão sentido em múltiplas sessões

Após um determinado tempo rodando, a frequência de trades do Sniper cai visivelmente.

**Evidência da sessão 09/06 aponta para Hipótese B (bloqueio silencioso):**
2760 refusals em ~4 horas, 84% concentrado em 5 motivos. `rsi_lt_min_rsi_5m` com threshold 60 gerou 510 bloqueios (18.5%) — ativos em zona de acumulação RSI 45-60 sendo recusados sistematicamente. `cvd_negative_quarantine` 727 bloqueios — parte pode ser ruído de 5m sem contexto de 1h.

Com `min_rsi_5m` ajustado para 45, a próxima sessão longa deve mostrar redução significativa. ARIA compara distribuição de refusals pré (threshold 60) vs pós (threshold 45) na próxima análise.

**Próximo passo:** sessão com 4+ horas de dados. Se `rsi_lt_min_rsi_5m` cair de 18.5% para < 8%, o ajuste foi efetivo.

---

### B-21 — CVD alto como possível sinal de exaustão — CONFIRMADO e RESOLVIDO via B-37
**Status:** ✅ Confirmado · resolvido via gate volume_quality (F-15) · 09/06/2026  
**Origem:** Análise cruzada Brain + Analista Externo · 04/06/2026

Com 42+ trades acumulados o padrão se confirmou consistentemente: winners média volume_quality=0.535, losers média volume_quality=1.502 (3x maior). STGUSDT vq=16.20 — loser. CVD explosivo sem sustentação de trades = spike, não squeeze.

**Resolvido via B-37/F-15:** gate `volume_quality < 2.0` implementado em Sprint 3 (commit 7bc9aab). Normaliza CVD pelo número de trades — distingue spike de pressão sustentada de forma mais precisa que CVD bruto.

**Não implementar gate adicional de CVD bruto** — volume_quality já captura este comportamento.

### B-22 — Volume de signal_refusals possivelmente inflado
**Status:** Hipótese observacional · aguarda análise com dados  
**Origem:** Observação do Doreto · 04/06/2026

Em menos de 30 minutos após restart limpo o contador de refusals já ultrapassou 3.000. Doreto observa que sessões de 4-8h não parecem ter volume muito maior — sensação de que o número cresce rápido no início e desacelera depois, ou que está sendo inflado.

**Duas hipóteses:**

Hipótese A — volume real: o Sniper varre 200+ símbolos em ciclos contínuos de segundos. 10-20 refusals por ciclo × ciclos por minuto = milhares por hora. Comportamento correto.

Hipótese B — inflação por múltiplos gates: `_maybe_log_refusal()` pode estar sendo chamado para cada gate que falha individualmente em vez de só o primeiro. Um símbolo que falha em 5 gates grava 5 refusals em vez de 1 — inflando o contador sem representar 5 oportunidades perdidas distintas.

**Como confirmar:** analisar distribuição de refusals por símbolo por minuto com `reason_code` correto. Se mesmo símbolo aparece 50x no mesmo minuto com reason_codes diferentes — é inflação. Se distribuído entre símbolos — é volume real.

**Próximo passo:** Brain analisa `signal_refusals.jsonl` após 30min de coleta para confirmar.

### B-23 — ghost_signals.jsonl — log persistente de sinais bloqueados no último gate
**Status:** Backlog · aguarda volume para justificar implementação  
**Origem:** Observação do Doreto · 04/06/2026

O Ghost Audit no dashboard mostra apenas 3-5 entradas em janela visual — quando o símbolo sai da janela o dado se perde. Para cruzamento analítico real precisa de log persistente.

**O que gravar:** cada sinal bloqueado no último gate com campos completos — símbolo, timestamp, `reason_code`, score, DNA completo (trades_1m, cvd_change_pct, ema_trend, rsi_1h, ob_imbalance, lsr_trend, oi_trend).

**Para que serve quando implementado:** cruzar símbolos bloqueados com Post-Trade Impact — se o símbolo foi bloqueado e depois subiu muito, o gate está sendo excessivamente restritivo. Se foi bloqueado e caiu, o gate funcionou. Com volume suficiente isso vira calibração de thresholds com evidência real.

**Próximo passo:** quando B-22 (volume de refusals) for confirmado e tivermos 30+ trades, Brain avalia se `ghost_signals.jsonl` tem prioridade suficiente para virar task. Forge implementa em `signal_engine.py` — gravar no mesmo formato do `paper_closed.jsonl`.

### B-26 — Encryptos Smart Money Hunter — indicador proprietário de Doreto
**Status:** Exploração · informação do Melo recebida · 09/06/2026  
**Origem:** Prints do TradingView de Doreto · 04/06/2026

Indicador proprietário **Encryptos Smart Money Hunter v3.5** usado por Doreto há muito tempo. Criado pela Encryptos (mesmo ecossistema do eAssets). Três componentes principais:

**EXP (Encryptos Exponential):** força do ativo em múltiplos TFs (D, 4h, 1h, 30m, 15m, 5m, 1m). Escala ~0-200.

**RSI:** versão própria por TF. Confirmação de momentum.

**SML/ELV (Encryptos Smart Money Level):** o mais interessante. Mede acumulação institucional por TF.

**✅ Resposta direta do Melo (criador) — 09/06/2026:**

O ELV é uma **aproximação** de `trades_per_minute` construída com preço + volume + volatilidade porque o TradingView não dá acesso a dados de trades da Binance. O Melo tentou replicar a detecção de HFT/smart money sem ter os dados reais de trades.

> "No TradingView não tem trades por minuto ou qualquer outro indicador que puxe estes dados da Binance. Então eu criei isso aí usando volatilidade, usando volume e usando mudança de preço. É como se fosse tentando identificar que é a hora que eles ligam também os robôs HFTs, mas sem ter como acessar os mesmos dados."

**Conclusão crítica para o projeto:** o SS tem **vantagem estrutural** sobre o ELV — usa dados reais de `trades_1m` da API da Binance, que é exatamente o dado que o Melo tenta aproximar com volatilidade/volume. O SS não precisa replicar o ELV — já tem o dado original.

**Conexão com B-19/EA-05:** o Melo chegou ao mesmo problema que identificamos — distinguir spike de pressão sustentada. Ele usa volatilidade como proxy. O SS usa `trades_second` multi-TF (quando implementado). Caminhos diferentes para o mesmo objetivo.

**Próximo passo:** nenhum para implementação imediata. O SS já supera o ELV nos dados de atividade. Revisar quando B-19 (trades_second multi-TF) entrar em Sprint.

--- (Sniper reativo → preditivo)
**Status:** Visão estratégica · Sprint 4-5  
**Origem:** Análise de VELVETUSDT +40% em 2 dias · 04/06/2026

O Sniper hoje é reativo — entra quando o squeeze já começou. VELVETUSDT mostrou 3 fases distintas num movimento de +40%:

- **Fase 1 (acumulação silenciosa):** OI subindo gradualmente, LSR caindo, CVD positivo moderado, trades_1m ainda baixo. O Sniper provavelmente bloqueou aqui por gates de atividade.
- **Fase 2 (explosão):** trades_1m alto, liquidações visíveis, CVD forte — janela ideal de entrada do Sniper.
- **Fase 3 (exaustão):** CVD virou negativo com preço ainda subindo — divergência clássica, movimento puxado por liquidações de shorts, não compradores novos. Confirmação do B-21.

**O que precisamos:** detectar a Fase 1 antes da explosão. O `multitf_confluence.py` do King Kong faz exatamente isso — acumulação em múltiplos TF antes do movimento. Está no backlog como B-01 com o módulo já disponível.

**Indicadores usados por Doreto no Coinglass para esta análise:**
OI (candles), LSR (accounts), CVD agregado futures, Funding Rate (OI weighted), Liquidações agregadas (long). Todos em 5m TradingView.

**Pré-requisito:** validar o sistema reativo atual com 30+ trades antes de adicionar complexidade preditiva.

--- — impacto nas métricas
**Status:** Hipótese · risco parcialmente mitigado pelo reload automático  
**Origem:** Observação do Doreto · 04/06/2026

A Binance Futures reseta o candle diário às 00:00 UTC = 21:00 BRT. Nesse momento: volume diário zera, candle diário fecha e abre novo, RSI recalcula, CVD acumulado do dia muda de base, funding rate acumula e zera.

**Mitigação já existente:** o bot faz reload automático às 21:00 BRT com 300s de warmup — durante esse período os buffers se repopulam e os gates ficam conservadores. Isso é proteção real.

**Risco residual identificado:**
- Relatório diário roda às 20:50 BRT — captura métricas do candle prestes a fechar. Estado pode ser enganoso (RSI, volume, CVD no pico do dia).
- Se houver trade aberto no momento da virada, ele atravessa com dados de candle que acabou de fechar.
- Primeiros trades após os 300s de warmup entram com candle novo que tem pouquíssima história — RSI, CVD e volume diário ainda em formação.

**Próximo passo:** verificar se algum trade da coleta oficial foi aberto nos primeiros 5-10 minutos após os 300s de warmup das 21:00. Se sim, checar se o resultado foi pior que a média. Com 20+ trades e uma virada registrada, teremos dado concreto.

---

### B-27 — Engenharia de prompt avançada para context.md e Analista Externo
**Status:** Referência futura · baixa prioridade  
**Origem:** Observação do Doreto · 04/06/2026

Framework de prompt estruturado com tags role/context/examples/instructions/formatting. O que já temos implementado: role (Brain/Forge), context (context.md), instructions (protocolo Brain×Forge). O que falta: examples — casos reais de análises bem feitas para calibrar futuras sessões, especialmente útil para o Analista Externo.

Revisar se qualidade das análises cair ou contexto começar a se perder entre sessões. Por enquanto overhead desnecessário.

---

### B-29 — BTC Reset Monitor — integração no SS
**Status:** Backlog · Sprint 3-4 · código pronto e testado  
**Origem:** Indicador proprietário Doreto · entregue pelo Analista Externo · 05/06/2026

Mede desalavancagem do BTC em múltiplos TFs simultaneamente. Teoria da Tempestade e Bonança — mercado cripto precisa de "limpeza" antes de novos movimentos sustentados. Detecta dois padrões: RESET CLÁSSICO (RSI < threshold por tempo mínimo) e V RELÂMPAGO (queda + recuperação rápida = sinal de entrada explosivo).

**Código:** `src/indicators/btc_reset.py` — pronto para copiar para o projeto SS. Testes passando.

**Dados já disponíveis no SS:** `rsi:5m`, `rsi:15m`, `rsi:1h` no MetricStore — integração mínima funcional já no Sprint 3. O 4h depende de EA-02 (Sprint 4). 12h e 1D requerem novo TF.

**Impacto operacional direto:** função `get_post_reset_candidates()` filtra ativos com EXP_BTC positivo durante queda + OI voltando + LSR caindo — candidatos ideais para squeeze pós-reset. Conecta diretamente com B-01 e B-25.

**Parâmetros configuráveis:** `rsi_threshold=30` e `liq_threshold=10M USD` vão para `preferences.json`. Calibrar após análise de histórico mensal.

**Ordem de integração sugerida:**
- Sprint 3: integração mínima com 3 TFs disponíveis + exposição no dashboard
- Sprint 4: adicionar 4h quando EA-02 estiver pronto + ring buffer para detecção V
- Sprint 5: adicionar 12h e 1D

---

### B-30 — CRM — Crypto Risk Meter — integração no SS
**Status:** Backlog · Sprint 3-4 · código pronto e testado  
**Origem:** Indicador proprietário Doreto · entregue pelo Analista Externo · 05/06/2026

Mede risco do ambiente cripto em tempo real. Score 0-100 com lógica FGI invertida intencionalmente — medo extremo = oportunidade para o operador que opera contra a manada. Ganância extrema = mercado alavancado = risco real.

**Código:** `src/indicators/crm.py` — pronto. Testes passando.

**Dados já no SS (32% do peso):** `btc_change_24h` via MetricStore + `funding_rate_avg` calculado dos ativos ativos. CRM já funciona com dados parciais desde o primeiro dia.

**Dados externos (68% do peso):** USDT.D e ETH.D via CoinGecko `/api/v3/global`, Fear & Greed via `api.alternative.me/fng`. Fetch automático implementado em `fetch_crm_data()`.

**Integração mínima Sprint 3:** usar só `btc_change_24h` e `funding_rate_avg` — score parcial mas imediato, sem novas requisições.

**Integração completa Sprint 4:** task asyncio a cada 5 minutos buscando os dados externos.

**Uso operacional futuro:** gate de contexto no signal_engine quando Brain validar correlação com performance — não bloquear sinais agora, só expor no dashboard e no signal dict.

---

### B-31 — GRM — Global Risk Meter — integração no SS
**Status:** Backlog · Sprint 4-5 · código pronto e testado  
**Origem:** Indicador proprietário Doreto · entregue pelo Analista Externo · 05/06/2026

Mede apetite de risco dos mercados financeiros globais. VIX (35%), DXY (25%), S&P500 (20%), Gold (12%), Nasdaq (8%). Lógica especial: Gold subindo + S&P caindo simultaneamente = bônus de fuga dupla para segurança.

**Código:** `src/indicators/grm.py` — pronto. Testes passando. Todos os dados via Yahoo Finance sem autenticação — instabilidade possível, código já trata com None nos campos que falharem.

**Valor hoje:** puramente visual no dashboard para contexto macro. Zero sobreposição com dados existentes no SS.

**Valor operacional futuro:** quando tivermos evidência de correlação entre GRM alto e performance do SS — requer meses de dados. Por enquanto informativo.

**Integração sugerida Sprint 4-5:** task asyncio a cada 5 minutos com `fetch_grm_data()`. Expor no dashboard junto com CRM.

**Nota sobre Yahoo Finance:** se instável, alternativa é `yfinance` library ou Stooq API — o módulo retorna None nos campos que falharem sem quebrar o sistema.

---

### B-32 — Dashboard manual eAssets (doreto-squeeze-sniper.html)
**Status:** Backlog · referência e evolução futura  
**Origem:** Analista Externo + Doreto · 05/06/2026

Dashboard HTML standalone para análise manual de oportunidades a partir do JSON exportado do eAssets. Integra CRM, GRM e BTC Reset Monitor visualmente. DNA Score (0-100) aplicando critérios do SS sobre dados do Eassets. Abre CoinGlass automaticamente ao clicar no ativo.

Inclui penalidades automáticas alinhadas com EA-01 (EMA:1h ≤ -4 = -20 pontos) e EA-03 (range confluência multi-TF no score).

**Uso atual:** ferramenta de análise manual paralela ao SS automatizado. O Analista Externo usa para preparar briefings com evidência antes de trazer para o Brain.

**Evolução futura:** quando API do eAssets estiver disponível, integração automática com o dashboard do SS elimina necessidade de exportação manual do JSON.

--- (20:50–21:05 BRT)
**Status:** Backlog · prioridade média · vira task F-10 quando Forge disponível  
**Origem:** Reflexão do Doreto · 05/06/2026

**Problema identificado:** três pontos fracos na virada das 21:00 BRT:
- Relatório diário das 20:50 captura candle ainda aberto — dados incompletos
- Janela 20:50–21:05 é a mais volátil do dia — funding reset, liquidações em cascata, spikes bidirecionais
- Warmup de 300s após reload acontece exatamente nesse período de alta volatilidade

**Proposta Brain:**

1. **Janela de silêncio 20:50–21:05 BRT** — nenhum trade novo abre nesse período. Bot continua monitorando e coletando dados mas não dispara entradas. Implementação simples em `signal_engine.py` ou `main.py`.

2. **Relatório diário movido para 21:01 BRT** — captura o candle completo recém-fechado. Dados reais do dia inteiro.

3. **Warmup de 300s encadeado** — se termina dentro da janela de silêncio, bot só volta a disparar quando ambos estiverem concluídos. Sem lógica extra necessária.

**O que NÃO implementar agora:** realização automática de 50% dos lucros na virada — lógica nova sem evidência de que trades abertos nesse momento têm desempenho pior. Estudar depois com dados.

**Trades abertos na virada:** não interferir — trailing stop e mae_guard já protegem. Só bloquear novas entradas.

**Arquivos suspeitos:** `main.py` (scheduler do relatório e reload), `signal_engine.py` (gate de horário).

---

### B-33 — Checklist de migração Paper → Live
**Status:** Documento vivo · alimentar a cada nova implementação  
**Origem:** Brain · 06/06/2026

Este item nunca fecha — é atualizado a cada sprint com novos requisitos de validação antes de ligar o Live com capital real.

---

**CRITÉRIOS DE PERFORMANCE (Paper)**

- [ ] WR ≥ 45% sustentado por 50+ trades com os gates atuais ativos
- [ ] Profit Factor > 1.2 nos últimos 50 trades
- [ ] DrawdownManager nunca acionado em sessão completa
- [ ] Média de squeeze_failed < 40% dos trades totais
- [ ] Nenhum MAE > 15% nos últimos 20 trades

---

**PARIDADE DE CÓDIGO Paper → Live**

Campos e gates novos que precisam ser verificados no `live_tracker.py` antes do Live:

- [ ] Gate combo (`trades_1m >= 10 AND oi_trend >= 0.008 AND lsr_trend <= -0.3`) — Sprint 3 · commit d4b01b0 — verificar se `live_tracker.py` aplica ou herda do `signal_engine.py`
- [ ] `volume_quality` no signal dict — Sprint 3 · commit 3f8b6c1 — campo calculado no `signal_engine.py` (compartilhado)
- [ ] `exp_btc_norm_1h` no signal dict — Sprint 3 · commit 8b81a81 — `metric_engine.py` (compartilhado)
- [ ] EA-07 gate `exp_btc_norm_1h` — ⚠️ SUSPENSA · buffer 140s produz correlação invertida (losers norm=1.564 > winners norm=1.071) · aguarda implementação com klines reais 1h · Sprint 4
- [ ] `min_trades_1m = 10` — Sprint 3 · commit d5da930 — verificar se `preferences.json` tem seção `live.signal.min_trades_1m` separada
- [ ] `ghost_signals.jsonl` — Sprint 3 · commit b02700f — exclusivo Paper ou também no Live?
- [ ] `CALIBRATION_MARGIN_CAP` — no Live não existe esse cap — sizing real vai ser diferente. Decisão de risco por trade precisa ser tomada conscientemente antes de ligar

---

**INFRAESTRUTURA LIVE**

- [ ] Chaves API Binance Live configuradas no `.env` (separadas das chaves de teste)
- [ ] Bracket tiers Binance verificados para os símbolos do universo (F-03 já implementado)
- [ ] VPS ou máquina dedicada 24h (B-09) — não depender de laptop pessoal
- [ ] Monitoramento de uptime configurado
- [ ] Telegram alertas Live funcionando (testado em Paper — verificar Live)

---

**DECISÕES DE RISCO ANTES DO LIVE**

- [ ] Capital inicial definido (não usar capital que não pode perder)
- [ ] Risco por trade definido (hoje 5% no Paper — manter ou reduzir no início do Live?)
- [ ] Max posições simultâneas definido (hoje 20 no Paper — reduzir no início?)
- [ ] Stop de drawdown diário definido (ex: se perder 3% do capital em 1 dia, parar)
- [ ] Protocolo de emergência documentado (como parar tudo se algo der errado)

---

**INDICADORES PROPRIETÁRIOS (quando implementados)**

- [ ] BTC Reset Monitor (B-29) — integrado e calibrado antes do Live
- [ ] CRM mínimo (B-30) — integrado e exposto no dashboard Live
- [ ] Janela de silêncio 21:00 BRT (B-28/F-10) — ativa no Live também

---

_Este checklist é alimentado a cada sprint. Nenhum item pode ser pulado._  
_Última atualização: 06/06/2026 · Sprint 3 EA_

---

---

### B-34 — LSR bypass quando OI forte + liquidações confirmadas
**Status:** Hipótese · aguarda evidência nos refusals  
**Origem:** Documentos externos filtrados pelo Brain · 06/06/2026

Em squeezes violentos de altcoins, o LSR pode ter repique técnico positivo no exato momento da ignição antes de desabar — causando bloqueio indevido pelo gate `lsr_trend_positive`. A hipótese é que se `oi_change_pct:5m > 25%` AND `liq_short_1m > 0`, o LSR positivo poderia ser ignorado porque o fluxo institucional confirma o squeeze independente do ruído do LSR.

**Status atualizado 09/06/2026:** F-12 resolvido — `liq_short_1m` chegando com valores reais pela primeira vez. B-34 agora é testável. Nas próximas sessões Brain filtra refusals de `lsr_trend_positive` onde `oi_change_pct > 25%` E `liq_short_1m > 0`. ARIA cruza com Eassets para ver se esses ativos tinham estado macro favorável.

**Próximo passo:** análise dos próximos 15 trades com `liq_short_1m` real.

---

### B-35 — Penalização anti-FOMO no score (price_change:5m > 3.5%)
**Status:** Hipótese · verificar se `exaustao_15m` já cobre  
**Origem:** Documentos externos filtrados pelo Brain · 06/06/2026

Penalizar ativos que já subiram muito nos últimos 5 minutos para evitar comprar o topo do squeeze. Se `price_change:5m > 3.5%`, subtrair pontos do score final.

O gate `exaustao_15m` já existe no sistema e pode estar cobrindo esse cenário. Antes de implementar algo novo, verificar com o Forge como `exaustao_15m` está implementado e qual é o threshold atual.

**Próximo passo:** Forge confirma lógica atual do `exaustao_15m`. Brain avalia se precisa de ajuste com dados dos próximos trades.

---

## REGRAS DE PROCESSO — Brain × Forge × ARIA

### R-01 — Forge commita context.md a cada sprint concluído
**Status:** Regra permanente · ativa desde 06/06/2026

A cada sprint concluído ou conjunto de commits relevantes, o Forge commita `context.md` atualizado nos dois repos (`vjdoreto/squeeze-sniper` privado e `vjdoreto/squeeze-sniper-brain` público) antes de encerrar a sessão.

O `context.md` deve refletir:
- Estado atual de todos os fixes ativos com commit hash
- Tasks concluídas e pendentes do sprint
- Parâmetros relevantes em produção com valores atuais
- Estado congelado de qualquer parâmetro aguardando validação
- Próximo passo definido pelo Brain

**Por quê:** é a cola que mantém Brain × Forge sincronizados entre sessões. O Brain lê o `context.md` no boot de cada nova conversa — se estiver desatualizado o Brain começa com contexto errado.

---

### R-02 — Fluxo Brain × ARIA × Forge
**Status:** Regra permanente · ativa desde 05/06/2026

Ideia ou observação → Brain primeiro (filtra com dados)
Brain valida → ARIA pode contribuir com visão externa (Eassets)
Brain + ARIA alinham → task vai para o Forge com evidência
Forge implementa → Brain documenta → ARIA monitora nos próximos logs

ARIA não passa tasks diretamente ao Forge. Todo alinhamento passa pelo Brain primeiro.

---

_Revisão periódica: sempre que Brain e Doreto se reunirem com novidades._  
_Versão atual: 3.0 · 08/06/2026_

---

### B-36 — EA-07 SUSPENSA — exp_btc_norm_1h com klines reais 1h
**Status:** Suspensa · Sprint 4  
**Origem:** Análise 33 trades + ARIA · 08/06/2026

O gate EA-07 baseado em `exp_btc_norm_1h < threshold` foi suspenso porque o campo atual usa buffer de polling (~140s) e apresenta correlação INVERTIDA — losers têm norm médio maior (1.564) que winners (1.071). EDENUSDT ganhou +9.14% com norm=-2.176. Ativar o gate com a implementação atual pioraria o WR.

Reativar apenas quando `exp_btc_norm_1h` for recalculado usando klines reais de 1h do SymbolStore. Quando implementado corretamente, threshold sugerido pela ARIA: -1.5 (baseado no range real -2.87 a +3.37 dos ghosts).

---

### B-37 — EA-09 gate volume_quality < 2.0
**Status:** Evidência confirmada · vira task F-15 · Sprint 3  
**Origem:** ARIA análise 33 trades · 08/06/2026

Winners média vq=0.535, losers média vq=1.502 (3x maior). Gate `vq >= 2.0` bloquearia 3 trades — NILUSDT (4.67), STGUSDT (16.20), MEGAUSDT (6.61) — todos losers, zero winners perdidos. Já escalado como F-15 para o Forge.

Threshold 2.0 a validar com próximos trades. ARIA monitorando se algum winner é bloqueado.

---

### B-38 — MTF — contexto 1h como modificador de gates de 5m
**Status:** Projeto estrutural · Sprint 5+  
**Origem:** ARIA análise ALLOUSDT 1.009 near-misses · 08/06/2026

O SS toma decisões em janelas de 5m sem contexto de 1h/4h. ALLOUSDT teve 1.009 near-misses bloqueados por CVD negativo em janelas de 5m enquanto o Eassets via EXP_BTC:1h=+108 e EMA:4h=6/6. O ativo subiu durante o fim de semana.

A limitação é arquitetural — não tem solução incremental simples. A fusão correta é usar o contexto do Eassets (ou do MetricStore de 1h quando EA-02 estiver pronto) como modificador dos thresholds de gate de 5m. Se EXP_BTC:1h > +30 e EMA:4h = +6, gates de CVD e LSR podem ser mais permissivos porque o contexto macro confirma o movimento.

Pré-requisito: EA-02 (ema_trend:4h) implementado e validado. Sprint 5+.


### B-39 — liq_threshold proporcional ao OI — implementado F-16
**Status:** ✅ Implementado Sprint 3 · commit 9477fd8 · 08/06/2026  
**Origem:** Observação do Doreto + ARIA · confirmada com 42 trades

O threshold fixo de $500K era calibrado para BTC e matematicamente impossível em altcoins de $3-5M de OI. Em 42 trades acumulados, `liq_cascade = True` apareceu zero vezes. Agora usa `max(oi_usd * 0.02, 10_000)` — escala automaticamente com o ativo. BBUSDT OI $4M → threshold $80K.

Teste de confirmação: `liq_cascade = True` deve aparecer nos próximos trades de altcoins. ARIA monitora.

**Atualizar B-33 (checklist Live):** verificar paridade paper + live para F-16.

---

### B-40 — ema_trend:4h gate combinado — implementado F-18
**Status:** ✅ Implementado Sprint 3 · commit adaed4f · 08/06/2026  
**Origem:** ARIA + Brain · evidência de 3 sessões consecutivas

Gate `ema_4h <= -4 AND exp_btc_norm_1h < -1.5` ativo no signal_engine. klines 4h no boot + stream `kline_4h` no WebSocket (chunk 60→48 para caber no limite de 200 streams da Binance).

Evidência acumulada: BANANAS31 ganhou +17% com EMA:4h=0. BBUSDT perdeu -15.92% com EMA:4h=-6. Padrão confirmado em 3 sessões. EMA:4h=-6 presente na maioria dos losers.

Teste de confirmação: `ema_4h_bearish` deve aparecer nos refusals nos primeiros minutos após restart.

**Atualizar B-33 (checklist Live):** verificar paridade paper + live para F-18.

---

### B-41 — Documento DNA do Sniper — guardião Forge
**Status:** Pendente · Forge deve criar e manter  
**Origem:** Doreto · 08/06/2026

O Forge deve criar e commitar no repo privado `vjdoreto/squeeze-sniper` um documento `SQUEEZE_SNIPER_DNA.md` que contenha:
- DNA completo com hierarquia de decisão e pilares
- Motor de score `calculate_fit_score()` documentado com pesos e thresholds atuais
- Campos do signal dict com descrição e escala
- Gates ativos com reason_codes e thresholds
- Histórico de mutações do DNA com data e evidência

O Forge é guardião exclusivo deste documento — atualiza a cada sprint quando o DNA sofrer mutação. O Brain consulta mas não edita. Doreto autoriza mutações.

---

### B-42 — F-12 RESOLVIDO — causa raiz: socket no endpoint errado
**Status:** ✅ Resolvido · 09/06/2026  
**Origem:** 42 trades com liq_short_1m = 0 · diagnóstico completo

Causa raiz real: o WebSocket `!forceOrder@arr` conectava no endpoint errado desde o início. Todos os fixes anteriores de cálculo (`ap*z`, threshold proporcional) estavam corretos mas nunca chegavam dados porque o stream não conectava no lugar certo.

Após o fix e restart: `liq_short_1m` vai acumular valores reais pela primeira vez. F-16 (liq_threshold proporcional) terá impacto real. `liq_cascade = True` pode finalmente aparecer num trade.

Confirmar após restart: `DIAG F-12 payload bruto (#1)` nos logs na primeira liquidação real.

---

_Revisão periódica: sempre que Brain e Doreto se reunirem com novidades._
_Versão atual: 3.1 · 08/06/2026_

### B-43 — mover threshold exaustao_15m para preferences.json
**Status:** Backlog · melhoria de governança · baixa prioridade  
**Origem:** Verificação B-35 · 09/06/2026

Gate `exaustao_15m` em `signal_engine.py:643` usa threshold `pc_15m > 3.0` hardcoded. Valor correto e bem calibrado — não mexer agora. Mas mover para `preferences.json` facilita calibração futura sem tocar no código.

**Próximo passo:** quando Sprint 4 iniciar, Forge move `exaustao_15m_pct: 3.0` para preferences.json e lê de lá no signal_engine. Mudança de governança pura, sem impacto em produção.

---

_Revisão periódica: sempre que Brain e Doreto se reunirem com novidades._
_Versão atual: 3.2 · 09/06/2026_

### B-44 — mtf_1h_crash — gate de contexto 1h já existente
**Status:** ✅ threshold movido para preferences.json · commit desta sessão · 09/06/2026  
**Origem:** Descoberta durante verificação de refusals · 09/06/2026

Gate `mtf_1h_crash` em `signal_engine.py:328-330`. Bloqueia entradas quando `exp_1h < mtf_1h_crash_threshold` — ativo caindo no 1h = dead cat bounce = não entrar. Exceção quando `liq_cascade = True`.

`mtf_1h_crash_threshold: -0.05` agora em `preferences.json` (paper + live) e `config.py`. Brain calibra mudando só o JSON.

**B-43 (exaustao_15m)** ainda pendente — mover para Sprint 4.

---

_Revisão periódica: sempre que Brain e Doreto se reunirem com novidades._
_Versão atual: 3.4 · 09/06/2026_

### B-45 — RSI actual_window 15 → 28
**Status:** ✅ Implementado · 09/06/2026  
**Origem:** Anomalia RSI=100 no dashboard · COMPUSDT · 09/06/2026

RSI do SS usava `actual_window = min(15, len(closes))` — janela pequena o suficiente para retornar RSI=100 quando os últimos 15 candles são todos de alta. TradingView usa Wilder smoothing sobre 14 períodos com histórico completo, retornando valores suavizados.

Solução: aumentar `actual_window` de 15 para 28 (2× período). Dilui picos de RSI espúrios, aproxima comportamento do TradingView sem reescrever o cálculo completo. RSI menos reativo a movimentos curtos — reduz falsos positivos de RSI alto em spikes de 5m.

Opção descartada: Wilder smoothing completo (SMMA) — mais fiel mas desnecessário agora.

---

_Revisão periódica: sempre que Brain e Doreto se reunirem com novidades._
_Versão atual: 3.8 · 09/06/2026_

### B-46 — EA-02: ema_trend:4h via klines reais — pré-requisito crítico Sprint 4
**Status:** Sprint 4 · primeiro item · desbloqueia B-36, B-38, B-40  
**Origem:** ARIA · evidência acumulada 3 sessões · 09/06/2026

Pré-requisito crítico para múltiplos itens. O `ema_trend:4h` atual (B-40) usa buffer de polling — deve migrar para klines reais quando EA-02 for implementado.

Evidência de 3 sessões: winners EMA:4h médio=-2.0, losers=-5.0. BANANAS31 (+17%) EMA:4h=0. BBUSDT (-15.92%) EMA:4h=-6. WAXPUSDT (-16.93%) EMA:4h=-6 em todos TFs.

WebSocket `kline_4h` já implementado (B-40). Forge adiciona cálculo `ema_trend:4h` no MetricStore usando klines 4h do SymbolStore. Verificar se klines 4h já estão parcialmente disponíveis antes de especificar.

**Desbloqueia:** B-36 (EA-07 exp_btc_norm real), B-38 (MTF modificador), B-40 (gate ema_4h_bearish com dados reais).

---

### B-47 — Seleção dos 100 ativos prioritários — gap vs Eassets
**Status:** Hipótese · Sprint 4 · validar antes de implementar  
**Origem:** ARIA · ALLOUSDT/ROBOUSDT/MOVEUSDT nos ghosts · 09/06/2026

O SS seleciona ~100 ativos prioritários. O Eassets cobre 530+. Hipótese: o critério de seleção pode estar excluindo sistematicamente ativos em fase de acumulação — exatamente os que o Eassets identifica antes da explosão.

ALLOUSDT bloqueado 1.009 vezes — estava nos 100? ROBOUSDT EMA 6/6/6 com 20 near-misses — estava no universo? MOVEUSDT EXP_BTC:1h=+40.0 com 154 ghosts — monitorado?

**Como validar:** Brain pede ao Forge a lista atual dos 100 prioritários e critério de seleção. ARIA cruza com JSON do Eassets (530+) e identifica ativos DNA score >= 70 fora dos 100. Se gap significativo, revisar critério.

**Próximo passo:** Brain solicita lista dos 100 ao Forge nesta sessão.

---
