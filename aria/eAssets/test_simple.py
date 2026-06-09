
import json
from pathlib import Path

logs_dir = Path(__file__).parent / "logs"

print("=" * 60)
print("TESTE DE ENRIQUECIMENTO CVD")
print("=" * 60)

print("\n1. Verificando arquivos de log:")
for f in ["signals.jsonl", "paper_closed.jsonl"]:
    fp = logs_dir / f
    print(f"   {f}: {'EXISTE' if fp.exists() else 'NAO EXISTE'}")

print("\n2. Lendo sinais do Sniper:")
signals = {}
if (logs_dir / "signals.jsonl").exists():
    with open(logs_dir / "signals.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()[-50:]  # last 50 signals
        for line in reversed(lines):
            try:
                sig = json.loads(line.strip())
                symbol = sig.get("symbol")
                if symbol and symbol not in signals:
                    signals[symbol] = sig
                    print(f"   Encontrado: {symbol} | CVD: {sig.get('cvd_change_pct')} | Score: {sig.get('score')}")
            except Exception as e:
                print(f"   Erro na linha: {e}")
                continue

print(f"\n3. Total de sinais carregados: {len(signals)}")
print(f"   Símbolos: {list(signals.keys())}")

print("\n4. Teste com exemplo de eassets JSON:")
example_eassets = {
    "timestamp": "2026-06-07T00:00:00",
    "data": {
        "JSTUSDT": {"price": 0.07803, "oi_trend:5m": 0.01338},
        "SUSHIUSDT": {"price": 0.2281, "oi_trend:5m": 0.01768},
        "ALICEUSDT": {"price": 1.348, "oi_trend:5m": 0.01581},
        "BTCUSDT": {"price": 70000, "oi_trend:5m": 0.01}
    }
}

data_obj = example_eassets.get("data", example_eassets)
print(f"\nSímbolos no exemplo de eassets: {list(data_obj.keys())}")

print("\n5. Enriquecendo o exemplo:")
enriched_count = 0
for symbol, data in data_obj.items():
    if isinstance(data, dict) and symbol in signals:
        sig = signals[symbol]
        data["cvd_change_pct:5m"] = sig.get("cvd_change_pct")
        data["cvd:5m"] = sig.get("cvd_1m")
        data["cvd_streak:5m"] = sig.get("cvd_streak")
        data["squeeze_sniper_score:5m"] = sig.get("score")
        print(f"   Enriquecido {symbol}: CVD = {data['cvd_change_pct:5m']}, Score = {data['squeeze_sniper_score:5m']}")
        enriched_count += 1

print(f"\n6. Total de símbolos enriquecidos: {enriched_count}")
