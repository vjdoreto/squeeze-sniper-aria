# Repository Guidelines

## Project Structure & Module Organization
This project is an ultra-lean trading bot focused on Short Squeeze detection and institutional tracking on Binance Futures.
- `.\src\data_engine.py`: The core engine responsible for high-speed data acquisition. It uses WebSockets for `AggTrades` and optimized polling for `Open Interest` (OI) and `LSR`. Calculates exponential trends (`exp`, `oi_trend`, `lsr_trend`).
- `.\config.py`: Secrets from `.env`; prefs from `preferences.local.json` (priority) or `preferences.json`.
- `.\preferences.local.json`: Local tunables (gitignored). Copy from `preferences.example.json`.
- `.\src\web_dashboard.py`: Web UI at http://127.0.0.1:8765 (auto-opens browser).
- `.\src\persistence.py`: Appends signals to `logs/signals.jsonl`.
- `.\src\ui.py`: Rich terminal fallback if `dashboard.terminal_fallback` is true.
- `.\src\signal_engine.py`: Squeeze Ignition detector (exponential slopes, cooldown).
- `.\src\strategy.py`: Legacy shim — imports `SqueezeIgnition` from `signal_engine`.
- `.\src\sniper.py`: Order executor with paper/live mode, position and lot validation.
- `.\main.py`: Main orchestrator (entry point).
- `.\docs\GOVERNANCE.md`: Governance, scope tiers P0–P3, anti-Monitor rules.
- `.\docs\EASSETS_REFERENCE.md`: Metric manifest + panel phases A–D vs eassets JSON.
- `.\docs\ARCHITECTURE.md`: Layer diagram ingest → MetricStore → signal/panel.
- `.\eassets-panel-20260519-220030.json`: Reference export from eassets.ai (field contract).
- `.\.env`: Secrets only (never commit). See `.env.example` for variables.
- `.\requirements.txt`: Minimal dependencies for high performance (`python-binance`, `aiohttp`, `redis`, `pandas`, `numpy`, `websockets`).

## Build, Test, and Development Commands
- **Run Bot**: `python main.py` (paper + web dashboard by default)
- **Logs**: Located in the `.\logs\` directory.

## Key Changes (V4)
- Filters top 100 symbols by 24h volume (not all 500+)
- Updates OI every 8s (not 20s)
- Uses exponential slopes for trend detection (inspired by eassets)
- Position checking before entry
- Quantity validation against lot_size filters

## Strategic Governance (V4)
- **RSI Paradox**: RSI > 75 is NOT a reason to block a signal. Squeezes are momentum anomalies, not mean-reversion events. Overbought RSI often means shorts are being forced to cover. We removed the hard RSI block from the signal engine.
- **Relative Strength**: `exp_btc` (altcoin exp - btc exp) is a crucial metric to filter out noise. We want assets that are strong on their own, not just following BTC.
- **Symbol Funnel**: While we filter by volume to keep the bot lean, `top_n` should be kept relatively high (e.g., 150) in `preferences.local.json` to capture mid-cap squeezes. Deep liquidity targets like BTC/ETH rarely squeeze violently.
