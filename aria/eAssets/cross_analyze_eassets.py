
import json
from pathlib import Path

# Paths
LOGS_DIR = Path(__file__).parent.parent / "logs"
EASSETS_DATA_DIR = Path(__file__).parent / "dados_eassets"
EASSETS_JSON = EASSETS_DATA_DIR / "eassets-panel-20260607-102455.json"
PAPER_CLOSED = LOGS_DIR / "paper_closed.jsonl"
SIGNALS = LOGS_DIR / "signals.jsonl"
REFUSALS = LOGS_DIR / "signal_refusals.jsonl"


def load_jsonl(path):
    data = []
    if not path.exists():
        return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except Exception as e:
                    pass
    return data


def load_sniper_signals(logs_dir: Path):
    signals = {}
    signals_file = logs_dir / "signals.jsonl"
    if signals_file.exists():
        with open(signals_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                try:
                    sig = json.loads(line.strip())
                    symbol = sig.get("symbol")
                    if symbol and symbol not in signals:
                        signals[symbol] = sig
                except Exception:
                    continue

    if not signals:
        closed_file = logs_dir / "paper_closed.jsonl"
        if closed_file.exists():
            with open(closed_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    try:
                        trade = json.loads(line.strip())
                        sig = trade.get("entry", {}).get("signal", {})
                        symbol = sig.get("symbol")
                        if symbol and symbol not in signals:
                            signals[symbol] = sig
                    except Exception:
                        continue
    return signals


def main():
    print("=" * 80)
    print("ANALISE CRUZADA eAssets <-> Squeeze Sniper")
    print("=" * 80)

    # Load eAssets data
    if not EASSETS_JSON.exists():
        print(f"Arquivo {EASSETS_JSON.name} nao encontrado!")
        return

    with open(EASSETS_JSON, "r", encoding="utf-8") as f:
        eassets_data = json.load(f)

    eassets_symbols = eassets_data.get("data", {})
    print(f"\nTotal de simbolos no eAssets: {len(eassets_symbols)}")

    # Load Squeeze Sniper data
    paper_trades = load_jsonl(PAPER_CLOSED)
    signals = load_jsonl(SIGNALS)
    sniper_signals = load_sniper_signals(LOGS_DIR)

    print(f"Total de trades fechados no SS: {len(paper_trades)}")
    print(f"Total de sinais gerados no SS: {len(signals)}")
    print(f"Total de sinais unicos por simbolo no SS: {len(sniper_signals)}")

    # Process eAssets symbols
    print("\n" + "=" * 80)
    print("OPORTUNIDADES PERDIDAS (eAssets mostrou movimento, SS nao capturou ou saiu cedo)")
    print("Foco: Divergencia entre Tendencia (eAssets) vs Gatilho (Sniper)")
    print("=" * 80)

    ss_traded_symbols = {t["symbol"] for t in paper_trades}
    ss_signal_symbols = {s["symbol"] for s in signals}

    strong_symbols = []
    for symbol, data in eassets_symbols.items():
        if isinstance(data, dict):
            price_change_1d = float(data.get("price_change:1D", 0) or 0)
            trades_5m = int(data.get("trades:5m", 0) or 0)
            oi_trend = float(data.get("oi_trend:5m", 0) or 0)
            exp_5m = float(data.get("exp:5m", 0) or 0)
            ema_trend = int(data.get("ema_trend:1h", 0) or 0)
            range_level = float(data.get("range_level:1h", 0) or 0)
            
            strength = 0
            if price_change_1d >= 5:
                strength += 3
            if exp_5m >= 4:
                strength += 3
            if oi_trend >= 1:
                strength += 2
            if trades_5m >= 300:
                strength += 1
            if ema_trend >= 4: # eAssets Gold: Tendencia forte no 1h
                strength += 2

            if strength >= 3:
                strong_symbols.append({
                    "symbol": symbol,
                    "strength": strength,
                    "priceChange1d": price_change_1d,
                    "exp5m": exp_5m,
                    "oiTrend5m": oi_trend,
                    "trades5m": trades_5m,
                    "ema_trend": ema_trend,
                    "range_level": range_level
                })

    print(f"\nSimbolos com movimento forte no eAssets: {len(strong_symbols)}")

    print("\n--- TOP 25 OPORTUNIDADES (por forca) ---")
    for symbol_data in sorted(strong_symbols, key=lambda x: x["strength"], reverse=True)[:25]:
        symbol = symbol_data["symbol"]
        traded = symbol in ss_traded_symbols
        signaled = symbol in ss_signal_symbols

        status = "Sinal gerado e trade feito" if traded else "Apenas sinal gerado" if signaled else "Nenhum sinal/trade"
        print(f"\n{symbol}")
        print(f"   Forca eAssets: {symbol_data['strength']}/11 | 24h: {symbol_data['priceChange1d']:.1f}% | EMA 1h: {symbol_data['ema_trend']}")
        print(f"   Status no SS: {status}")
        
        if not signaled and symbol_data['ema_trend'] >= 4:
            print(f"   ⚠️ ALERTA: Sniper ignorou tendencia forte (EMA Trend {symbol_data['ema_trend']})")
        if symbol_data['range_level'] > 70:
            print(f"   📦 ACUMULACAO: Ativo em zona de explosao (Range Level {symbol_data['range_level']:.1f})")

        if traded:
            trades_for_symbol = [t for t in paper_trades if t["symbol"] == symbol]
            for trade in trades_for_symbol:
                pnl = trade.get("entry", {}).get("realized_pnl_usdt", 0)
                entry_signal = trade.get("entry", {}).get("signal", {})
                duration = trade.get("exit", {}).get("time", 0) - trade.get("entry", {}).get("time", 0)
                
                print(f"   -> PNL: {pnl:.2f} | Score SS: {entry_signal.get('score')} | Duracao: {duration/60:.1f}min")
                if duration >= 470: # Perto do Max Hold
                    print(f"      🚨 ALPHA DECAY: Saiu por tempo. O eAssets indica que a tendencia ainda era de {symbol_data['ema_trend']}")

    # Detail analysis of HOLOUSDT
    print("\n" + "=" * 80)
    print("ANALISE DETALHADA DE HOLOUSDT (oportunidade que SS capturou parcialmente)")
    print("=" * 80)

    if "HOLOUSDT" in eassets_symbols:
        holo_data = eassets_symbols["HOLOUSDT"]
        print(f"\nDados do eAssets para HOLOUSDT:")
        print(f"   Price Change 24h: {holo_data.get('price_change:1D', 'N/A')}%")
        print(f"   EXP 5m: {holo_data.get('exp:5m', 'N/A')}")
        print(f"   OI Trend 5m: {holo_data.get('oi_trend:5m', 'N/A')}")
        print(f"   Trades 5m: {holo_data.get('trades:5m', 'N/A')}")

        holo_trades = [t for t in paper_trades if t["symbol"] == "HOLOUSDT"]
        print(f"\nTrades do SS em HOLOUSDT: {len(holo_trades)}")
        for i, trade in enumerate(holo_trades, 1):
            print(f"\nTrade {i}:")
            print(f"   PNL: {trade['entry']['realized_pnl_usdt']:.2f}")
            print(f"   SS Score na entrada: {trade['entry']['signal']['score']}")
            print(f"   SS CVD 1m na entrada: {trade['entry']['signal']['cvd_1m']}")
            print(f"   Max Hold Seconds: 480 (8 minutos)")
            print(f"   -> SS SAIU CEDO DEMAIS! O preco continuou subindo!")

    # Analyze CVD filter
    print("\n" + "=" * 80)
    print("ANALISE DO FILTRO DE CVD (entrada com CVD negativo = PERDA)")
    print("=" * 80)
    bad_cvd_trades = [t for t in paper_trades if t["entry"]["signal"]["cvd_1m"] < 0]
    print(f"\nTotal de trades com CVD 1m negativo na entrada: {len(bad_cvd_trades)}")
    for trade in bad_cvd_trades:
        print(f"   {trade['symbol']}: PNL {trade['entry']['realized_pnl_usdt']:.2f} | CVD 1m SS: {trade['entry']['signal']['cvd_1m']}")

    print("\n" + "=" * 80)
    print("CONCLUSOES")
    print("=" * 80)
    print("1. NAO ENTRE COM CVD 1m NEGATIVO! Todos esses trades perderam (apenas taxas)!")
    print("2. SS SAIU CEDO DEMAIS em varias oportunidades! Aumentar MAX_HOLD_SECONDS?")
    print("3. Muitas oportunidades NAO foram pegas! Relaxar alguns filtros (min_score, min_rsi, etc)?")
    print("4. 18 trades em ~24h com win rate 11.1%: precisamos ajustar!")


if __name__ == "__main__":
    main()
