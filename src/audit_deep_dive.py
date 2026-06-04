import json
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

try:
    stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(stdout_reconfigure):
        stdout_reconfigure(encoding="utf-8")
    stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(stderr_reconfigure):
        stderr_reconfigure(encoding="utf-8")
except Exception:
    pass

def run_deep_audit(closed_path: str = "logs/paper_closed.jsonl"):
    path = Path(closed_path)
    if not path.exists():
        print(f"❌ Arquivo {closed_path} não encontrado.")
        return

    trades = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except:
                continue

    if not trades:
        print("⚠️ Nenhum trade para analisar.")
        return

    df = pd.json_normalize(trades)
    
    # 1. Análise de Duplicidade (Trades no mesmo minuto)
    df['entry_time'] = pd.to_datetime(df['entry.time'], unit='s')
    dups = df[df.duplicated(subset=['symbol', 'entry_time'], keep=False)]
    
    # 2. Eficiência de Saída (Captura de Lucro)
    # Quanto do MFE nós realmente realizamos?
    df['capture_efficiency'] = df['exit.pnl_pct'] / df['quality.mfe_pct']
    
    # 3. Identificação de "Slippage Fantasma"
    # Trades onde o PnL foi muito pior que o SL configurado
    df['sl_violation'] = df.apply(lambda x: x['exit.pnl_pct'] < (x.get('targets.sl_pct', 0.02) * 100 * -1.5), axis=1)

    print("="*50)
    print(f"📊 AUDITORIA PROFUNDA SQUEEZESNIPER - {datetime.now()}")
    print("="*50)
    print(f"Total de Trades Analisados: {len(df)}")
    print(f"Win Rate Real: {(df['exit.pnl_pct'] > 0).mean():.2%}")
    print(f"PnL Médio: {df['exit.pnl_pct'].mean():.2f}%")
    print(f"MFE Médio: {df['quality.mfe_pct'].mean():.2f}%")
    print(f"MAE Médio: {df['quality.mae_pct'].mean():.2f}%")
    print("-"*50)
    
    print(f"🚨 Trades Duplicados Detectados: {len(dups)}")
    if not dups.empty:
        print(dups[['symbol', 'entry_time', 'exit.pnl_pct']])

    print("-"*50)
    print(f"📉 Violações de Stop Loss (Slippage Crítico): {df['sl_violation'].sum()}")
    bad_exits = df[df['sl_violation']]
    if not bad_exits.empty:
        print(bad_exits[['symbol', 'exit.pnl_pct', 'quality.mfe_pct', 'exit.reason']])

    print("-"*50)
    print("💡 CONCLUSÃO DO ENGENHEIRO:")
    avg_capture = df[df['exit.pnl_pct'] > 0]['capture_efficiency'].mean()
    print(f"Eficiência de Captura nos vencedores: {avg_capture:.2%}")
    
    if avg_capture < 0.3:
        print("👉 O Trailing Stop está muito 'apertado'. Você está devolvendo 70% do lucro antes de sair.")
    
    giveback_trades = df[(df['quality.mfe_pct'] > 5) & (df['exit.pnl_pct'] < 0)]
    print(f"Trades que foram 'Ganhadores' (>5% MFE) e viraram 'Perdedores': {len(giveback_trades)}")
    if not giveback_trades.empty:
        print("Ativos Críticos (Giveback):", list(set(giveback_trades['symbol'])))

    print("="*50)

if __name__ == "__main__":
    # Analisa tanto o paper quanto o live se existirem
    print("Analisando PAPER...")
    run_deep_audit("logs/paper_closed.jsonl")
    print("\nAnalisando LIVE...")
    run_deep_audit("logs/live_closed.jsonl")