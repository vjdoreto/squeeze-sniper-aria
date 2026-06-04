import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from src.signal_engine import SqueezeIgnition

logger = logging.getLogger("BacktestEngine")

class BasicBacktest:
    """
    SPRINT 12.220: Motor de Replay Alpha (Trade Lifecycle).
    Simula entradas, SL/TP e Trailing Stop MFE sobre o rastro histórico.
    """
    def __init__(self, history_date: str):
        self.csv_path = Path(f"logs/history/snapshots_{history_date}.csv")
        self.engine = SqueezeIgnition() # Usa config default ou carrega do JSON
        self.results = []
        self.active_trades = []

    def run(self):
        if not self.csv_path.exists():
            print(f"❌ Histórico para {self.csv_path.name} não encontrado.")
            return

        print(f"⏳ Iniciando Backtest sobre rastro de {self.csv_path.name}...")
        df = pd.read_csv(self.csv_path)
        
        # Agrupa por timestamp para simular o loop do bot
        timestamps = df['timestamp'].unique()
        
        for ts in sorted(timestamps):
            # Simula um 'tick' do motor de dados
            snap = df[df['timestamp'] == ts]
            market_data = {}
            for _, row in snap.iterrows():
                market_data[row['symbol']] = {
                    "price": row['price'],
                    "oi": row['oi'],
                    "lsr": row['lsr'],
                    "exp:5m": row.get('exp', 0), # Mapeamento de colunas CSV
                    "oi_trend:5m": row.get('oi_trend', 0),
                    "lsr_trend:5m": row.get('lsr_trend', 0),
                    "volume_delta_1min": row.get('cvd_1m', 0),
                    "trades_count_1min": row.get('trades_1m', 0),
                    "exp_btc:5m": row.get('exp_btc', 0),
                }
            
            # Testa sinais para cada símbolo nesse timestamp
            for symbol, d in market_data.items():
                hit = self.engine.analyze(symbol, market_data, trading_mode="paper")
                if hit:
                    self.results.append({
                        "ts": ts,
                        "symbol": symbol,
                        "price": hit['price'],
                        "score": hit['score'],
                        "exit_price": None,
                        "pnl": 0.0
                    })
            
            # Simulação de Saída (Simplificada para validação de lógica)
            self._update_virtual_trades(market_data)

        self._report()

    def _update_virtual_trades(self, market_data):
        """Simula a caça ao preço (Trailing Stop) nos trades abertos no backtest."""
        for t in self.results:
            if t["exit_price"] is not None: continue
            
            symbol = t["symbol"]
            if symbol in market_data:
                current_price = market_data[symbol]["price"]
                entry_price = t["price"]
                pnl = (current_price / entry_price - 1) * 100
                
                # Simulação Profit Guard (5% lucro -> trava 2%)
                if pnl >= 5.0:
                    t["exit_price"] = entry_price * 1.02
                    t["pnl"] = 2.0
                    t["reason"] = "profit_guard"
                # Simulação Stop Loss Simples (2%)
                elif pnl <= -2.0:
                    t["exit_price"] = entry_price * 0.98
                    t["pnl"] = -2.0
                    t["reason"] = "stop_loss"

    def _report(self):
        print("\n" + "="*40)
        print(f"📊 RESULTADO DO BACKTEST")
        print("="*40)
        print(f"Total de Sinais Detectados: {len(self.results)}")
        
        if not self.results:
            print("⚠️ Nenhum sinal encontrado com os filtros atuais.")
            return

        df_res = pd.DataFrame(self.results)
        top_syms = df_res['symbol'].value_counts().head(5)
        print("\n🔥 Ativos mais frequentes:")
        print(top_syms)
        
        avg_score = df_res['score'].mean()
        print(f"\n🎯 Score Médio dos Sinais: {avg_score:.1f}")
        print("="*40)

if __name__ == "__main__":
    # Exemplo de uso: python -m src.backtest_engine 2026-05-31
    import sys
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    bt = BasicBacktest(date_str)
    bt.run()