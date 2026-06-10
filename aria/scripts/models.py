"""
models.py — Dataclasses e enums compartilhados entre os indicadores
Doreto Squeeze Sniper — Indicadores Proprietários v1.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── Enums de estado ──────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW      = "BAIXO"
    MODERATE = "MODERADO"
    HIGH     = "ELEVADO"
    CRITICAL = "CRÍTICO"


class ResetState(str, Enum):
    NEUTRAL      = "NEUTRO"
    PARTIAL      = "RESET PARCIAL"
    STRONG       = "RESET FORTE"
    EXTREME      = "RESET EXTREMO"
    V_LIGHTNING  = "V RELÂMPAGO"


# ─── Inputs ───────────────────────────────────────────────────────────────────

@dataclass
class CRMInput:
    """
    Dados necessários para calcular o CRM (Crypto Risk Meter).
    Todos os campos são opcionais — o indicador calcula com o que tiver,
    marcando os campos ausentes como None e ajustando o score proporcionalmente.
    """
    usdt_dominance:     Optional[float] = None  # % dominância USDT (ex: 8.7)
    fear_greed_index:   Optional[int]   = None  # 0–100 (ex: 12 = Extreme Fear)
    btc_change_24h:     Optional[float] = None  # % variação BTC 24h (ex: -4.27)
    funding_rate_avg:   Optional[float] = None  # média funding dos ativos (ex: 0.0003)
    eth_dominance:      Optional[float] = None  # % dominância ETH (ex: 8.8)


@dataclass
class GRMInput:
    """
    Dados necessários para calcular o GRM (Global Risk Meter).
    Depende de fontes externas (Yahoo Finance). O módulo inclui
    fetch_grm_data() para buscar automaticamente se não fornecido.
    """
    vix:            Optional[float] = None  # VIX atual (ex: 22.4)
    dxy:            Optional[float] = None  # DXY atual (ex: 104.2)
    sp500_change:   Optional[float] = None  # % variação S&P500 (ex: -1.2)
    nasdaq_change:  Optional[float] = None  # % variação Nasdaq (ex: -1.8)
    gold_change:    Optional[float] = None  # % variação Gold (ex: +0.8)


@dataclass
class BTCResetInput:
    """
    Dados necessários para calcular o BTC Reset Monitor.
    rsi_by_tf pode ser fornecido pronto (do MetricStore do SS)
    ou calculado internamente via closes_by_tf.
    """
    # Opção A — RSIs já calculados pelo MetricStore do SS
    rsi_by_tf: dict = field(default_factory=dict)
    # ex: {'5m': 28.3, '15m': 31.2, '30m': 29.8, '1h': 27.5,
    #      '4h': 18.1, '12h': 11.5, '1d': 10.6}

    # Opção B — Closes brutos (o módulo calcula o RSI internamente)
    closes_by_tf: dict = field(default_factory=dict)
    # ex: {'5m': [42100, 42050, ...], '1h': [...]}

    # Liquidações BTC na última hora (USD)
    liq_usd_1h: float = 0.0

    # Parâmetros configuráveis
    rsi_threshold:   float = 30.0       # RSI abaixo = TF resetado
    liq_threshold:   float = 10_000_000 # 10M USD default

    # Histórico de RSI por TF para detectar padrão V
    # ex: {'5m': [55.2, 42.1, 28.3, 31.5, 50.2], '1h': [...]}
    rsi_history_by_tf: dict = field(default_factory=dict)


# ─── Outputs ──────────────────────────────────────────────────────────────────

@dataclass
class CRMOutput:
    score:      float           # 0–100
    level:      RiskLevel       # BAIXO / MODERADO / ELEVADO / CRÍTICO
    components: dict            # score de cada componente
    missing:    list            # campos ausentes que não foram calculados
    summary:    str             # texto resumido para log/dashboard


@dataclass
class GRMOutput:
    score:      float
    level:      RiskLevel
    components: dict
    missing:    list
    summary:    str


@dataclass
class TFResetStatus:
    """Estado de reset de um timeframe específico."""
    tf:         str             # '5m', '1h', etc.
    rsi:        float           # RSI atual
    is_reset:   bool            # RSI < threshold
    is_watch:   bool            # RSI < threshold + 10 (zona de atenção)
    is_v:       bool            # padrão V detectado
    weight:     float           # peso deste TF no score total


@dataclass
class BTCResetOutput:
    score:          float           # 0–100
    state:          ResetState      # NEUTRO / PARCIAL / FORTE / EXTREMO / V
    tf_statuses:    list            # lista de TFResetStatus
    reset_count:    int             # quantos TFs estão em reset
    v_detected:     bool            # padrão V detectado em algum TF
    v_tfs:          list            # quais TFs têm V
    liq_multiplier: float           # multiplicador aplicado pelas liquidações
    liq_usd_1h:     float           # liquidações recebidas
    summary:        str
