# Backlog Estratégico — Brain × Doreto
_Documento vivo · atualizado conforme novas ideias chegam_
_Criado: 04/06/2026 · Versão: 1.0_

> Este documento é nosso — Brain e Doreto. Não é fila do Forge. É onde guardamos ideias, hipóteses e visões antes de decidir se viram task, se precisam de mais dados, ou se descartamos. Revisamos periodicamente: incluímos, alteramos, removemos.

---

## LÓGICA DO BOT / ESTRATÉGIA

### B-49 — Janela cega pós-reset 21h BRT (25 min descobertos)
**Status:** Tese com evidência inicial · aguarda coleta de trades para confirmar padrão  
**Origem:** Observação Doreto + análise Brain · 11/06/2026

**Problema observado:** O `reset_daily_history()` às 21:00 BRT (00:00 UTC) zera o ring buffer `_history` de todos os 527 símbolos. Os slopes derivados — `exp:5m`, `oi_trend:5m`, `lsr_trend:5m`, `cvd_change_pct:5m` — levam ~30 minutos para reconstruir com novos candles. O gate `silence_window_2100` cobre apenas 20:50–21:05 BRT (15 min). Resultado: há uma **janela descoberta de ~25 minutos** (21:05–21:30 BRT) onde o bot opera com slopes incompletos — podendo perder squeezes reais ou entrar com dados corrompidos.

**Evidência inicial (11/06/2026):** SOPHUSDT subiu ~10% na janela 21:00–21:30 BRT. Bot não capturou. Doreto confirmou que o `price_change_24h` retornou ao normal apenas ~30 minutos após a virada — consistent com o tempo de reconstrução do buffer.

**Por que a janela é especialmente crítica:** 00:00 UTC é horário de funding rate da Binance (ciclo 8h). Shorts com FR positivo pagam para manter posição — pressão de fechamento aumenta exatamente nessa janela. O SS está parcialmente cego no momento de maior probabilidade de squeeze do dia.

**Opções de fix (para avaliar quando tivermos mais dados):**

- **Opção A — Fix imediato:** ampliar `silence_window_2100` de 21:05 para 21:30 BRT em `signal_engine.py`. Simples, cirúrgico. Custo: perde 25 minutos de janela operacional por dia. Não resolve o custo — só protege contra entrada ruim. SOPH-type ainda seria perdido.

- **Opção B — Fix estrutural:** usar `price_at_reset` (já salvo em `reset_daily_history`) como baseline do novo dia em vez de zerar os slopes. Transição suave — slopes continuam válidos imediatamente após a virada. Zero janela perdida. Alinhado com o comportamento do eAssets (que já faz transição suave). Mais complexo — Forge precisa investigar `metric_engine.py`.

**Critério para virar task:** identificar 3+ casos (trades perdidos ou entradas com dados corrompidos) na janela 21:00–21:30 BRT nos próximos logs. Um caso não é padrão. Três casos são evidência.

**Próximo passo:** ao analisar o próximo lote de trades, Brain filtra `entry.timestamp` entre 21:00–21:30 BRT e cruza com `exp:5m` / `oi_trend:5m` no momento da entrada. Se esses campos estiverem baixos enquanto o ativo estava em movimento real → confirma tese → escala para tasks.md com Opção A+B.

---

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
**Status:** ⚡ Caminho simplificado · revisão 11/06/2026  
**Origem:** Doreto + visão macro de fluxo de capital

BTC.D e USDT.D mostram para onde o capital está indo — dolarização vs rotação para altcoins. OTHERS.D mostra força das small caps.

**Atualização 11/06/2026:** o eAssets dashboard já consome BTC.D, USDT.D, ETH.D como componentes do CRM — sem CoinMarketCap. A lógica está em `calcCRM()` no `doreto-squeeze-sniper.html`. Se quisermos esses dados no SS dashboard, vêm junto com a portagem de B-05, não separado.

**CoinMarketCap não é mais necessário para este item.**

**Próximo passo:** entra junto com B-05 quando decidirmos adicionar bloco macro ao SS dashboard.

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

### B-05 — GRM/CRM no dashboard SS
**Status:** ⚡ Caminho simplificado · revisão 11/06/2026  
**Origem:** Doreto tem código de outro projeto (King Kong) com parte disso implementado

**Atualização 11/06/2026:** o `doreto-squeeze-sniper.html` (eAssets) já tem CRM e GRM **implementados e funcionando** sem CoinMarketCap e sem Yahoo Finance. As funções `calcCRM()` e `calcGRM()` são JavaScript puro calculado a partir dos dados do próprio painel.

- **CRM:** USDT.D variação + BTC.D variação + ETH.D variação + Fear & Greed + BTC 24h change + funding rate médio
- **GRM:** VIX nível/variação + DXY nível/variação + S&P500 + Nasdaq + Gold

**`cmc_client.py` do King Kong não é mais o caminho.** Se quisermos trazer CRM/GRM para o dashboard do SS, o Forge porta `calcCRM()` e `calcGRM()` do eAssets — funções testadas em uso real, sem novas dependências.

**Próximo passo:** quando quiser adicionar ao SS dashboard, Brain passa o trecho relevante do eAssets HTML ao Forge. Trabalho de horas, não de sprint.

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

### B-16 — Session Window Filter: horários de alta/baixa probabilidade × CRM/GRM
**Status:** Hipótese Brain · documentada 11/06/2026 · aguarda cruzamento com 50+ trades  
**Origem:** Observação empírica de Doreto + análise Brain sobre estrutura de mercado 24/7

#### A tese central
O mercado de futuros Binance USDM é global mas os participantes têm fusos. A distribuição de liquidações reais (`liq_short_1m > 0`) não é uniforme ao longo do dia — ela concentra nos horários em que os grandes players estão ativos e alavancados. O SS hoje opera com o mesmo threshold 24/7 sem nenhum ajuste de contexto temporal.

#### Janelas identificadas por Doreto (observação empírica validada)

**Alta probabilidade — squeezes reais com liq_short_1m > 0:**

| Janela | BRT | UTC | Por quê |
|--------|-----|-----|---------|
| Abertura asiática | 01h–04h | 04h–07h | China/Japão/Coreia ativos, fluxo institucional asiático em altcoins |
| Abertura americana | 10h–13h | 13h–16h | NYSE abre, correlação macro sobe, desalavancagem forçada |
| Noite americana | 20h–23h | 23h–02h | Maior volume do dia, overlapping EUA + Ásia início |
| Virada diária (21h BRT) | 21h | 00h | Candle diário fecha + funding rate cobrado — rebalanceamento institucional |
| Domingo 21h BRT | 21h dom | 00h seg | Candle SEMANAL fecha + abertura iminente Ásia segunda |
| 1h BRT | 01h | 04h | Confirmação fluxo asiático — Doreto observou squeezes recorrentes |

**Baixa probabilidade — regime liq_short_1m ≈ 0 (confirmado hoje 17h BRT):**

| Janela | BRT | UTC | Por quê |
|--------|-----|-----|---------|
| Tarde BRT | 15h–19h | 18h–22h | Transição EUA dormindo/acordando — volume raso |
| Madrugada BRT | 04h–08h | 07h–11h | Ásia encerrando, EUA ainda dormindo |
| Fim de semana manhã | 08h–14h sáb/dom | 11h–17h | Sem fluxo institucional, só varejo |

**Padrão de fim de semana (observação Doreto):**

- **Sexta à noite:** traders fecham posições antes do fim de semana → liquidações mas em direções imprevisíveis (noise alto)
- **Sábado final de tarde (17h–20h BRT):** varejo americano acorda no sábado, abre plataforma → volume de varejo sobe em mercado com liquidez institucional reduzida → movimentos amplificados
- **Domingo final de tarde + 21h BRT:** mesmo padrão + antecipação do fechamento semanal

#### Por que isso importa para o SS

Hoje (11/06, 17h BRT) o diagnóstico foi exato: score máximo 78, liq_short_1m = 0, zero signals desde restart às 16:55h. Isso não é bug — é o regime de baixa probabilidade da tarde. O SS está correto em não entrar. A questão é se devemos tornar isso explícito no DNA.

#### Integração estratégica com CRM e GRM

O dashboard eAssets (`doreto-squeeze-sniper.html`) já tem CRM e GRM **implementados e funcionando** — sem Yahoo Finance, sem CoinMarketCap, calculados a partir dos dados do próprio painel:

**CRM (Crypto Risk Meter)** — mede risco interno cripto:
- `USDT.D variação` (peso alto — fuga para stablecoins = medo)
- `BTC.D variação` (alta no BTC.D drena altcoins)
- `ETH.D variação` (alts sangrando vs altseason)
- `Fear & Greed Index`
- `BTC 24h change`
- `Funding rate médio` (positivo alto = euforia = risco)

**GRM (Global Risk Meter)** — mede risco macro global:
- `VIX` (nível + variação)
- `DXY` (nível + variação — dólar forte = saída de risco)
- `S&P 500 variação`
- `Nasdaq variação`
- `Gold variação`

O CRM já influencia o score de entrada no dashboard: `crmVal >= 76 → -10 pts` e `crmVal >= 56 → -5 pts`. Mas isso é só no dashboard — o SS não consulta CRM nem GRM na hora de decidir entrar.

#### Hipótese de integração (a validar com dados)

Combinação Session Window + CRM/GRM poderia criar um contexto de 3 camadas para o SS:

```
VERDE (janela boa + CRM baixo + GRM baixo):
  → min_score atual, D3 padrão, todos os gates normais

AMARELO (janela ruim OU CRM/GRM elevado):
  → exigir liq_cascade = True obrigatório (sem bypass D3)
  → ou min_score + 3 pts temporariamente

VERMELHO (janela ruim + CRM crítico + GRM alto):
  → standby automático, não entra independente do score
```

Isso explicaria e formalizaria o que já está acontecendo empiricamente: o SS é mais eficiente nas janelas corretas. Em vez de o Doreto ter que parar o bot manualmente, o DNA reconhece o regime.

#### Pré-requisito para implementar

**Não implementar agora.** Precisamos de:
1. 50+ trades com timestamp para mapear horário × WR × liq_short_1m
2. Cruzamento: trades nas janelas de alta probabilidade têm WR sistematicamente maior?
3. Cruzamento: CRM alto no momento da entrada correlaciona com losers?
4. Se ambos confirmados → Brain propõe gate + Forge implementa com evidência

**Próximo passo:** quando tivermos 50+ trades, ARIA extrai `entry.time` × `exit_reason` × `mfe` × `liq_short_1m` e Brain mapeia a distribuição por horário. Essa análise vai confirmar ou rejeitar a hipótese empírica do Doreto.

---

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
**Status:** ✅ FECHADO — comportamento esperado confirmado pelo Forge · 12/06/2026

**Resposta Forge:** 1 refusal por símbolo por ciclo de avaliação (primeiro gate que falha retorna). Não há inflação por múltiplos gates. Volume alto é real — scanner roda em ~527 símbolos a cada ciclo. Pico inicial é warmup (warmup_metrics_none, rsi_1h_warmup dominam os primeiros minutos). Nada a investigar.

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
**Status:** ⏸️ Pausado · Sprint 6+ · decisão Doreto 10/06/2026 — foco em DNA e coleta de trades primeiro  
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
**Status:** ⏸️ Pausado · Sprint 6+ · decisão Doreto 10/06/2026 — foco em DNA e coleta de trades primeiro  
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

**PARIDADE 12/06/2026 — 10 fixes a verificar em `live_tracker.py` antes do Live**

> Fixes implementados em `paper_tracker.py` / `signal_engine.py` em 12/06. Todos precisam de auditoria de paridade com `live_tracker.py`.

- [ ] **D3 — gate `liq_required_no_cascade`** · `signal_engine.py:688` · `6d9554d` — gate em signal_engine, deve ser compartilhado; verificar se live_tracker herda corretamente
- [ ] **D4 — bônus `ema_trend_1h` removido** · `market_view.py:102` · `6d9554d` — `calculate_fit_score()` é compartilhado; confirmar que live usa mesmo market_view
- [ ] **D6 — gate `overextension_double`** · `signal_engine.py:699` · `6d9554d` — idem D3
- [ ] **D7 — gate `lsr_multiframe_divergence`** · `signal_engine.py:707` · `6d9554d` — idem D3
- [ ] **E1 — bypass `oi_trend_too_weak` para cascade** · `signal_engine.py:787` · `aa5d2ee` — idem D3
- [ ] **E2 — bypass `lsr_trend_not_negative` para cascade** · `signal_engine.py:797` · `aa5d2ee` — idem D3
- [ ] **E3-gate-final — bypass `oi_accel` cascade no gate final** · `signal_engine.py:966` · `4129488` — idem D3
- [ ] **D-URGENTE-1 — SL fill no sl_price target** · `paper_tracker.py` · `7ebc3b8` — ⚠️ CRÍTICO: lógica de saída em `live_tracker.py` pode ter bug idêntico; Forge audita antes do Live
- [ ] **D-HIGH-1 — gate `cvd_negative_cascade_entry`** · `signal_engine.py` · `d256018` — gate compartilhado; verificar
- [ ] **D-HIGH-2 — throttle 4h após stop_loss hit** · `risk_manager.py` + `main.py` · `d2eac09` — `risk_manager.py` é compartilhado; verificar se `extend_cooldown()` é chamado no Live também

---

_Este checklist é alimentado a cada sprint. Nenhum item pode ser pulado._  
_Última atualização: 12/06/2026 · 10 fixes de 12/06 adicionados (Brain · deliberação Brain × Forge)_

---

---

### B-34 — LSR bypass quando OI forte + liquidações confirmadas
**Status:** Logging ativo · commit `6f0bc0a` · aguarda próxima sessão com dados reais de liq_short_1m nos refusals · 10/06/2026  
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
**Status:** ✅ Implementado · commit `6f0bc0a` · 10/06/2026  
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

### B-48 — Scripts de análise automática Brain × ARIA
**Status:** ✅ Implementado · commit `6f0bc0a` · 10/06/2026
**Origem:** Doreto · 09/06/2026 · sessão de migração Brain+ARIA para Antigravity

Hoje a análise dos 4 trades e o cruzamento com o eAssets foram feitos manualmente — Brain leu os logs, ARIA leu o JSON, Forge extraiu os dados. Com volume crescente de trades e sessões diárias, isso não escala.

**Proposta — dois scripts dedicados:**

**Script Brain (`brain/analyze_logs.py`):**
- Lê `logs/paper_closed.jsonl` automaticamente
- Calcula KPIs da sessão: WR, PnL, Profit Factor, MFE médio, MAE médio, captura MFE
- Tabela winners vs losers por campo do signal dict (trades_1m, cvd_change_pct, rsi_5m, ema_trend_4h, volume_quality, cvd_streak)
- Identifica padrões automáticos: squeeze_failed com MFE=0, trades com captura < 30%
- Output: markdown estruturado pronto para o Brain ler e gerar recomendações

**Script ARIA (`aria/eAssets/analyze_eassets.py`):**
- Lê o JSON mais recente de `aria/eAssets/dados_eassets/` automaticamente
- Cruza símbolos do eAssets com trades do dia (`paper_closed.jsonl`)
- Para cada trade: extrai ema_trend:4h, exp_btc:1h, rsi:1h, oi_trend:5m do eAssets
- Identifica divergências: campo do bot vs campo do eAssets (ex: ema_trend_4h=0 bot vs -6 eAssets)
- Tier 1/2: top ativos por EXP_BTC:1h com EMA:4h positivo fora dos trades do dia
- Output: markdown estruturado pronto para ARIA gerar contraponto

**Benefício:** Brain e ARIA rodam os scripts, leem o output e já chegam ao consenso com dados prontos. Forge implementa o que sair do consenso. Ciclo de análise cai de 30min para 5min.

**Próximo passo:** Forge implementa os dois scripts em sequência. Autorizado por Doreto 10/06/2026.

**Adendo B-34-log (ARIA 10/06):** adicionar `liq_short_1m` ao refusal gravado em `signal_engine.py` junto com B-48. Uma linha de código — desbloqueia validação de B-34 na próxima sessão com dados reais.

---

### B-49 — Score teto 83 — thresholds de liq calibrados para large caps
**Status:** ✅ Implementado parcialmente · commit `315f0d6` · 10/06/2026
**Origem:** Consenso Brain × ARIA × Forge · diagnóstico sessão VELVET/BEAT

Com F-12 ativo, eventos de liquidação chegavam ($438–$6090) mas eram descartados por piso de $10k. Score máximo travado em 83, min_score 85 — zero trades por design.

**Fix aplicado:** thresholds score $10k/$50k/$100k → $1k/$5k/$20k. Floor liq_cascade $10k → $1k.

**Validar na próxima sessão:** `liq_short_1m_stable > 0` contribuindo pts ao score. Score máximo atingindo 85+. `liq_cascade = True` aparecendo em pelo menos 1 trade.

---

### B-50 — Bootstrap cego para ativos fora do top 50 volume 24h estático
**Status:** ✅ Implementado · commit `315f0d6` · 10/06/2026
**Origem:** ARIA análise VELVET/BEAT · Brain diagnóstico paradoxo estrutural

VELVET com exp:5m=0 enquanto subia +95% — estava no universo dos 288 mas sem klines no boot. Bootstrap expandido para top 30% por volume usando dados já carregados por _bootstrap_prices(). Sem chamadas REST extras.

**Validar na próxima sessão:** log de boot `Bootstrap klines: top50=50 + volume_recente=X → Y únicos` — confirma expansão. Ativos que "acordam" no dia devem ter exp:5m populado desde o início.

---

### B-51 — RIFUSDT-type: lsr_trend flat com CVD explosivo + FR negativo bloqueado
**Status:** Evidência inicial · backlog · 12/06/2026
**Origem:** Brain · análise ghost signals sessão 12/06

4 ghost signals consecutivos RIFUSDT: score=100, CVD=61.3%, trades=182–194, FR=-0.000496 (shorts pagando), ema_trend=6/máx, ema_trend_4h=2 — bloqueados por `lsr_trend_not_negative` com lsr_trend=-0.051 (threshold exige ≤ -0.3).

**A questão:** lsr_trend=-0.051 é ruído (gate correto) ou acumulação legítima onde shorts não estão fugindo mas também não estão chegando? Com FR negativo, shorts estão pagando para manter — esse é sinal de curto-circuito iminente sem necessariamente ter LSR despencando ainda.

**Por que não virou task agora:** n=4 casos, 1 símbolo, zero trades com esse perfil para saber se o movimento aconteceu. R-02 exige n≥10.

**Critério para virar task:** identificar 10+ ocorrências de lsr_trend entre -0.05 e -0.3 com CVD>30% + FR negativo nos ghost signals. ARIA verifica se esses ativos subiram após o bloqueio. Se WR hipotético >60% → propor ajuste de threshold com evidência.

**Próximo passo:** quando ARIA analisar o próximo lote de ghost_signals.jsonl, filtrar esse perfil e reportar ao Brain.

---

### B-52 — Dois paths de DNA: squeeze clássico vs demand breakout
**Status:** Questão estratégica aberta · 12/06/2026
**Origem:** Brain · análise estrutural do DNA atual

O DNA atual tenta servir dois padrões físicos distintos com bypasses paralelos:

**Squeeze clássico:** LSR despencando agressivamente (≤ -0.3), liq_cascade=True, OI subindo — colapso institucional de longs alavancados. Gates projetados para isso.

**Demand breakout (B-34-type):** CVD explodindo, FR negativo/neutro, LSR flat ou mildamente negativo (-0.05 a -0.3) — entrada de capital comprador progressiva que força fechamento de shorts gradualmente. Não tem a violência do cascade mas tem direção confirmada.

**O problema de ter os dois no mesmo DNA:** cada bypass adicionado para o demand breakout (B-34, lsr_bypass) cria superfície de falso positivo para o squeeze clássico e vice-versa. As regras de evidência se confundem.

**Questão para Doreto:** o SS foi projetado como sniper de cascade. Demand breakout é um padrão diferente com horizonte diferente (minutos vs segundos). Queremos realmente os dois? Ou especializamos o SS clássico e criamos um path B separado só quando o clássico estiver validado com 50+ trades?

**Pré-requisito para decidir:** 50+ trades limpos com DNA atual. Com a amostra, Brain separa trades por perfil de entrada e vê qual path tem melhor WR.

---

### B-53 — Fase de coleta forçada: DNA freeze por 2–3 dias
**Status:** Proposta estratégica · 12/06/2026
**Origem:** Brain · observação sobre ritmo de sprints vs validação

**O problema identificado:** cada sprint adiciona gates. Mais gates = menos trades. Menos trades = validação mais lenta. Após o Hard Reset de 12/06, estamos com zero trades e DNA completamente novo. Existe risco real de calibrar para sempre sem confirmar se o core thesis funciona.

**Proposta:** depois que o DNA estiver estável por 1–2 sessões sem bugs novos visíveis, declarar formalmente um "DNA freeze" — nenhum gate novo, nenhuma mutação de parâmetro, por 2–3 dias de coleta. Objetivo único: chegar a 50 trades com o mesmo DNA para responder a pergunta fundamental.

**O que fazer durante o freeze:** Brain analisa logs, ARIA analisa eAssets, registra tudo no backlog. Zero implementação. Forge disponível para bugs críticos (D-URGENTE) mas não para calibrações.

**Critério de término:** 50 trades fechados com WR e PF calculáveis — daí Brain/Doreto decide: go/no-go live, ou nova rodada de calibrações com evidência real.

**Quando ativar:** Doreto decide. Brain recomenda após 2 sessões limpas consecutivas sem SL catastrófico.

---

### B-54 — O Squeezometer discrimina? Questão estrutural sem resposta
**Status:** Questão estratégica aberta · 12/06/2026
**Origem:** Brain · análise histórica + padrão observado

Identificado em 03/06: diferença de 0.7pts entre winners (96.4) e losers (95.7). Score 100 com MFE=0 documentado múltiplas vezes. Adicionamos gates que bloqueiam losers óbvios, mas o Squeezometer em si — o número que aparece na tela — ainda não prediz qualidade de entrada.

**A questão real:** os gates que adicionamos são a inteligência do sistema, ou o score deveria fazer isso? Existe uma versão do Squeezometer onde score 85 entra e score 78 não entra de forma confiável? Ou o threshold é só um filtro de sanidade e a discriminação real vem dos gates individuais?

**Por que importa:** se o score não discrimina, continuar calibrando o threshold (78, 80, 85, 90) é perda de tempo — o que importa são os gates. Se discrimina mas está mal calibrado, os pesos dos componentes precisam de revisão com dados reais.

**Como responder:** após 50+ trades limpos, Brain roda análise discriminante: score médio winners vs losers, dispersão por componente (qual componente do score mais diferencia?). Se diferença < 3pts → score é ornamental, gates são a inteligência real. Se diferença > 5pts → score tem valor preditivo, vale calibrar pesos.

**Próximo passo:** aguarda B-53 (coleta forçada de 50 trades).

---

### B-55 — Ring buffers sub-minuto: prioridade real antes do Live
**Status:** Backlog estratégico · reafirmado 12/06/2026
**Origem:** Brain · análise do gap de timing do SS

O horizonte real de uma squeeze de liquidação em altcoin é 60–180 segundos. O SS entra com decisão em dados de 5m. Até o sinal disparar, parte do movimento já aconteceu — daí os squeeze_failed com MFE=0 em ativos que depois subiram.

O app eAssets já opera em segundos. O SS opera em minutos. Esse gap é onde o edge vai embora.

**O que é:** ring buffers de 10s/20s/30s alimentados pelo AggTrade WebSocket já existente. Campos novos: `price_change:30s`, `cvd_delta:10s`, `trades_rate:20s`. Se nenhum confirmar momentum atual no momento do sinal → não entra, independente do score.

**Por que é mais importante do que parece:** não é um gate a mais — é a diferença entre entrar no setup e entrar no início do movimento. Atualmente o SS entra no setup. Com sub-minuto, entra quando o movimento começou de fato.

**Pré-requisito:** 50+ trades para confirmar que o padrão de "entrou no setup mas o squeeze veio depois" é recorrente (não só os casos documentados de ZAMA/JTO/VIC em 03/06).

**Próximo passo:** pós B-53 (coleta forçada). Brain analisa squeeze_failed com Post-Trade Impact positivo e quantifica o gap de timing. Se padrão recorrente → vira task prioritária pré-Live.

---

---

### B-56 — Path B: Momentum Rider (proposta Forge × Doreto · 12/06/2026)
**Status:** Backlog de estudo · zero código até Path A validado (50+ trades, KPIs GO/LIVE)
**Origem:** Sessão Forge × Doreto · 12/06/2026
**Supersede:** B-52 (absorvido aqui com expansão)

#### O que é

Path A (SS atual) é sniper de evento pontual — detecta cascade, extrai momentum de 90–300s. Path B é diferente na física: detecta início de movimento direcional antes de ele ser óbvio — acumulação terminando, força relativa aparecendo. Entra cedo, deixa o trade respirar, extrai a perna completa.

São complementares. Path A opera em segundos, Path B em minutos. Não concorrem — coexistem.

#### Evidência que sugere edge (caso RIFUSDT · 12/06)

Score=100, CVD=61.3%, RSI:1h=82.5, EMA=6/máx, EMA:4h=+2, FR=-0.000496 (shorts pagando), lsr_trend=-0.051. Path A rejeitou por lsr_trend > -0.3. O threshold foi calibrado para shorts capitulando em massa — confirmação tardia. lsr_trend=-0.051 com esse DNA pode ser exatamente o onset de Path B: shorts começando a sentir pressão, não capitulando ainda.

#### Diferenças fundamentais Path A vs Path B

| Dimensão | Path A — Cascade | Path B — Momentum |
|----------|-----------------|-------------------|
| Gatilho | liq_cascade + CVD spike | ema alinhado + range_level + exp_btc crescendo |
| Hold time | 90–300s | 5–30 min |
| Stop loss | 2.5% | 3–5% |
| Leverage | 10x | 3–5x |
| Trailing | 75% callback rápido | largo, segue tendência |
| Exit lógica | squeeze_failed + tempo | reversão de tendência |
| Dados chave | liq_short_1m, liq_cascade | ema multi-TF, range_level:1h, exp_btc:1h |

O trailing atual mata Path B — callback de 75% em 90s fecha antes da segunda perna existir.

#### Estudos necessários antes de qualquer código

**E-01 → ARIA** (pode começar nos snapshots históricos já disponíveis):
Para cada ativo nos snapshots eAssets com ema_trend_4h ≥ +4 + range_level:1h ≥ 3 + exp_btc:1h > 10 — qual foi o movimento nas 2h seguintes? Se <40% geraram move de 5%+ → sem edge, proposta descartada.

**E-02 → Brain** (aguarda B-53 — coleta forçada):
Definir o "onset detector" com base nos dados reais. Candidatos: (a) primeiro candle 5m fechando com CVD acelerando 2 ciclos consecutivos; (b) exp_btc:1m cruzando zero com exp_btc:1h já positivo; (c) range_level:5m subindo de 0 para ≥2 com ema_trend_4h≥+4. Qual tem base nos dados? Brain define, Doreto aprova.

**E-03 → Brain** (aguarda coleta de 50+ trades limpos):
Nos trades fechados: qual percentual teve MFE > 8% e saiu com <3%? Isso quantifica o custo do trailing agressivo atual e fundamenta a necessidade de trailing diferente no Path B.

**E-04 → ARIA** (pode começar nos snapshots históricos):
Mapear quais símbolos têm padrão de tendência limpa (move 10%+ sustentado por 15min+) vs reversão imediata. Define o universo candidato Path B — estimativa Forge: 50–80 símbolos, não 527.

**E-05 → Brain + Forge** (futuro — após evidência dos estudos acima):
Implementar Path B como modo observacional puro. Zero entradas reais. Logar sinais que teriam entrado e o que teria acontecido. Coletar 2–3 semanas em paralelo com Path A rodando.

#### O que Path B NÃO é

- Não é gate a mais no Path A — são pipelines separados, capital separado
- Não é swing trading de dias — continua intraday Futures, horizonte de minutos
- Não é prioridade agora — Path A precisa de validação primeiro
- Não substitui o cascade — coexistem

#### Definição formal do Path B (aprovada Brain · 12/06/2026)

Após E-01 ARIA, os 4 critérios de entrada confirmados:
```
ema_trend:4h ≥ +4
range_level:1h ≥ 3
exp_btc:1h > 10
lsr_trend:1h ≤ 0   ← discriminador central (adicionado pós E-01)
```
Com esse combo: 60% taxa de move ≥+5% nas 2h seguintes (n=14, 1 dia — confirmar em mais dados).

**EPICUSDT-type (LSR positivo, subiu mesmo assim):** é demand breakout (B-34-type), não Path B. Não incluir — diluiria o critério lsr:1h ≤ 0 que é o discriminador central.

**FR como sinal de qualidade adicional (hipótese — n=2 ainda):** FR > +0.001 + lsr:1h ≤ 0 → move esperado maior (ESPORTSUSDT +12.7% e +58.5%). FR neutro + lsr:1h ≤ 0 → move menor mas edge presente. Formalizar em dois tiers após 20+ observações.

**Universo candidato E-04 (ARIA · 12/06):** ~40 símbolos.
- Tier 1 (acumulação sustentada máxima, 4/4 snaps): MANTAUSDT, BROCCOLIF3BUSDT, ASRUSDT, SOONUSDT
- Tier 2 (tendência pura): PARTIUSDT, USUSDT, STGUSDT, VELVETUSDT, AIOUSDT, BEATUSDT, BRUSDT, BANKUSDT, CRVUSDT, ARCUSDT + outros
- Tier 3 (3/4 snaps): AIOTUSDT, OPENUSDT, ESPORTSUSDT, EPICUSDT, FHEUSDT, ZEREBROUSDT
- EXCLUÍDOS: SPACEUSDT (slippage A-05), BTCDOMUSDT (rever)
- Zona cinza (monitorar): GWEIUSDT, CCUSDT, BIOUSDT

**Case model confirmado:** ESPORTSUSDT — +12.7% (S2→S3) e +58.5% (S3→S4) com lsr_trend:1h negativo e FR extremo. Mesmo ativo que foi -43% no Path A (cascade). Confirma que são físicas distintas — o que mata no Path A funciona no Path B.

**Pendência E-01:** N=14, 1 dia, 1 regime. ARIA precisa de snapshots de 3-5 dias com regimes distintos (BTC lateral, BTC subindo, fim de semana) antes do estudo ser robusto o suficiente para formalizar onset detector.

#### Checklist de pré-requisitos (Brain monitora)

- [ ] Path A: 50+ trades com DNA atual
- [ ] Path A: WR ≥ 55%, PF ≥ 1.3
- [x] E-01 ARIA: validação inicial concluída (60% com 4 critérios · N=14 · ampliar para 3-5 dias)
- [ ] E-01 ARIA: confirmação em múltiplos regimes (3-5 dias de snapshots)
- [ ] E-02 Brain: onset detector aprovado por Doreto (aguarda E-01 completo)
- [x] E-04 ARIA: universo ~40 símbolos mapeado (Tier 1-3 + zona cinza)
- [ ] Autorização Doreto para iniciar E-05 (fase ghost)

---

### B-57 — Limite de 200 streams WebSocket Binance (risco pré-B-55)
**Status:** Risco de infraestrutura · investigar antes de B-55 virar task  
**Origem:** Forge · deliberação Brain × Forge · 12/06/2026

A Binance limita 200 streams por conexão WebSocket. O SS hoje tem +527 símbolos com chunking de conexões — mas nunca foi auditado formalmente se todos os símbolos estão cobertos uniformemente.

**Risco específico:** quando B-55 (ring buffers sub-minuto) for implementado, cada símbolo vai precisar de stream AggTrade em janelas de 10/20/30s. Isso pode dobrar o consumo de streams e quebrar o chunking atual silenciosamente.

**Próximo passo:** antes de B-55 virar task, Forge audita `data_engine.py` — contar streams ativos por conexão, confirmar cobertura dos 527 símbolos, e estimar impacto de B-55 no consumo total. Brain registra como pré-requisito de B-55.

---

### B-58 — D-E3 em monitoramento: gate ema1h≥4 + ema4h≤2
**Status:** Monitoramento ativo · 13/06/2026
**Origem:** Análise profunda Brain 13/06 — sessão 7ª

Evidência inicial: n=3 trades com ema1h=6 AND ema4h≤2, WR=0%, -$6.01. Forge recomendou adiar (n=3 pequeno, D-E1+D-E2 cobrem parte). Brain concordou.

**Critério para virar task:** após 20+ trades limpos pós-restart 13/06, Brain verifica se o padrão persiste. Se ema1h≥4 + ema4h≤2 continuar com WR < 35% → propor gate com diff exato para Forge. Se D-E1/D-E2 eliminarem a maioria dos casos → encerrar observação.

**Nota:** ema4h=2 não é pego por D-E1 (threshold ≤ -2). D-E3 cubriria o gap ema4h=0 e ema4h=2 quando overextended no 1h.

---

### B-59 — squeeze_failed: problema central não resolvido
**Status:** Investigação pendente · 13/06/2026
**Origem:** Análise profunda Brain 13/06 — sessão 7ª

48.5% dos trades pós-reset são squeeze_failed (n=16), WR=0%, -$19.06. D-E1 e D-E2 removem alguns casos da amostra (5+4=9 trades) mas o squeeze_failed em si permanece o maior dreno do sistema.

**Perfil dos squeeze_failed remanescentes (sem os capturados por D-E1/D-E2):**
- Cascade=True com liq>$1000 e ema4h≥-1 — squeeze não confirmado em 90s
- MFE=0 imediato na maioria — entrada prematura, não setup errado

**Hipótese Brain:** o timing de entrada é o problema estrutural, não os gates de seleção. Ring buffers sub-minuto (B-55) são a resposta correta — confirmar que o squeeze JÁ começou antes de entrar.

**Próximo passo:** com 20+ trades limpos, Brain separa squeeze_failed por perfil (liq, cascade, ema4h) e quantifica o gap de timing usando Post-Trade Impact 5min/15min. Se padrão confirmar → B-55 sobe de prioridade no roadmap pré-Live.

---

_Versão 4.1 · 13/06/2026 — B-58 adicionado (D-E3 monitoramento) · B-59 adicionado (squeeze_failed estrutural) · D-E1/D-E2 implementados (1e715e5) · PaperAnalyzer auto-apply desabilitado · baseline limpo estabelecido (Brain · sessão 7ª)_
