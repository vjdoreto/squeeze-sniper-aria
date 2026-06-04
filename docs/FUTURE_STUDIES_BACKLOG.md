# Backlog de Estudos Futuros — SqueezeSniper V4

Este arquivo registra hipóteses e melhorias técnicas para investigação futura, visando otimização de custos e performance sem comprometer a estabilidade atual do sistema.

## 1. Otimização de Taxas: Market vs. Limit Orders
**Data de Registro:** 2026-05-29

### Contexto
O Sniper opera atualmente 100% via ordens a mercado (Market Orders) para garantir a captura imediata da ignição do Squeeze. Isso incorre em taxas de **Taker** (~0.04%).

### Hipótese de Estudo
- **Entrada via Limit Offset:** Avaliar o uso de ordens `LIMIT` com um pequeno *offset* positivo (ex: Preço do Sinal + 0.05%). O objetivo é testar se o sistema consegue ser executado como **Maker** (taxa de ~0.02%) sem perder o rastro da subida exponencial.
- **Saída Passiva (TP Limit):** Implementar `TAKE_PROFIT_LIMIT` no motor do Sniper. Investigar se, em Short Squeezes, a liquidez no topo é suficiente para fechar a posição passivamente ou se o preço "salta" o nível de ordens limitadas, gerando trades enforcados.

### Riscos Detectados
- **Sinal Fantasma:** Preço bate o sinal, mas a ordem limite não é preenchida.
- **Alpha Decay:** O tempo gasto esperando o preenchimento da ordem limite pode resultar em uma entrada em preço pior do que uma ordem a mercado imediata.

### Métrica de Sucesso
Aumento do lucro líquido (Net PnL) por trade em pelo menos 0.04% (economia de taxas) sem reduzir o Win Rate global do sistema.

---

## 2. Gate de Confirmação de Momentum Sub-Minuto
**Data de Registro:** 2026-06-04 · **Origem:** Forge (análise noturna)

### Problema identificado
O DNA detecta **condições para um squeeze** (OI subindo, LSR caindo, CVD positivo em 5m). Mas condição não é squeeze. Os trades com MFE 0% entram quando os ingredientes estão prontos — mas o squeeze nunca começa. Os winners (+12%, +31%) tinham o preço **já se movendo** no momento da entrada.

A diferença entre winner e MFE 0% não está nos indicadores de 5m. Está nos 30-60 segundos antes da entrada.

### Hipótese
Adicionar um gate de sub-minuto que confirme que o squeeze **já começou** antes de entrar:

```python
# Gate de confirmação — squeeze é live, não potencial
price_accel_30s = d.get("price_change:30s") or 0      # preço acelerando agora
volume_spike_20s = d.get("trades_10s") > baseline * 2  # volume explodindo
cvd_delta_10s = d.get("cvd_delta:10s") or 0           # CVD crescendo agora
```

Se nenhum desses confirmar momentum atual → não entra, independente do score 5m.

### Referência de implementação
O `eassets.ai` gerencia dados de segundos em tempo real (1m, sub-minuto). Estudar como fazem a coleta e aggregação de dados em janelas de 10-30s sem sobrecarregar a API.

### Impacto esperado
- Eliminar maioria dos trades MFE 0% (entradas em spike que desmoronam antes do trailing posicionar)
- Melhor timing: entrar na **formação** do squeeze, não no meio de um candle aleatório
- WR pode subir de 63% para 75%+ no trailing_stop (eliminando falsos positivos)

---

## 3. Contexto Macro em Tempo Real — USDT.D, BTC.D, ETH.D
**Data de Registro:** 2026-06-04 · **Origem:** Forge + Doreto

### Problema identificado
O sistema não tem visibilidade do contexto macro em tempo real na decisão de entrada. Um squeeze em ambiente de fuga de capital (USDT.D subindo + BTC.D subindo) é estruturalmente diferente de um em ambiente de rotação (BTC.D subindo, USDT.D estável). Hoje o sistema só usa EXP_BTC por símbolo — não o fluxo agregado de capital.

### Fontes de dados disponíveis

**CoinMarketCap API** (Doreto tem chave):
- `USDT.D` — dominância do Tether (sobe = fuga de cripto)
- `BTC.D` — dominância do Bitcoin (sobe = rotação de alts para BTC)
- `ETH.D` — dominância do Ethereum
- `Fear & Greed Index` — sentimento de mercado (0-100)

**Lógica existente:** Doreto tem código de outro programa que já capturava esses dados via CMC API.

### Hipótese de gate macro

```python
# Gate de contexto macro — bloqueia entrada em fuga de capital
usdt_dominance_rising = usdt_d_1h_change > +0.5   # USDT.D subindo = capital saindo
btc_dominance_rising  = btc_d_1h_change > +0.3    # BTC.D subindo = alts sangrando
fear_greed_extreme    = fear_greed_index < 20      # medo extremo = sem squeeze real

if usdt_dominance_rising and btc_dominance_rising:
    return None  # "macro_capital_flight" — mercado não favorece squeeze
```

**Modo standby:** quando USDT.D sobe mas BTC.D estável = rotação interna entre alts → squeezes reais acontecem nesse cenário, manter ativo.

### Integração sugerida
- Polling CMC API a cada 5 minutos (não precisa ser tempo real)
- Dados armazenados no `DataEngine` como contexto global
- Gate aplicado no `signal_engine.py` antes de qualquer avaliação de sinal

---

## 4. CVD Cap — Perda de Discriminação
**Data de Registro:** 2026-06-04 · **Origem:** Forge

### Problema
CVD está capeado em 999.9% com frequência. Um CVD de 200% e um de 999.9% geram o mesmo score — mas são situações completamente diferentes. O cap existe por razão técnica (overflow de display) mas apaga informação valiosa de discriminação.

### Hipótese
- Remover cap do score interno (manter apenas no display do dashboard)
- Usar escala logarítmica para CVD no score: `log10(cvd_change_pct + 1) × fator`
- Isso preserva discriminação em valores altos sem explodir o score

---

## 5. Paridade com eassets.ai — Dados Sub-Segundo
**Data de Registro:** 2026-06-04 · **Origem:** Doreto + Forge · **Referência:** `docs/EASSETS_REFERENCE.md`

### Contexto
O eassets.ai consegue gerenciar dados de segundos em tempo real para 34+ símbolos simultaneamente. O SqueezeSniper já monitora 529 símbolos mas em janelas de 1m e 5m. Para o gate de confirmação de momentum (item 2 acima), precisamos de janelas de 10-30s.

### Dados necessários
- `price_change:30s` — variação de preço nos últimos 30s
- `cvd_delta:10s` — delta do CVD nos últimos 10s
- `trades_rate:20s` — trades por segundo nos últimos 20s

### Estratégia de implementação
O AggTrade WebSocket já está ativo e entrega cada trade individualmente. O que falta é criar **ring buffers de 10s, 20s e 30s** no `MetricStore` alimentados pelo AggTrade existente — sem nova conexão WebSocket.

Custo computacional: baixo (apenas acumulação em RAM, sem nova I/O).

---

*Documento atualizado: 2026-06-04 · Versão 2.0*