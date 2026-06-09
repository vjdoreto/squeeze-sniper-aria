#!/usr/bin/env python3
"""
Enriquece o JSON do eassets com dados do Squeeze Sniper (CVD, score, etc.)
Uso: python enrich_dashboard_json.py <input_eassets.json> [output_enriched.json] [logs_dir]
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def load_sniper_signals(logs_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Carrega os últimos sinais do Squeeze Sniper do logs/signals.jsonl ou logs/paper_closed.jsonl
    Retorna um dicionário: {symbol: signal_data}
    """
    signals = {}
    signals_file = logs_dir / "signals.jsonl"
    if signals_file.exists():
        with open(signals_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Pegar o último sinal para cada símbolo
            for line in reversed(lines):
                try:
                    sig = json.loads(line.strip())
                    symbol = sig.get("symbol")
                    if symbol and symbol not in signals:
                        signals[symbol] = sig
                except Exception:
                    continue
    
    # Se não tem signals.jsonl, tenta paper_closed.jsonl
    if not signals:
        closed_file = logs_dir / "paper_closed.jsonl"
        if closed_file.exists():
            with open(closed_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    try:
                        trade = json.loads(line.strip())
                        sig = trade.get("signal", {})
                        symbol = sig.get("symbol")
                        if symbol and symbol not in signals:
                            signals[symbol] = sig
                    except Exception:
                        continue
    return signals


def enrich_eassets_json(eassets_data: Dict[str, Any], sniper_signals: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enriquece o JSON do eassets com os dados do Squeeze Sniper
    """
    enriched_count = 0
    
    # Obter o objeto de dados (eassets usa {"data": {...}})
    data_obj = eassets_data.get("data", eassets_data)
    
    # Percorrer cada símbolo
    for symbol, data in data_obj.items():
        if isinstance(data, dict) and symbol in sniper_signals:
            sig = sniper_signals[symbol]
            
            # Adicionar campos do Sniper ao JSON do eassets
            data["cvd_change_pct:5m"] = sig.get("cvd_change_pct")
            data["cvd:5m"] = sig.get("cvd_1m")
            data["cvd_streak:5m"] = sig.get("cvd_streak")
            data["squeeze_sniper_score:5m"] = sig.get("score")
            data["oi_change_pct:5m"] = sig.get("oi_change_pct")
            data["lsr_change_pct:5m"] = sig.get("lsr_change_pct")
            data["trades_1m"] = sig.get("trades_1m")
            data["rsi:5m"] = sig.get("rsi_5m")
            data["ema_trend:5m"] = sig.get("ema_trend")
            data["volume_quality"] = sig.get("volume_quality")
            data["exp_btc_norm_1h"] = sig.get("exp_btc_norm_1h")
            
            enriched_count += 1
    
    # Adicionar metadata
    eassets_data["enriched_symbols"] = enriched_count
    
    return eassets_data


def main():
    if len(sys.argv) < 2:
        print("Uso: python enrich_dashboard_json.py <input_eassets.json> [output_enriched.json] [logs_dir]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else input_path.parent / f"{input_path.stem}_enriched.json"
    # Padrão: logs na pasta raiz do SqueezeSniper (pai da pasta eAssets)
    default_logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir = Path(sys.argv[3]) if len(sys.argv) >= 4 else default_logs_dir
    
    # Carregar JSON do eassets
    with open(input_path, "r", encoding="utf-8") as f:
        eassets_data = json.load(f)
    
    # Carregar sinais do Sniper
    sniper_signals = load_sniper_signals(logs_dir)
    
    # Enriqueça o JSON
    enriched_data = enrich_eassets_json(eassets_data, sniper_signals)
    
    # Salvar resultado
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Enriquecimento concluído! {len(sniper_signals)} símbolos do Sniper encontrados.")
    print(f"📄 Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    main()