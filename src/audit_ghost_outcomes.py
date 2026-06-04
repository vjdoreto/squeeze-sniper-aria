import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional
import sys

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GhostAuditor")

def audit_refusals(date_str: Optional[str] = None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    refusals_path = Path("logs/signal_refusals.jsonl")
    history_path = Path(f"logs/history/snapshots_{date_str}.csv")
    prefs_path = Path("preferences.json")

    if not refusals_path.exists() or not history_path.exists():
        print(f"❌ Dados insuficientes para auditoria na data {date_str}.")
        print(f"Verifique se {refusals_path} e {history_path} existem.")
        return

    # 1. Carrega configurações para simular SL/TP (Nova estrutura harmonizada)
    with open(prefs_path, "r", encoding="utf-8") as f:
        prefs = json.load(f)
        # Usa Paper como padrão (pode ser ajustado para Live se necessário)
        mode = prefs.get("trading_mode", "paper")
        tp_pct = prefs[mode]["execution"]["tp_pct"]
        sl_pct = prefs[mode]["execution"]["sl_pct"]

    # 2. Carrega Snapshots de Preço (O "Futuro" para o sinal ignorado)
    df_history = pd.read_csv(history_path)
    df_history['timestamp'] = pd.to_datetime(df_history['timestamp'], unit='s')

    # 3. Carrega Recusas (O "Passado")
    refusals = []
    with open(refusals_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                ref_dt = datetime.fromtimestamp(data['ts'])
                if ref_dt.strftime("%Y-%m-%d") == date_str:
                    refusals.append(data)
            except: continue

    if not refusals:
        print(f"⚪ Nenhuma recusa encontrada no log para a data {date_str}.")
        return

    print("="*80)
    print(f"🕵️ AUDITORIA DE FALSOS NEGATIVOS (RECUSAS) - DATA: {date_str}")
    print(f"Simulando desfecho com TP: {tp_pct*100}% | SL: {sl_pct*100}%")
    print("="*80)

    results = []
    for ref in refusals:
        symbol = ref['symbol']
        ts_ref = datetime.fromtimestamp(ref['ts'])
        entry_price = ref.get('price') or ref.get('details', {}).get('price')
        
        if not entry_price: continue

        # Busca o futuro do ativo (próximos 60 minutos após a recusa)
        future = df_history[
            (df_history['symbol'] == symbol) & 
            (df_history['timestamp'] > ts_ref) &
            (df_history['timestamp'] <= ts_ref + pd.Timedelta(minutes=60))
        ]

        if future.empty: continue

        target_tp = entry_price * (1 + tp_pct)
        target_sl = entry_price * (1 - sl_pct)
        
        outcome = "HOLDING/LIMIT"
        for _, row in future.iterrows():
            if row['price'] >= target_tp:
                outcome = "WINNER (Missed Opportunity)"
                break
            if row['price'] <= target_sl:
                outcome = "LOSER (Correct Block)"
                break
        
        results.append({
            "reason": ref['reason_code'],
            "outcome": outcome,
            "symbol": symbol
        })

    df_res = pd.DataFrame(results)
    if df_res.empty:
        print("⚪ Nenhuma correspondência encontrada nos snapshots para as recusas.")
        return

    # 4. Relatório de Eficiência por Motivo
    summary = df_res.groupby(['reason', 'outcome'], observed=False).size().unstack(fill_value=0)
    
    print("\n📊 ANÁLISE DE EFICIÊNCIA DOS FILTROS (DNA vs REALIDADE):")
    print(summary)

    # Cálculo de métrica de governança
    correct_blocks = len(df_res[df_res['outcome'] == "LOSER (Correct Block)"])
    missed_winners = len(df_res[df_res['outcome'] == "WINNER (Missed Opportunity)"])
    
    total_resolved = correct_blocks + missed_winners
    efficiency = (correct_blocks / total_resolved) * 100 if total_resolved > 0 else 0

    print("\n" + "-"*40)
    print(f"🎯 SCORE DE PRECISÃO DOS BLOQUEIOS: {efficiency:.2f}%")
    print(f"- Bloqueios que salvaram capital: {correct_blocks}")
    print(f"- Bloqueios que perderam lucro (Falsos Negativos): {missed_winners}")
    print("-"*40)

    if efficiency > 70:
        print("✅ CONCLUÍDO: Seus filtros estão protegendo seu capital com alta precisão.")
    elif efficiency < 40 and total_resolved > 5:
        print("⚠️ ALERTA: O bot está desprezando muitos sinais lucrativos. Avalie relaxar os thresholds.")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    audit_refusals(target)