# SqueezeSniper-V4

Bot lean para Binance Futures: detecção de **short squeeze** (OI ↑, LSR ↓, pressão de compra) com arquitetura modular pós-pivot do projeto `#3 Monitor`.

## Requisitos

- Python 3.10+
- Conta Binance Futures com API key (permissões de leitura; trading só em `live`)

## Setup rápido

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edite .env: só API_KEY e API_SECRET (e integrações futuras)
# Preferências locais (recomendado sem git):
copy preferences.example.json preferences.local.json
# Edite preferences.local.json — modo, top_n, dashboard
```

## Executar (paper + dashboard no browser)

```powershell
pip install -r requirements.txt
python main.py
```

O navegador abre em `http://127.0.0.1:8765` (configurável em `preferences.local.json`).

- **Paper**: `"trading_mode": "paper"` — sem ordens reais; sinais em `logs/signals.jsonl`
- **Live** (cuidado): `"trading_mode": "live"` no seu JSON local

Prioridade de prefs: `preferences.local.json` → `preferences.json` → `PREFERENCES_FILE` no `.env`

## Estrutura

```
main.py              # Orquestrador
config.py            # .env (segredos) + preferences.json (bot)
preferences.json     # Modo, top N, sinais, SL/TP — editável sem reiniciar secrets
src/data_engine.py   # WebSocket + OI/LSR + métricas base
src/signal_engine.py # Regras de squeeze + cooldown
src/sniper.py        # Execução (paper/live)
src/ui.py            # Dashboard terminal
ROADMAP.md           # Marcos e estado do projeto
docs/GOVERNANCE.md   # Regras de evolução e riscos
```

## Documentação

- [ROADMAP.md](ROADMAP.md) — marcos, gap vs eassets, sprints
- [docs/EASSETS_REFERENCE.md](docs/EASSETS_REFERENCE.md) — contrato de métricas e fases do painel
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — camadas e anti-padrões Monitor
- [docs/GOVERNANCE.md](docs/GOVERNANCE.md) — governança P0–P3, DoD
- [AGENTS.md](AGENTS.md) — orientação para agentes de código

## Pivot (resumo)

O bot antigo concentrava demais lógica em poucos arquivos enormes. O V4 mantém **top 100** por volume, OI a cada **8s**, slopes exponenciais inspirados em eassets, e separação clara entre detecção e execução.
