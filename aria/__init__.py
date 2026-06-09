"""
indicators — Indicadores Proprietários Doreto Squeeze Sniper
Versão 1.0 · 05/06/2026

Módulos:
    crm       → Crypto Risk Meter
    grm       → Global Risk Meter
    btc_reset → BTC Reset Monitor
    models    → Dataclasses e enums compartilhados

Uso rápido:
    from indicators import calculate_crm, calculate_grm, calculate_btc_reset
    from indicators.models import CRMInput, GRMInput, BTCResetInput
"""

from .crm       import calculate_crm, fetch_crm_data
from .grm       import calculate_grm, fetch_grm_data
from .btc_reset import calculate_btc_reset, get_post_reset_candidates
from .models    import (
    CRMInput, CRMOutput,
    GRMInput, GRMOutput,
    BTCResetInput, BTCResetOutput,
    TFResetStatus, RiskLevel, ResetState,
)

__all__ = [
    "calculate_crm", "fetch_crm_data",
    "calculate_grm", "fetch_grm_data",
    "calculate_btc_reset", "get_post_reset_candidates",
    "CRMInput", "CRMOutput",
    "GRMInput", "GRMOutput",
    "BTCResetInput", "BTCResetOutput",
    "TFResetStatus", "RiskLevel", "ResetState",
]
