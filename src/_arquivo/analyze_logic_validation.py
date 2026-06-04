import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LogicValidator")

# Windows: tenta evitar UnicodeEncodeError (stdout stderr default cp1252).
import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

def load_paper_trades(path: Path):
    if not path.exists():
        return []
    trades = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            trades.append(json.loads(line))
    return trades

def run_validation(date_str: Optional[str] = None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    csv_path = Path(f"logs/history/snapshots_{date_str}.csv")
    paper_path = Path("logs/paper_closed.jsonl")

    if not csv_path.exists():
        print(f"❌ Erro: Arquivo de snapshot {csv_path} não encontrado.")
        return

    print("=" * 80)
    print(f"🔍 VALIDANDO LÓGICA SNIPER - DATA: {date_str}")
    print("=" * 80)

    # 1. Carregar Snapshots
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    df = df.sort_values(['symbol', 'timestamp'])

    # Calcular CVD Acumulado tratando os resets de 1min do DataEngine
    def get_cum_cvd(series):
        # CSV pode carregar colunas numéricas como str; forçamos float para evitar TypeError.
        cum, curr, last = [], 0.0, 0.0
        for v in series:
            try:
                v_f = float(v)
            except (TypeError, ValueError):
                v_f = 0.0

            if abs(v_f) < abs(last):
                curr += v_f  # Detectou reset (ou inversão brusca), soma o novo valor cheio
            else:
                curr += (v_f - last)  # Soma apenas a variação desde o último snapshot

            cum.append(curr)
            last = v_f

        return pd.Series(cum, index=series.index)
    df['cvd_cum'] = df.groupby('symbol', group_keys=False).apply(
        lambda g: get_cum_cvd(g['cvd_1m'])
    )
    
    # Calcular lsr_change_pct se não existir no CSV (retrocompatibilidade)
    if 'lsr_change_pct' not in df.columns:
        df['lsr_prev_5m'] = df.groupby('symbol')['lsr'].shift(30)
        df['lsr_change_pct'] = (df['lsr'] - df['lsr_prev_5m']) / df['lsr_prev_5m'].abs() * 100

    # 2. Ranking de exp_btc (Prioridade P1)
    print("\n💎 TOP 10 MOEDAS POR FORÇA RELATIVA MÉDIA (exp_btc):")
    # Remover BTCUSDT e BTCDOMUSDT do ranking de força relativa
    ranking_df = df[~df['symbol'].isin(['BTCUSDT', 'BTCDOMUSDT', 'ETHUSDT'])]
    avg_exp_btc = ranking_df.groupby('symbol')['exp_btc'].mean().sort_values(ascending=False)
    print(avg_exp_btc.head(10))

    # 3. Análise de Oportunidades Teóricas vs Reais
    # Vamos definir um critério "Squeeze" simplificado baseado no rastro
    # exp > 0.5 AND lsr < 1.0 AND exp_btc > 0
    print("\n🚀 ANALISANDO EFICIÊNCIA DE CAPTURA (Simulação de Squeeze):")
    
    # Filtros baseados no DNA
    theoretical_signals = df[
        (df['exp_btc'] > 0.5) & 
        (df['lsr'] < 1.0) & 
        (df['trades_1m'] > 10)
    ].copy()
    
    total_theoretical = len(theoretical_signals['symbol'].unique())
    print(f"- Ativos que apresentaram condições ideais hoje: {total_theoretical}")

    # 4. Cruzar com Paper Trades
    paper_trades = load_paper_trades(paper_path)
    # Filtrar trades apenas da data analisada
    start_ts = pd.Timestamp(date_str).timestamp()
    end_ts = start_ts + 86400
    daily_trades = [t for t in paper_trades if start_ts <= t['entry']['timestamp'] <= end_ts]

    print(f"- Trades efetivamente executados pelo Paper Tracker: {len(daily_trades)}")

    executed_symbols = {t['symbol'] for t in daily_trades}
    missed_symbols = set(theoretical_signals['symbol'].unique()) - executed_symbols

    if missed_symbols:
        print(f"\n⚠️ Oportunidades que o rastro pegou mas o Sniper NÃO atirou (Verificar Filtros):")
        for sym in list(missed_symbols)[:10]:
            print(f"  - {sym}")
        if len(missed_symbols) > 10:
            print(f"  ... e mais {len(missed_symbols)-10} ativos.")
    else:
        print("\n✅ Eficiência Máxima: Todas as moedas no rastro foram processadas!")

    # 5. Validação de Latência (Velocidade de Reação)
    if daily_trades:
        latencies = []
        for t in daily_trades:
            sym = t['symbol']
            entry_ts = t['entry']['timestamp']
            
            # Encontra o primeiro snapshot onde os critérios foram batidos para este símbolo
            first_seen = theoretical_signals[theoretical_signals['symbol'] == sym]
            if not first_seen.empty:
                # Converter Timestamp do pandas de volta para unix para cálculo
                snap_ts = first_seen.iloc[0]['timestamp'].timestamp()
                latency = entry_ts - snap_ts
                if latency >= 0:
                    latencies.append(latency)
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"\n⏱️ LATÊNCIA MÉDIA DE REAÇÃO (Snapshot -> Ordem): {avg_latency:.2f}s")
            print(f"  (Nota: Snapshots são a cada 10s, latência ideal < 20s)")

    # 6. Saúde do LSR
    print("\n📊 SAÚDE DO SENTIMENTO (LSR):")
    lsr_stats = df['lsr'].describe()
    print(f"- Média Global LSR: {lsr_stats['mean']:.2f}")
    low_lsr_count = len(df[df['lsr'] < 1.0])
    total_count = len(df)
    print(f"- Presença de Sentimento 'Vendedor' (Combustível): {(low_lsr_count/total_count)*100:.1f}% dos snapshots")

    # 8. Análise de Acumulação de CVD (DNA P3)
    print("\n📦 ANÁLISE DE ACUMULAÇÃO (CVD Cumulative):")
    acc_stats = []
    for symbol in theoretical_signals['symbol'].unique():
        sym_df = df[df['symbol'] == symbol]
        # Analisar a janela de 5 minutos antes de cada sinal teórico disparado hoje
        for sig_time in theoretical_signals[theoretical_signals['symbol'] == symbol]['timestamp']:
            window = sym_df[sym_df['timestamp'] <= sig_time].tail(30) # ~5 min de rastro
            if len(window) > 10:
                # Verificamos se o CVD Acumulado subiu na janela (Mais compra que venda)
                acc_stats.append(window['cvd_cum'].iloc[-1] > window['cvd_cum'].iloc[0])
            
    if acc_stats:
        pos_rate = (sum(acc_stats) / len(acc_stats)) * 100
        print(f"- Sinais com acumulação de compra nos 5min pré-ignição: {pos_rate:.1f}%")
        if pos_rate > 70:
            print("  ✅ Confirmado: O rastro de compra institucional precede as explosões de preço.")
        else:
            print("  ⚠️ Alerta: Muitos sinais disparando sem acumulação clara (possível volatilidade vazia).")

    # 9. Análise de Acumulação de OI (DNA P1)
    print("\n💰 ANÁLISE DE ACUMULAÇÃO DE OI (Open Interest):")
    oi_acc_stats = []
    for symbol in theoretical_signals['symbol'].unique():
        sym_df = df[df['symbol'] == symbol]
        # Analisar a janela de 5 minutos antes de cada sinal teórico
        for sig_time in theoretical_signals[theoretical_signals['symbol'] == symbol]['timestamp']:
            window = sym_df[sym_df['timestamp'] <= sig_time].tail(30) # ~5 min
            if len(window) > 10:
                # Verificamos se o OI subiu na janela (Dinheiro novo entrando)
                oi_acc_stats.append(window['oi'].iloc[-1] > window['oi'].iloc[0])
            
    if oi_acc_stats:
        oi_pos_rate = (sum(oi_acc_stats) / len(oi_acc_stats)) * 100
        print(f"- Sinais com entrada de dinheiro novo (OI) nos 5min pré-ignição: {oi_pos_rate:.1f}%")
        if oi_pos_rate > 70:
            print("  ✅ Confirmado: O interesse aberto cresce antes da ignição, validando entrada de capital.")
        else:
            print("  ⚠️ Alerta: Muitos sinais ocorrendo com OI estável ou caindo (pode indicar apenas fechamento de posições).")

    # 10. Correlação Win Rate vs exp_btc
    if daily_trades:
        print("\n📈 CORRELAÇÃO: FORÇA RELATIVA (exp_btc) vs WIN RATE:")
        correlation_data = []
        for t in daily_trades:
            # Tenta pegar do sinal salvo, se não encontrar (trades antigos), busca no snapshot mais próximo
            exp_btc_val = t['entry'].get('signal', {}).get('exp_btc')
            
            if exp_btc_val is None:
                sym_df = df[df['symbol'] == t['symbol']]
                if not sym_df.empty:
                    # Busca o snapshot mais próximo do timestamp de entrada
                    entry_dt = pd.to_datetime(t['entry']['timestamp'], unit='s')
                    idx = (sym_df['timestamp'] - entry_dt).abs().idxmin()
                    exp_btc_val = sym_df.loc[idx, 'exp_btc']
            
            if exp_btc_val is not None:
                correlation_data.append({
                    'symbol': t['symbol'],
                    'win': 1 if t['quality']['win'] else 0,
                    'exp_btc': exp_btc_val
                })
        
        if correlation_data:
            tdf = pd.DataFrame(correlation_data)
            bins = [-float('inf'), 0.5, 1.5, float('inf')]
            labels = ['Fraco (< 0.5)', 'Médio (0.5 - 1.5)', 'Forte (> 1.5)']
            tdf['bucket'] = pd.cut(tdf['exp_btc'], bins=bins, labels=labels)
            
            corr_report = tdf.groupby('bucket', observed=True)['win'].agg(['count', 'mean'])
            for bucket, row in corr_report.iterrows():
                win_rate = row['mean'] * 100
                print(f"- {bucket:20} | Trades: {row['count']:3.0f} | Win Rate: {win_rate:5.1f}%")
                
                # Identifica quais moedas performaram melhor nesta categoria
                bucket_data = tdf[tdf['bucket'] == bucket]
                if not bucket_data.empty:
                    best_syms = bucket_data.groupby('symbol')['win'].agg(['count', 'mean']).sort_values(by=['mean', 'count'], ascending=False)
                    top_3 = [f"{s} ({r['mean']*100:.0f}%)" for s, r in best_syms.head(3).iterrows()]
                    print(f"    🚀 Melhores ativos: {', '.join(top_3)}")

    # 11. Correlação: LSR Change % vs Velocidade de Take Profit (Duração)
    if daily_trades:
        print("\n⏱️ CORRELAÇÃO: LSR CHANGE % vs VELOCIDADE DE TAKE PROFIT (WINS):")
        tp_data = []
        for t in daily_trades:
            # Focamos em trades vencedores para medir a velocidade do lucro
            if not t['quality']['win']:
                continue
            
            duration = t['live'].get('duration_sec')
            lsr_chg = t['entry'].get('signal', {}).get('lsr_change_pct')
            
            if lsr_chg is None:
                sym_df = df[df['symbol'] == t['symbol']]
                if not sym_df.empty:
                    entry_dt = pd.to_datetime(t['entry']['timestamp'], unit='s')
                    idx = (sym_df['timestamp'] - entry_dt).abs().idxmin()
                    lsr_chg = sym_df.loc[idx, 'lsr_change_pct']
            
            if lsr_chg is not None and duration is not None:
                tp_data.append({'lsr_chg': lsr_chg, 'duration': duration})
        
        if tp_data:
            tdf = pd.DataFrame(tp_data)
            bins = [-float('inf'), -5, -2, 0, float('inf')]
            labels = ['Forte Queda (< -5%)', 'Queda Média (-5% a -2%)', 'Queda Leve (-2% a 0%)', 'Estável/Subida (> 0%)']
            tdf['lsr_bucket'] = pd.cut(tdf['lsr_chg'], bins=bins, labels=labels)
            
            dur_report = tdf.groupby('lsr_bucket', observed=True)['duration'].agg(['count', 'mean', 'min'])
            for bucket, row in dur_report.iterrows():
                print(f"- {bucket:25} | Trades: {row['count']:3.0f} | Duração Média: {row['mean']:6.1f}s (Min: {row['min']:.0f}s)")

    # 7. Conclusão da Lógica
    print("\n🏁 VEREDITO DE ROBUSTEZ:")
    if len(daily_trades) > 0:
        wins = [t for t in daily_trades if t['quality']['win']]
        win_rate = (len(wins) / len(daily_trades)) * 100
        if win_rate > 50 and avg_exp_btc.mean() > 0:
            print("✅ LÓGICA VALIDADA: O cruzamento de força relativa e rastro institucional está gerando lucro.")
        else:
            print("🟡 LÓGICA EM OBSERVAÇÃO: Ajuste os thresholds de LSR e OI Change para filtrar ruído.")
    else:
        print("⚪ DADOS INSUFICIENTES: Aguarde mais trades para validação estatística.")
    
    print("=" * 80)

if __name__ == "__main__":
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    run_validation(target_date)
