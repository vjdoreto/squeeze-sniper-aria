#!/usr/bin/env python3
"""Teste rápido para verificar o enriquecimento CVD"""

import json
from pathlib import Path

# Caminhos
logs_dir = Path(__file__).parent / "logs"

print("=" * 60)
print("TESTE DE ENRIQUECIMENTO CVD")
print("=" * 60)

# 1. Verificar arquivos de log
print("\n1. Verificando arquivos de log:")
for f in ["signals.jsonl", "paper_closed.jsonl"]:
    fp = logs_dir / f
    print(f"   {f}: {'EXISTE' if fp.exists() else 'NÃO EXISTE'}")

# 2. Ler últimos sinais
print("\n2. Últimos sinais do Sniper:")
signals = {}
if (logs_dir / "signals.jsonl").exists():
    with open(logs_dir / "signals.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()[-20:]  # últimos 20 sinais
        for line in reversed(lines):
            try:
                sig = json.loads(line.strip())
                symbol = sig.get("symbol")
                if symbol and symbol not in signals:
                    signals[symbol] = sig
                    print(f"   ✅ {symbol}: CVD={sig.get('cvd_change_pct')}, Score={sig.get('score')}")
            except Exception as e:
                print(f"   ❌ Erro na linha: {e}")
                continue

if not signals and (logs_dir / "paper_closed.jsonl").exists():
    print("\n   Tentando paper_closed.jsonl...")
    with open(logs_dir / "paper_closed.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()[-20:]
        for line in reversed(lines):
            try:
                trade = json.loads(line.strip())
                sig = trade.get("signal", {})
                symbol = sig.get("symbol")
                if symbol and symbol not in signals:
                    signals[symbol] = sig
                    print(f"   ✅ {symbol}: CVD={sig.get('cvd_change_pct')}, Score={sig.get('score')}")
            except Exception as e:
                print(f"   ❌ Erro na linha: {e}")
                continue

if not signals:
    print("\n   ⚠️ Nenhum sinal encontrado no log!")
    print("   Execute o Squeeze Sniper para gerar sinais!")

# 3. Testar com um exemplo de JSON do eassets
print("\n3. Testando enriquecimento com exemplo:")
example_eassets = {
    "timestamp": "2026-06-07T00:00:00",
    "data": {
        "AGTUSDT": {"price": 0.015733, "oi_trend:5m": 10.1},
        "BTCUSDT": {"price": 70000, "oi_trend:5m": 5.0}
    }
}

from enrich_dashboard_json import enrich_eassets_json
result = enrich_eassets_json(example_eassets, signals)
print(f"   ✅ Enriquecidos: {result.get('enriched_symbols', 0)} símbolos")

if "data" in result:
    for sym, data in result["data"].items():
        if "cvd_change_pct:5m" in data:
            print(f"      {sym}: CVD={data['cvd_change_pct:5m']}")

# 4. Procurar por arquivos JSON do eassets na pasta
print("\n4. Arquivos JSON na pasta:")
for f in Path(__file__).parent.glob("*.json"):
    if "enriched" not in f.name and "preferences" not in f.name:
        print(f"   {f.name}")

