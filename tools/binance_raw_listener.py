"""
tools/binance_raw_listener.py
Listener raw de WebSocket Binance Futures — loga tudo sem filtro.

Uso:
    python tools/binance_raw_listener.py [SYMBOL1 SYMBOL2 ...]
    python tools/binance_raw_listener.py BTCUSDT VELVETUSDT STGUSDT

Sem argumentos usa: BTCUSDT VELVETUSDT STGUSDT AIOUSDT BTWUSDT

Streams capturados por símbolo:
    @aggTrade       — cada negociação (preço, qty, comprador/vendedor)
    @kline_1m       — candle 1m ao vivo
    @markPrice      — mark price + funding rate (a cada ~3s)
    @bookTicker     — melhor bid/ask em tempo real

Stream global:
    !forceOrder@arr — todas as liquidações de futuros

Output: tools/raw_logs/raw_YYYYMMDD_HHMMSS.jsonl  (um evento por linha)
        + print no terminal para acompanhar ao vivo
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Carrega .env manualmente (sem dependência de python-dotenv)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

try:
    from binance import AsyncClient, BinanceSocketManager
except ImportError:
    print("Instale: pip install python-binance")
    sys.exit(1)

API_KEY    = os.environ.get("BINANCE_API_KEY", "")
API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

DEFAULT_SYMBOLS = ["BTCUSDT", "VELVETUSDT", "STGUSDT", "AIOUSDT", "BTWUSDT"]

# Contadores por tipo de evento para o sumário ao vivo
_counters: dict = {}
_start_ts = time.time()


def _log_path() -> Path:
    out = Path(__file__).parent / "raw_logs"
    out.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return out / f"raw_{ts}.jsonl"


def _fmt_event(evt: dict) -> str:
    """Formata evento para print resumido no terminal."""
    e = evt.get("e", evt.get("stream", "?"))
    sym = evt.get("s", evt.get("S", ""))
    ts = datetime.fromtimestamp(evt.get("T", evt.get("E", time.time())) / 1000,
                                tz=timezone.utc).strftime("%H:%M:%S")

    if e == "aggTrade":
        side = "SELL" if evt.get("m") else "BUY "
        return f"[{ts}] aggTrade  {sym:<18} {side}  p={evt['p']}  q={evt['q']}"

    if e == "kline":
        k = evt.get("k", {})
        status = "CLOSED" if k.get("x") else "live  "
        return (f"[{ts}] kline/{k.get('i','?')} {sym:<18} {status}"
                f"  o={k.get('o')}  c={k.get('c')}  v={k.get('v')}")

    if e == "markPriceUpdate":
        return (f"[{ts}] markPrice {sym:<18} mark={evt.get('p')}  "
                f"fund={evt.get('r')}  nextFund={evt.get('T','')}")

    if e == "bookTicker":
        return (f"[{ts}] bookTick  {sym:<18} bid={evt.get('b')} x{evt.get('B')}"
                f"  ask={evt.get('a')} x{evt.get('A')}")

    if e == "forceOrder":
        o = evt.get("o", {})
        side = o.get("S", "?")
        notional = float(o.get("ap", o.get("p", 0))) * float(o.get("z", o.get("q", 0)))
        return (f"[{ts}] LIQ       {o.get('s',''):<18} {side:<5}"
                f"  notional=${notional:,.0f}  ap={o.get('ap')}  z={o.get('z')}")

    return f"[{ts}] {e:<12} {sym:<18} {json.dumps(evt)[:80]}"


async def main(symbols: list[str]):
    log_file = _log_path()
    print(f"\nBinance Futures Raw Listener")
    print(f"Simbolos: {', '.join(symbols)}")
    print(f"Log: {log_file}")
    print(f"Ctrl+C para parar\n{'='*70}\n")

    client = await AsyncClient.create(API_KEY, API_SECRET)
    bsm = BinanceSocketManager(client)

    streams = []
    for s in symbols:
        sl = s.lower()
        streams.append(f"{sl}@aggTrade")
        streams.append(f"{sl}@kline_1m")
        streams.append(f"{sl}@markPrice")
        streams.append(f"{sl}@bookTicker")
    streams.append("!forceOrder@arr")

    print(f"Conectando {len(streams)} streams...")

    event_count = 0
    with log_file.open("w", encoding="utf-8") as f:
        try:
            async with bsm.futures_multiplex_socket(streams) as ws:
                print("Conectado. Recebendo eventos...\n")
                while True:
                    msg = await ws.recv()
                    if not msg:
                        continue

                    data = msg.get("data", msg)
                    # Adiciona timestamp de recebimento
                    data["_recv_ts"] = time.time()
                    data["_stream"] = msg.get("stream", "")

                    # Grava raw
                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    f.flush()

                    event_count += 1
                    e_type = data.get("e", "?")
                    _counters[e_type] = _counters.get(e_type, 0) + 1

                    # Print ao vivo (throttle: só aggTrade de BTC e eventos especiais)
                    show = (
                        e_type in ("forceOrder", "markPriceUpdate")
                        or (e_type == "kline" and data.get("k", {}).get("x"))  # só candles fechados
                        or (e_type == "aggTrade" and data.get("s") == symbols[0])  # só 1º símbolo
                        or (e_type == "bookTicker" and event_count % 50 == 0)  # 1 em 50
                    )
                    if show:
                        print(_fmt_event(data))

                    # Sumário a cada 30s
                    if event_count % 500 == 0:
                        elapsed = time.time() - _start_ts
                        print(f"\n--- {event_count} eventos em {elapsed:.0f}s ---")
                        for k, v in sorted(_counters.items(), key=lambda x: -x[1]):
                            print(f"  {k:<20} {v:>6}")
                        print()

        except (KeyboardInterrupt, asyncio.CancelledError):
            pass

    elapsed = time.time() - _start_ts
    print(f"\n\nEncerrado. {event_count} eventos em {elapsed:.0f}s")
    print(f"Log salvo: {log_file}")
    print("\nContadores por tipo:")
    for k, v in sorted(_counters.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v:>6}")

    await client.close_connection()


if __name__ == "__main__":
    syms = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SYMBOLS
    syms = [s.upper() for s in syms]
    asyncio.run(main(syms))
