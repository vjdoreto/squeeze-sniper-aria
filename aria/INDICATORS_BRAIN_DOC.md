# Indicadores Proprietários — Documentação Técnica
**Para:** Brain · Forge  
**De:** Analista Eassets  
**Data:** 05/06/2026 · v1.0  
**Módulos:** `crm.py` · `grm.py` · `btc_reset.py` · `models.py`

---

## Resumo executivo

Três indicadores proprietários prontos para integração no SS.  
Código modular, tipado, testado, sem dependências além de `aiohttp` (já usado no SS).  
Cada módulo é independente — podem ser integrados um por vez, em qualquer sprint.

```
indicators/
├── __init__.py         # exports limpos
├── models.py           # dataclasses e enums compartilhados
├── crm.py              # Crypto Risk Meter
├── grm.py              # Global Risk Meter
└── btc_reset.py        # BTC Reset Monitor
```

---

## Instalação

Copiar a pasta `indicators/` para `src/` do projeto SS.

```
src/
├── indicators/         ← copiar aqui
│   ├── __init__.py
│   ├── models.py
│   ├── crm.py
│   ├── grm.py
│   └── btc_reset.py
├── data_engine.py
├── signal_engine.py
└── ...
```

Sem novas dependências além de `aiohttp` (já instalado no SS).

---

## 1. CRM — Crypto Risk Meter

### O que faz
Mede o risco do ambiente cripto em tempo real. Score 0–100.  
**Lógica FGI invertida intencionalmente** — medo = oportunidade para este operador.

### Dados necessários

| Campo | Fonte no SS | Status |
|---|---|---|
| `btc_change_24h` | `metric_store.get('BTCUSDT', 'price_change:1D')` | ✅ já existe |
| `funding_rate_avg` | média de `metric_store.get(s, 'fr')` dos ativos ativos | ✅ já existe |
| `usdt_dominance` | CoinGecko `/api/v3/global` | ❌ nova requisição |
| `fear_greed_index` | `api.alternative.me/fng/?limit=1` | ❌ nova requisição |
| `eth_dominance` | CoinGecko `/api/v3/global` (mesmo endpoint do USDT.D) | ❌ nova requisição |

### Integração mínima (com dados já existentes no SS)

```python
# signal_engine.py ou main.py
from src.indicators import calculate_crm, CRMInput

# Dados já disponíveis no SS
btc_chg = self.metric_store.get('BTCUSDT', 'price_change:1D') or 0.0
fr_values = [self.metric_store.get(s, 'fr') or 0.0 for s in self.active_symbols]
fr_avg = sum(fr_values) / len(fr_values) if fr_values else 0.0

crm_result = calculate_crm(CRMInput(
    btc_change_24h=btc_chg,
    funding_rate_avg=fr_avg,
    # usdt_dominance, fear_greed, eth_dominance → None = ignorados
))
# Score calculado com os 2 campos disponíveis (32% do peso total)
```

### Integração completa (com fetch automático)

```python
# main.py — task periódica a cada 5 minutos
from src.indicators import fetch_crm_data, calculate_crm

async def _update_crm_task(self):
    while True:
        try:
            btc_chg = self.metric_store.get('BTCUSDT', 'price_change:1D') or 0.0
            fr_avg  = self._calc_funding_avg()
            crm_data = await fetch_crm_data(
                btc_change_24h=btc_chg,
                funding_rate_avg=fr_avg,
            )
            self.crm_result = calculate_crm(crm_data)
            logger.info(f"CRM: {self.crm_result.score:.1f} [{self.crm_result.level.value}]")
        except Exception as e:
            logger.warning(f"CRM update falhou: {e}")
        await asyncio.sleep(300)  # 5 minutos
```

### Uso no signal_engine (gate opcional)

```python
# Exemplo de uso como contexto — NÃO bloquear sinais (decisão do Brain)
crm = self.crm_result
if crm and crm.score >= 80:
    logger.warning(f"CRM CRÍTICO ({crm.score:.0f}) — ambiente adverso, entrada com risco elevado")
    # Opcional: reduzir kelly ou adicionar ao signal dict
    signal['crm_score'] = crm.score
    signal['crm_level'] = crm.level.value
```

---

## 2. GRM — Global Risk Meter

### O que faz
Mede o risco macro global. Score 0–100.  
Lógica especial: Gold subindo + S&P caindo = bônus de fuga dupla.

### Dados necessários

Todos externos (Yahoo Finance). Nenhum existe no SS atualmente.

| Campo | Symbol Yahoo | Dado usado |
|---|---|---|
| `vix` | `^VIX` | preço atual |
| `dxy` | `DX-Y.NYB` | preço atual |
| `sp500_change` | `^GSPC` | % variação dia |
| `nasdaq_change` | `^IXIC` | % variação dia |
| `gold_change` | `GC=F` | % variação dia |

### Integração completa

```python
# main.py — task periódica a cada 5 minutos
from src.indicators import fetch_grm_data, calculate_grm

async def _update_grm_task(self):
    while True:
        try:
            grm_data = await fetch_grm_data()
            self.grm_result = calculate_grm(grm_data)
            logger.info(f"GRM: {self.grm_result.score:.1f} [{self.grm_result.level.value}]")
        except Exception as e:
            logger.warning(f"GRM update falhou: {e}")
        await asyncio.sleep(300)
```

### Nota sobre Yahoo Finance

Yahoo Finance não requer autenticação mas pode ter instabilidade de CORS/rate limit.  
Se falhar consistentemente, alternativa: `yfinance` library ou Stooq API.  
O módulo retorna `None` nos campos que falharem — score calculado com o que tiver.

---

## 3. BTC Reset Monitor

### O que faz
Detecta desalavancagem do BTC em múltiplos TFs.  
Dois modos: RESET CLÁSSICO (RSI < threshold por tempo mínimo) e V RELÂMPAGO (queda + recuperação rápida).

### Dados necessários

| Campo | Fonte no SS | Status |
|---|---|---|
| `rsi_by_tf` | `metric_store.get('BTCUSDT', 'rsi:5m')` etc | ✅ já existe (5m, 15m, 1h) |
| `rsi_by_tf['4h']` | klines 4h do BTCUSDT | ⚠️ depende de EA-02 (ema_trend:4h) |
| `rsi_by_tf['12h']` | klines 12h | ❌ novo TF a ser adicionado |
| `liq_usd_1h` | acumular `liq_short_1m` por 60 ciclos | ⚠️ requer janela de 1h |
| `rsi_history_by_tf` | ring buffer RSI por TF | ❌ novo — necessário para V |

### Integração mínima (TFs já disponíveis)

```python
# Usando apenas os TFs que já existem no MetricStore
from src.indicators import calculate_btc_reset, BTCResetInput

rsi_tf = {}
for tf in ['5m', '15m', '1h']:  # expandir conforme TFs forem adicionados
    val = self.metric_store.get('BTCUSDT', f'rsi:{tf}')
    if val is not None:
        rsi_tf[tf] = float(val)

reset_result = calculate_btc_reset(BTCResetInput(
    rsi_by_tf=rsi_tf,
    liq_usd_1h=self.liq_usd_1h_accumulator,
    liq_threshold=self.preferences.get('reset_liq_threshold', 10_000_000),
    rsi_threshold=self.preferences.get('reset_rsi_threshold', 30.0),
))

if reset_result.state.value != 'NEUTRO':
    logger.warning(f"BTC RESET: {reset_result.summary}")
```

### Ring buffer para histórico V (necessário para detecção de V)

```python
# metric_engine.py — adicionar ring buffer de RSI por TF para o BTC
# Tamanho sugerido: 10 valores por TF

class BTCRsiHistory:
    """Buffer circular para histórico de RSI do BTC por TF."""
    def __init__(self, maxlen: int = 10):
        from collections import deque
        self._buffers: dict = {}
        self._maxlen = maxlen

    def update(self, tf: str, rsi: float):
        if tf not in self._buffers:
            self._buffers[tf] = deque(maxlen=self._maxlen)
        self._buffers[tf].append(rsi)

    def get(self, tf: str) -> list:
        return list(self._buffers.get(tf, []))

    def snapshot(self) -> dict:
        return {tf: list(buf) for tf, buf in self._buffers.items()}

# Uso em metric_engine.py no ciclo de atualização do RSI:
# self.btc_rsi_history.update('5m', new_rsi_5m)
# self.btc_rsi_history.update('1h', new_rsi_1h)
```

### Parâmetros configuráveis no preferences.json

```json
{
  "reset_monitor": {
    "rsi_threshold": 30,
    "liq_threshold_usd": 10000000,
    "enabled": true
  }
}
```

### Função pós-reset (identificar candidatos da bonança)

```python
from src.indicators import get_post_reset_candidates

if reset_result.state in ('RESET FORTE', 'RESET EXTREMO', 'V RELÂMPAGO'):
    candidates = get_post_reset_candidates(
        reset_output=reset_result,
        symbol_data=self.metric_store.snapshot_all(),
        exp_btc_threshold=-5.0,
    )
    if candidates:
        top = candidates[:5]
        logger.info(f"Candidatos pós-reset: {[c['symbol'] for c in top]}")
        # Opcionalmente: priorizar esses símbolos no próximo ciclo do signal_engine
```

---

## 4. Exposição no dashboard web

Os três resultados devem ser incluídos no `PanelSnapshot` para o WebSocket:

```python
# web_dashboard.py — adicionar ao snapshot
snapshot = {
    # ... campos existentes ...
    "crm": {
        "score": self.crm_result.score if self.crm_result else None,
        "level": self.crm_result.level.value if self.crm_result else None,
    },
    "grm": {
        "score": self.grm_result.score if self.grm_result else None,
        "level": self.grm_result.level.value if self.grm_result else None,
    },
    "btc_reset": {
        "score": self.reset_result.score if self.reset_result else None,
        "state": self.reset_result.state.value if self.reset_result else None,
        "reset_count": self.reset_result.reset_count if self.reset_result else 0,
        "v_detected": self.reset_result.v_detected if self.reset_result else False,
        "tf_statuses": [
            {"tf": s.tf, "rsi": s.rsi, "is_reset": s.is_reset, "is_v": s.is_v}
            for s in (self.reset_result.tf_statuses if self.reset_result else [])
        ],
    },
}
```

---

## 5. Ordem de implementação sugerida

| Sprint | Item | Esforço | Impacto |
|---|---|---|---|
| Sprint 3 | CRM com dados parciais (btc_chg + funding) | **mínimo** | imediato |
| Sprint 3 | BTC Reset com TFs existentes (5m, 15m, 1h) | **baixo** | alto |
| Sprint 4 | CRM completo com fetch_crm_data() | médio | alto |
| Sprint 4 | GRM completo com fetch_grm_data() | médio | médio |
| Sprint 4 | Ring buffer RSI para detecção de V | médio | alto |
| Sprint 5 | BTC Reset com 4h e 12h | baixo | alto |
| Sprint 5 | Exposição no web_dashboard.py | baixo | visual |

---

## 6. Testes

```bash
# Rodar testes (sem dependências externas):
cd /caminho/do/projeto
python -c "
import sys; sys.path.insert(0, 'src')
from indicators.btc_reset import calculate_rsi, detect_v_pattern
from indicators import calculate_crm, calculate_grm, calculate_btc_reset
from indicators.models import CRMInput, GRMInput, BTCResetInput
# ... testes inline
"
```

Todos os cenários validados:
- ✅ CRM com dados parciais (campos None ignorados com normalização)
- ✅ CRM bull vs bear vs ganância extrema
- ✅ GRM risk-on vs stress vs fuga dupla Gold+SP500
- ✅ BTC Reset: NEUTRO / PARCIAL / FORTE / EXTREMO / V RELÂMPAGO
- ✅ RSI calculator Wilder
- ✅ Detecção de padrão V (sem falso positivo)
- ✅ Multiplicador de liquidações

---

## 7. Notas importantes para o Brain

**Sobre o FGI no CRM:**  
A lógica está invertida intencionalmente. FGI=12 (Medo Extremo) = score de risco BAIXO no CRM porque o operador opera contra a manada. Medo extremo = mercado desalavancado = oportunidade. Esta lógica foi definida pelo proprietário e documentada explicitamente no código.

**Sobre o GRM:**  
O GRM hoje contribui pouco para o SS porque os dados são externos. O valor imediato é informativo (dashboard). O valor operacional vem quando o Brain decidir se GRM alto deve afetar o sizing ou a aprovação de sinais — isso é uma decisão futura, não deste sprint.

**Sobre o BTC Reset:**  
Este é o indicador com maior potencial de impacto no SS. A função `get_post_reset_candidates()` é diretamente conectada ao DNA do SS — pós-reset, os ativos com EXP_BTC positivo são os candidatos ao próximo squeeze. Merece prioridade na avaliação.

**Parâmetros configuráveis:**  
`rsi_threshold` (padrão 30) e `liq_threshold` (padrão 10M USD) devem ir para `preferences.json`. O proprietário planeja calibrar esses valores com análise de histórico mensal/anual — os defaults são ponto de partida, não valores finais.

---

*Analista Eassets · 05/06/2026*  
*Indicadores proprietários de Bob Doreto — implementação para avaliação do Brain*
