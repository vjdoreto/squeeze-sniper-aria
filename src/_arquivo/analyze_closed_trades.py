
import json
from pathlib import Path
from collections import defaultdict

def analyze_closed_trades():
    paper_path = Path("logs/paper_opportunities.json")
    
    if not paper_path.exists():
        print("Arquivo paper_opportunities.json não encontrado!")
        return

    with open(paper_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    closed = data.get("closed", [])
    open_trades = data.get("open", [])
    
    print("=" * 80)
    print(f"📊 ANÁLISE DETALHADA DOS TRADES DE PAPER")
    print("=" * 80)
    print(f"Total de trades fechados: {len(closed)}")
    print(f"Total de trades abertos: {len(open_trades)}")
    print()

    wins = []
    losses = []
    
    for t in closed:
        exit_data = t.get("exit", {})
        pnl = exit_data.get("pnl_pct", 0)
        if pnl >= 0:
            wins.append(t)
        else:
            losses.append(t)
    
    print(f"Vitórias: {len(wins)}")
    print(f"Derrotas: {len(losses)}")
    win_rate = (len(wins) / len(closed)) * 100 if closed else 0.0
    print(f"Win rate: {win_rate:.1f}%")
    print()

    print("-" * 80)
    print("🔍 ANÁLISE DOS TRADES VENCEDORES:")
    print("-" * 80)
    i = 1
    for t in wins:
        print(f"\nTRADE VENCEDOR {i}: {t['symbol']}")
        i +=1
        entry = t.get('entry', {})
        signal = entry.get('signal', {})
        metrics = entry.get('metrics', {})
        print(f"  PnL: {t.get('exit', {}).get('pnl_pct', 0):.2f}%")
        print(f"  exp: {signal.get('exp', 'N/A'):.4f}")
        print(f"  oi_trend: {signal.get('oi_trend', 'N/A'):.4f}")
        print(f"  lsr_trend: {signal.get('lsr_trend', 'N/A'):.4f}")
        print(f"  trades_1m: {metrics.get('trades_1m', 'N/A'):.0f}")
        print(f"  cvd_1m: {metrics.get('cvd_1m', 'N/A')}")
        print(f"  lsr: {metrics.get('lsr', 'N/A'):.4f}")

    print()
    print("-" * 80)
    print("🔍 ANÁLISE DOS TRADES PERDEDORES:")
    print("-" * 80)
    i = 1
    for t in losses:
        print(f"\nTRADE PERDEDOR {i}: {t['symbol']}")
        i += 1
        entry = t.get('entry', {})
        signal = entry.get('signal', {})
        metrics = entry.get('metrics', {})
        print(f"  PnL: {t.get('exit', {}).get('pnl_pct', 0):.2f}%")
        print(f"  exp: {signal.get('exp', 'N/A'):.4f}")
        print(f"  oi_trend: {signal.get('oi_trend', 'N/A'):.4f}")
        print(f"  lsr_trend: {signal.get('lsr_trend', 'N/A'):.4f}")
        print(f"  trades_1m: {metrics.get('trades_1m', 'N/A'):.0f}")
        print(f"  cvd_1m: {metrics.get('cvd_1m', 'N/A')}")
        print(f"  lsr: {metrics.get('lsr', 'N/A'):.4f}")

    print()
    print("=" * 80)
    print("📌 PRINCIPAIS PROBLEMAS IDENTIFICADOS:")
    print("=" * 80)
    print()
    
    # 1. Problema: Muitos trades com lsr_trend = 0
    zero_lsr_trades = [t for t in closed if t.get('entry', {}).get('signal', {}).get('lsr_trend') == 0]
    if zero_lsr_trades:
        print(f"1. ❌ {len(zero_lsr_trades)} trades com lsr_trend = 0 (LSR NÃO ESTAVA CAINDO!)")
        for t in zero_lsr_trades[:5]:
            print(f"   - {t['symbol']}")

    # 2. Problema: Trades com trades_1m muito baixo
    low_trades_trades = [t for t in closed if t.get('entry', {}).get('metrics', {}).get('trades_1m', 0) < 10]
    if low_trades_trades:
        print()
        print(f"2. ❌ {len(low_trades_trades)} trades com trades_1m < 10 (baixa atividade de mercado!")
        for t in low_trades_trades[:5]:
            print(f"   - {t['symbol']}: {t.get('entry', {}).get('metrics', {}).get('trades_1m', 0)}")

    # 3. Problema: Trades com exp baixo
    low_exp_trades = [t for t in closed if t.get('entry', {}).get('signal', {}).get('exp', 0) < 2]
    if low_exp_trades:
        print()
        print(f"3. ❌ {len(low_exp_trades)} trades com exp < 2 (baixo momentum!")
        for t in low_exp_trades[:5]:
            print(f"   - {t['symbol']}: {t.get('entry', {}).get('signal', {}).get('exp', 0):.4f}")

    print()
    print("=" * 80)
    print("💡 SUGESTÕES DE MELHORIA:")
    print("=" * 80)
    print("1. Aumentar min_exp para 2.0 (capturar apenas trades com momentum extremo")
    print("2. Aumentar min_trades_1m para 15")
    print("3. Garantir que lsr_trend < -0.1 (não aceitar lsr_trend = 0)")
    print("4. Aumentar cvd_streak_min para 4")
    print()

if __name__ == "__main__":
    analyze_closed_trades()
