import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import os
import sys

try:
    stdout_reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(stdout_reconfigure):
        stdout_reconfigure(encoding="utf-8")
    stderr_reconfigure = getattr(sys.stderr, "reconfigure", None)
    if callable(stdout_reconfigure):
        stderr_reconfigure(encoding="utf-8")
except Exception:
    pass

def run_advanced_audit():
    closed_path = Path("logs/paper_closed.jsonl")
    refusals_path = Path("logs/signal_refusals.jsonl")
    trades = []
    df = pd.DataFrame()

    print("="*60)
    print(f"🧠 AUDITORIA DE INTELIGÊNCIA ESTRATÉGICA - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    # --- 1. ANÁLISE DE ALPHA DECAY (O que aconteceu depois da venda?) ---
    if closed_path.exists():
        with open(closed_path, "r", encoding="utf-8") as f:
            for line in f:
                try: trades.append(json.loads(line))
                except: continue
        
        if trades:
            df = pd.json_normalize(trades)
            
            # Extrai performance pós-venda
            # Verificamos os campos post_trade.snapshots.5m.pct, etc.
            decay_cols = [c for c in df.columns if 'post_trade.snapshots' in c and '.pct' in c]
            
            print("\n📈 ANÁLISE DE SAÍDA (Alpha Decay):")
            early_exits = 0
            total_with_decay = 0
            
            for _, row in df.iterrows():
                # Pega o maior lucro atingido após a saída (em até 60 min)
                post_performance = []
                for col in decay_cols:
                    val = row.get(col)
                    if pd.notna(val) is True: post_performance.append(val)
                
                if post_performance:
                    total_with_decay += 1
                    max_post = max(post_performance)
                    if max_post > 3.0: # Se subiu mais de 3% após sairmos
                        early_exits += 1
            
            if total_with_decay > 0:
                leakage_rate = early_exits / total_with_decay
                print(f"- Taxa de 'Mão de Alface' (Subiu >3% após sair): {leakage_rate:.2%}")
                if leakage_rate > 0.4:
                    print("👉 ALERTA: O bot está saindo muito cedo. Considere aumentar o TP ou alargar o Trailing.")
                else:
                    print("✅ As saídas parecem estar capturando bem o topo do movimento.")

    # --- 2. ANÁLISE DE RECUSAS (Por que não entramos?) ---
    if refusals_path.exists():
        refusals = []
        with open(refusals_path, "r", encoding="utf-8") as f:
            for line in f:
                try: refusals.append(json.loads(line))
                except: continue
        
        if refusals:
            ref_df = pd.DataFrame(refusals)
            print("\n🛡️ ANÁLISE DE FILTROS (Recusas):")
            top_reasons = ref_df['reason_code'].value_counts().head(5)
            print("Top motivos de bloqueio:")
            for reason, count in top_reasons.items():
                print(f" - {reason}: {count} vezes")
            
            # Especial para o seu caso de hoje (Duplicidade/Telegram)
            if 'cooldown_active' in ref_df['reason_code'].values:
                print(f"ℹ️ Filtro de Cooldown barrou {len(ref_df[ref_df['reason_code']=='cooldown_active'])} entradas repetidas.")

    # --- 3. AUDITORIA DE DUPLICIDADE (O problema do Telegram) ---
    if closed_path.exists() and trades:
        print("\n🚨 AUDITORIA DE SAÚDE DO PIPELINE (Duplicidade):")
        # Verifica trades do mesmo símbolo com entrada no mesmo segundo
        df['entry_ts_int'] = df['entry.time'].astype(int)
        dups = df[df.duplicated(subset=['symbol', 'entry_ts_int'], keep=False)]
        
        if not dups.empty:
            print(f"❌ DETECTADO: {len(dups)} trades duplicados no log!")
            print("Isso explica o spam no Telegram. O bot está processando o mesmo sinal múltiplas vezes.")
            print("Causa provável: Race condition no loop de trading.")
        else:
            print("✅ Nenhuma duplicidade de execução detectada nos registros fechados.")

    # --- 4. QUALIDADE DO SQUEEZE (CVD vs PnL) ---
    if trades:
        print("\n💎 CORRELAÇÃO DNA SNIPER:")
        # Analisando se trades com CVD positivo realmente performam melhor
        cvd_col = 'entry.signal.cvd_1m' if 'entry.signal.cvd_1m' in df.columns else 'entry.metrics.cvd_1m'
        if cvd_col in df.columns:
            cvd_pos = df[df[cvd_col] > 0]['exit.pnl_pct'].mean()
            cvd_neg = df[df[cvd_col] <= 0]['exit.pnl_pct'].mean()
            
            print(f"- PnL Médio com CVD Positivo: {cvd_pos:.2f}%")
            print(f"- PnL Médio com CVD Negativo: {cvd_neg:.2f}%")
            
            if cvd_neg < cvd_pos:
                print("👉 CONCLUSÃO: O DNA não mente. Trades com CVD negativo estão puxando sua média para baixo.")
        else:
            print("⚠️ Campo CVD não encontrado nos dados de entrada")

    print("="*60)

if __name__ == "__main__":
    run_advanced_audit()