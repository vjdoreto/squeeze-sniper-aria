import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

def run_deep_audit():
    # SPRINT 6.41: Auditoria Híbrida (Histórico + Trades Abertos)
    closed_path = Path("logs/paper_closed.jsonl")
    state_path = Path("logs/paper_opportunities.json")
    
    trades = []

    # 1. Carrega Histórico de Trades Fechados
    if closed_path.exists():
        with open(closed_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    trades.append(json.loads(line))
                except: continue

    # 2. Carrega Estado Atual (para pegar os OPEN)
    if state_path.exists():
        try:
            state_data = json.loads(state_path.read_text(encoding="utf-8"))
            open_trades = state_data.get("open", [])
            # Evita duplicatas se o arquivo JSON também tiver trades recém-fechados
            known_ids = {t["id"] for t in trades}
            for ot in open_trades:
                if ot["id"] not in known_ids:
                    trades.append(ot)
        except Exception as e:
            print(f"⚠️ Erro ao ler paper_opportunities.json: {e}")

    if not trades:
        print("⚪ Nenhum trade para analisar.")
        return

    # Achatamento dos dados para análise tabular
    df_list = []
    for t in trades:
        entry = t.get("entry", {})
        sig = entry.get("signal", {})
        
        is_open = t.get("status") == "open"
        exit_data = t.get("exit") or {}
        live_data = t.get("live") or {}
        pnl_pct = live_data.get("pnl_pct", 0) if is_open else exit_data.get("pnl_pct", 0)
        pnl_usdt = live_data.get("pnl_usdt", 0) if is_open else exit_data.get("pnl_usdt", 0)

        # SPRINT 11.45: Filtro de Alucinação (Exclui trades com > 20% PnL ou PnL USDT impossível)
        if abs(pnl_pct) > 20.0 or abs(pnl_usdt) > 1000:
            continue

        qual = t.get("quality", {})
        
        df_list.append({
            "symbol": t["symbol"],
            "status": t.get("status", "closed"),
            "score": sig.get("score") or calculate_manual_score(entry.get("metrics", {})),
            "pnl_pct": pnl_pct,
            "pnl_usdt": pnl_usdt,
            "reason": "OPEN (Floating)" if is_open else exit_data.get("reason"),
            "mfe": qual.get("mfe_pct", 0),
            "mae": qual.get("mae_pct", 0),
            "duration": (time.time() - entry.get("time", 0)) / 60 if is_open else (exit_data.get("time", 0) - entry.get("time", 0)) / 60,
            "pc_24h": entry.get("metrics", {}).get("price_change_24h", 0)
        })

    df = pd.DataFrame(df_list)
    
    print("="*60)
    print(f"📊 AUDITORIA PROFUNDA: {len(df)} TRADES ANALISADOS")
    print("="*60)

    # 1. Performance por Faixa de Score (Descobrir o threshold ideal)
    df['score_bin'] = pd.cut(df['score'].fillna(0), bins=[-1, 50, 70, 85, 95, 100], labels=['0-50', '51-70', '71-85', '86-95', '96-100'])
    
    score_perf = df.groupby('score_bin', observed=False).agg({
        'pnl_pct': 'mean',
        'symbol': 'count',
        'mfe': 'mean'
    }).rename(columns={'symbol': 'qtd', 'pnl_pct': 'Avg PnL%', 'mfe': 'Avg MFE%'})
    
    print("\n📈 PERFORMANCE POR TIER DE SCORE:")
    print(score_perf)

    # 2. O "Cemitério" do Break-even (Análise de enforcamento de trade)
    # Filtramos apenas os fechados para análise de gestão
    closed_df = df[df['status'] == 'closed']
    lucky_escapes = len(closed_df[(closed_df['reason'] == 'stop_loss') & (closed_df['pnl_pct'] > -0.5) & (closed_df['mfe'] > 1.5)])
    open_count = len(df[df['status'] == 'open'])
    
    print("\n🛡️ ANÁLISE DE GESTÃO DE RISCO:")
    print(f"- Posições atualmente ABERTAS: {open_count}")
    print(f"- Trades que atingiram >1.5% de lucro mas voltaram para o Zero: {lucky_escapes}")
    print(f"- Se esses trades tivessem pego 2%, o lucro extra seria: ${lucky_escapes * 1.5:.2f}")

    # 3. Influência do Bias 24h (Crucial para lucratividade)
    bias_pos = df[df['pc_24h'] > 0]['pnl_pct'].mean()
    bias_neg = df[df['pc_24h'] < 0]['pnl_pct'].mean()
    
    print("\n🧭 BIAS DE TENDÊNCIA (Variação 24h):")
    print(f"- Avg PnL em moedas VERDES (24h% > 0): {bias_pos:.3f}%")
    print(f"- Avg PnL em moedas VERMELHAS (24h% < 0): {bias_neg:.3f}%")

    # 4. Auditoria de Ativos
    best_assets = df.groupby('symbol')['pnl_usdt'].sum().sort_values(ascending=False).head(5)
    worst_assets = df.groupby('symbol')['pnl_usdt'].sum().sort_values(ascending=False).tail(5)
    
    print("\n🏆 TOP 5 ATIVOS (Melhor lucro):")
    print(best_assets)
    print("\n💀 BOTTOM 5 ATIVOS (Candidatos a Blacklist):")
    print(worst_assets)
    print("="*60)

def calculate_manual_score(m):
    # Fallback caso o score não tenha sido salvo no log por algum motivo
    s = 0
    if (m.get("oi_change_pct:5m") or 0) > 0.5: s += 20
    if (m.get("lsr_change_pct:5m") or 0) < -1: s += 20
    if (m.get("exp:5m") or 0) > 0.02: s += 20
    return s

if __name__ == "__main__":
    run_deep_audit()