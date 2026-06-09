"""Secrets from .env; tunable bot settings from preferences.json."""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional, cast

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PREFERENCES_PATH = Path("preferences.json")

ModeName = Literal["paper", "live"]


def get_mode_node(prefs: Dict[str, Any], mode: ModeName) -> Dict[str, Any]:
    node = prefs.get(mode) or {}
    if not isinstance(node, dict):
        raise ValueError(f"Bloco '{mode}' inválido no preferences JSON.")
    return node


def get_mode_signal(prefs: Dict[str, Any], mode: ModeName) -> Dict[str, Any]:
    mode_node = get_mode_node(prefs, mode)
    node = mode_node.get("signal") or prefs.get("signal") or {}
    if not isinstance(node, dict):
        raise ValueError(f"Bloco '{mode}.signal' inválido.")
    return node


def get_mode_execution(prefs: Dict[str, Any], mode: ModeName) -> Dict[str, Any]:
    mode_node = get_mode_node(prefs, mode)
    node = mode_node.get("execution") or prefs.get("execution") or {}
    if not isinstance(node, dict):
        raise ValueError(f"Bloco '{mode}.execution' inválido.")
    return node


@dataclass(frozen=True)
class BotConfig:
    api_key: str
    api_secret: str
    trading_mode: str  # "paper" | "live"
    top_n: int
    usdt_amount: float
    leverage: int
    oi_poll_seconds: float

    min_exp: float
    min_oi_trend: float
    max_lsr_trend: float

    signal_cooldown_seconds: int
    sl_pct: float
    tp_pct: float

    # Sprint 6.1: Parâmetros de Execução Dinâmica
    sl_decay_interval_minutes: int
    sl_decay_step_pct: float
    partial_tp_breakeven_pct: float
    sl_trailing_swing_low: bool
    swing_low_tf: str

    # DNA / Fit score gate
    fit_score_min: float

    # Novos parâmetros P2-D
    min_vol_1m: float
    min_rsi_5m: float
    mtf_1h_crash_threshold: float
    min_exp_btc_for_btc_dump: float

    # Filtros % de crescimento (P1 — primary)
    min_cvd_change_pct: float
    min_oi_change_pct: float
    max_lsr_change_pct: float
    cvd_streak_min: int
    max_bid_ask_spread: float
    min_trades_1m: int
    min_vol_adaptive_ratio: float
    min_oi_accel: float

    # Gestão de capital
    initial_capital: float
    risk_pct_per_trade: float
    fee_pct: float  # SPRINT 6.38: Simulação de taxas reais (Binance Futures)
    blacklist: list[str]

    # Paper trading (Sprint 9.3)
    paper_max_open_positions: int
    live_max_open_positions: int

    signal_mode: str

    # LIVE
    live_closed_jsonl: Path
    live_compound_enabled: bool
    live_auto_pilot: bool
    live_margin_mode: str  # "ISOLATED" | "CROSS"
    liq_history_path: Path # SPRINT 12.116: Persistência do histórico de liquidações
    min_balance_usdt: float

    # Telegram (Sprint 5.4)
    telegram_token: Optional[str]
    telegram_chat_id: Optional[str]


def resolve_preferences_path() -> Path:
    """Único arquivo de preferências. Suporta override via env var PREFERENCES_FILE."""
    raw = os.getenv("PREFERENCES_FILE", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_PREFERENCES_PATH


def _preferences_path() -> Path:
    return resolve_preferences_path()


def load_preferences(path: Path | None = None) -> Dict[str, Any]:
    path = path or _preferences_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Arquivo de preferências não encontrado: {path.resolve()}\n"
            "Verifique se preferences.json existe na raiz do projeto."
        )
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: JSON deve ser um objeto na raiz.")
    return data


def load_config(preferences_path: Path | None = None) -> BotConfig:
    api_key = os.getenv("API_KEY", "").strip()
    api_secret = os.getenv("API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise ValueError("API_KEY e API_SECRET são obrigatórios no .env")

    prefs = load_preferences(preferences_path)
    mode_raw = str(prefs.get("trading_mode", "paper")).strip().lower()
    if mode_raw not in ("paper", "live"):
        raise ValueError(f"trading_mode inválido em preferences.json: {mode_raw!r}")
    mode = cast(ModeName, mode_raw)

    paper_cfg = prefs.get("paper") or {}
    live_cfg = prefs.get("live") or {}

    # SPRINT 12.85: Deep Isolation - Puxa blocos usando helpers
    active_p = get_mode_node(prefs, mode)
    signal = get_mode_signal(prefs, mode)
    execution = get_mode_execution(prefs, mode)

    paper_max_open_positions = int(paper_cfg.get("max_open_positions", 5))
    live_max_open_positions = int(live_cfg.get("max_open_positions", 12))

    # Gestão de capital: mínimo para permitir live (default 0.0 para não “travar” por saldo baixo)
    min_balance_usdt = float(live_cfg.get("min_balance_usdt", 0.0))

    config = BotConfig(
        api_key=api_key,
        api_secret=api_secret,
        trading_mode=mode,
        top_n=int(prefs.get("top_n", 100)),
        usdt_amount=float(active_p.get("usdt_amount", prefs.get("usdt_amount", 50))),
        leverage=int(active_p.get("leverage", prefs.get("leverage", 10))),
        oi_poll_seconds=float(prefs.get("oi_poll_seconds", 8)),

        min_exp=float(signal.get("min_exp", 0.3)),
        min_oi_trend=float(signal.get("min_oi_trend", 0.05)),
        max_lsr_trend=float(signal.get("max_lsr_trend", -0.002)),

        signal_cooldown_seconds=int(signal.get("cooldown_seconds", 320)),
        sl_pct=float(execution.get("sl_pct", 0.02)),
        tp_pct=float(execution.get("tp_pct", 0.04)),

        sl_decay_interval_minutes=int(execution.get("sl_decay_interval_minutes", 0)),
        sl_decay_step_pct=float(execution.get("sl_decay_step_pct", 0.0)),
        partial_tp_breakeven_pct=float(execution.get("partial_tp_breakeven_pct", 0.0)),
        sl_trailing_swing_low=bool(execution.get("sl_trailing_swing_low", False)),
        swing_low_tf=str(execution.get("swing_low_tf", "5m")),

        # CORREÇÃO P0 v4.2.4: Lê min_score do preferences.json (paper.signal.min_score)
        fit_score_min=float(signal.get("min_score", signal.get("fit_score_min", 20.0))),

        min_vol_1m=float(signal.get("min_vol_1m", 0.0)),
        min_rsi_5m=float(signal.get("min_rsi_5m", 48.0)),
        mtf_1h_crash_threshold=float(signal.get("mtf_1h_crash_threshold", -0.05)),
        min_exp_btc_for_btc_dump=float(signal.get("min_exp_btc_for_btc_dump", 0.0)),

        min_cvd_change_pct=float(signal.get("min_cvd_change_pct", 3.0)),
        min_oi_change_pct=float(signal.get("min_oi_change_pct", 0.2)),
        max_lsr_change_pct=float(signal.get("max_lsr_change_pct", -0.5)),
        cvd_streak_min=int(signal.get("cvd_streak_min", 2)),
        max_bid_ask_spread=float(signal.get("max_bid_ask_spread", 0.2)),
        min_trades_1m=int(signal.get("min_trades_1m", 2)),
        min_vol_adaptive_ratio=float(signal.get("min_vol_adaptive_ratio", 0.7)),
        min_oi_accel=float(signal.get("min_oi_accel", 0.0)),

        initial_capital=float(active_p.get("initial_capital", prefs.get("initial_capital", 1000))),
        risk_pct_per_trade=float(active_p.get("risk_pct_per_trade", prefs.get("risk_pct_per_trade", 0.05))),
        fee_pct=float(prefs.get("fee_pct", 0.0004)),
        blacklist=list(prefs.get("blacklist", [])),

        paper_max_open_positions=paper_max_open_positions,
        live_max_open_positions=live_max_open_positions,

        signal_mode=str(signal.get("signal_mode", "conservative")),

        live_closed_jsonl=Path(live_cfg.get("closed_jsonl", "logs/live_closed.jsonl")),
        live_compound_enabled=bool(live_cfg.get("compound_enabled", False)),
        live_auto_pilot=bool(live_cfg.get("auto_pilot", False)),
        live_margin_mode=str(live_cfg.get("margin_mode", "ISOLATED")),
        liq_history_path=Path(prefs.get("liq_history_path", "logs/liquidation_history.jsonl")),
        min_balance_usdt=min_balance_usdt,

        telegram_token=os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )

    validate_config(config)
    return config


def validate_config(cfg: BotConfig):
    """Valida se as configurações carregadas respeitam o DNA do SqueezeSniper."""
    errors: list[str] = []
    warnings: list[str] = []

    # DNA: LSR deve cair (shorts em pânico/liquidação)
    if cfg.max_lsr_trend >= 0:
        errors.append(
            f"DNA Violado: 'max_lsr_trend' ({cfg.max_lsr_trend}) deve ser < 0 para detectar squeeze."
        )

    if cfg.max_lsr_change_pct >= 0:
        errors.append(f"DNA Violado: 'max_lsr_change_pct' ({cfg.max_lsr_change_pct}) deve ser < 0.")

    # DNA: OI deve subir (dinheiro novo entrando na briga)
    if cfg.min_oi_change_pct < 0:
        errors.append(f"DNA Violado: 'min_oi_change_pct' ({cfg.min_oi_change_pct}) não pode ser negativo.")

    # DNA: Momentum mínimo (evita ruído)
    if cfg.min_exp < 0.005:
        warnings.append(
            f"Risco: 'min_exp' ({cfg.min_exp}) extremamente baixo. Perigo de sinais falsos por ruído."
        )

    # DNA: RSI alto é combustível (mínimo de segurança)
    if cfg.min_rsi_5m < 40:
        warnings.append(
            f"Alerta: 'min_rsi_5m' ({cfg.min_rsi_5m}) sugere compra em zona de fraqueza técnica."
        )

    # DNA: Margin mode - só LONG em ISOLATED
    if cfg.live_margin_mode == "CROSS":
        errors.append(
            f"DNA Violado: 'live_margin_mode' ({cfg.live_margin_mode}) deve ser ISOLATED. Só LONG em ISOLADO."
        )

    if warnings:
        for w in warnings:
            print(f"⚠️ CONFIG WARNING: {w}")

    if errors:
        msg = "❌ ERROS CRÍTICOS DE CONFIGURAÇÃO (DNA SQUEEZE):\n - " + "\n - ".join(errors)
        raise ValueError(msg)
