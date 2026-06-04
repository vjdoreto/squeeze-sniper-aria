#!/usr/bin/env python3
"""Análise de Leaks de Performance - SqueezeSniper v4.2.4"""
import json
from pathlib import Path
from typing import List, Dict

def analyze_leaks():
    """Analisa leaks de performance nos trades fechados"""
    
    paper_file = Path("logs/paper_closed.jsonl")
    if not paper_file.exists():
        print("Arquivo paper_closed.jsonl não encontrado")
        return
    
    trades: List[Dict] = []
    with open(paper_file, encoding="utf-8") as f:
        for line in f:
            try:
                trades.append(json.loads(line))
            except:
                continue
    
    if not trades:
        print("Nenhum trade encontrado")
        return
    
    print("=" * 80)
    print("ANÁLISE DE LEAKS - SQUEEZESNIPER V4.2.4")
    print("=" * 80)
    print(f"\nTotal de Trades: {len(trades)}")
    
    # Métricas Gerais
    total_pnl = sum(t.get("exit", {}).get("pnl_usdt", 0) for t in trades)
    total_fees = sum(t.get("exit", {}).get("total_fees", 0) for t in trades)
    avg_margin = sum(t.get("entry", {}).get("margin_usdt", 0) for t in trades) / len(trades)
    avg_duration = sum(t.get("exit", {}).get("duration_seconds", 0) for t in trades) / len(trades)
    
    wins = [t for t in trades if t.get("exit", {}).get("pnl_usdt", 0) > 0]
    losses = [t for t in trades if t.get("exit", {}).get("pnl_usdt", 0) <= 0]
    
    print(f"\n[METRICAS GERAIS]")
    print(f"  - Total PnL: ${total_pnl:.2f} USDT")
    print(f"  - Total Fees: ${total_fees:.2f} USDT")
    print(f"  - PnL Liquido: ${total_pnl - total_fees:.2f} USDT")
    print(f"  - Win Rate: {len(wins)/len(trades)*100:.1f}% ({len(wins)}W/{len(losses)}L)")
    print(f"  - Margem Media: ${avg_margin:.2f} USDT")
    print(f"  - Duracao Media: {avg_duration/60:.1f} minutos")
    
    # LEAK 1: Margem Muito Baixa
    print(f"\n[LEAK #1: MARGEM MUITO BAIXA]")
    print(f"  - Margem Media: ${avg_margin:.2f} (Esperado: ~$50 com risco 5%)")
    print(f"  - Impacto: Fees proporcionalmente altos, lucros insignificantes")
    
    # LEAK 2: Trailing Stop Prematuro
    trailing_trades = [t for t in trades if t.get("exit", {}).get("reason") == "trailing_stop"]
    avg_mfe_trailing = sum(t.get("quality", {}).get("mfe_pct", 0) for t in trailing_trades) / len(trailing_trades) if trailing_trades else 0
    avg_pnl_trailing = sum(t.get("exit", {}).get("pnl_pct", 0) for t in trailing_trades) / len(trailing_trades) if trailing_trades else 0
    
    print(f"\n[LEAK #2: TRAILING STOP PREMATURO]")
    print(f"  - Trades com Trailing: {len(trailing_trades)}/{len(trades)} ({len(trailing_trades)/len(trades)*100:.1f}%)")
    print(f"  - MFE Medio: {avg_mfe_trailing:.2f}%")
    print(f"  - PnL Medio: {avg_pnl_trailing:.2f}%")
    print(f"  - Captura: {(avg_pnl_trailing/avg_mfe_trailing*100) if avg_mfe_trailing > 0 else 0:.1f}%")
    
    # LEAK 3: Trades Muito Curtos
    short_trades = [t for t in trades if t.get("exit", {}).get("duration_seconds", 0) < 120]
    print(f"\n[LEAK #3: TRADES MUITO CURTOS (<2min)]")
    print(f"  - Quantidade: {len(short_trades)}/{len(trades)} ({len(short_trades)/len(trades)*100:.1f}%)")
    print(f"  - PnL Medio: {sum(t.get('exit', {}).get('pnl_usdt', 0) for t in short_trades) / len(short_trades) if short_trades else 0:.2f} USDT")
    print(f"  - Fees Medio: ${sum(t.get('exit', {}).get('total_fees', 0) for t in short_trades) / len(short_trades) if short_trades else 0:.2f}")
    
    # LEAK 4: Relação Risco/Recompensa
    print(f"\n[LEAK #4: RELACAO RISCO/RECOMPENSA]")
    avg_win = sum(t.get("exit", {}).get("pnl_usdt", 0) for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.get("exit", {}).get("pnl_usdt", 0) for t in losses) / len(losses)) if losses else 0
    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    
    print(f"  - Win Medio: ${avg_win:.2f}")
    print(f"  - Loss Medio: ${avg_loss:.2f}")
    print(f"  - R:R Ratio: {rr_ratio:.2f}:1 (Ideal: >2:1)")
    
    # LEAK 5: Fees vs PnL
    print(f"\n[LEAK #5: FEES COMENDO LUCROS]")
    fee_ratio = (total_fees / abs(total_pnl)) * 100 if total_pnl != 0 else 0
    print(f"  - Fees/PnL: {fee_ratio:.1f}%")
    print(f"  - Impacto: Fees de ${total_fees:.2f} em PnL de ${total_pnl:.2f}")
    
    # Análise por Símbolo
    print(f"\n[TOP 5 PIORES PERFORMERS]")
    symbol_pnl = {}
    for t in trades:
        sym = t.get("symbol", "UNKNOWN")
        pnl = t.get("exit", {}).get("pnl_usdt", 0)
        if sym not in symbol_pnl:
            symbol_pnl[sym] = []
        symbol_pnl[sym].append(pnl)
    
    worst = sorted(symbol_pnl.items(), key=lambda x: sum(x[1]))[:5]
    for sym, pnls in worst:
        print(f"  - {sym}: ${sum(pnls):.2f} ({len(pnls)} trades)")
    
    # Recomendações
    print(f"\n" + "=" * 80)
    print("[RECOMENDACOES CRITICAS]")
    print("=" * 80)
    
    print(f"\n1. AUMENTAR MARGEM POR TRADE:")
    print(f"   • Atual: ${avg_margin:.2f}")
    print(f"   • Recomendado: $50 (5% de $1000)")
    print(f"   • Ação: Ajustar 'margin_pct' ou 'base_margin_usdt' em preferences.json")
    
    print(f"\n2. AJUSTAR TRAILING STOP:")
    print(f"   • Problema: Captura apenas {(avg_pnl_trailing/avg_mfe_trailing*100) if avg_mfe_trailing > 0 else 0:.1f}% do MFE")
    print(f"   • Recomendado: Aumentar 'trailing_stop_callback' de 60% para 75-80%")
    print(f"   • Ação: Ajustar em preferences.json paper.execution.trailing_stop_callback")
    
    print(f"\n3. FILTRAR TRADES MUITO CURTOS:")
    print(f"   • Problema: {len(short_trades)/len(trades)*100:.1f}% dos trades <2min")
    print(f"   • Recomendado: Adicionar 'min_hold_seconds': 120")
    print(f"   • Ação: Adicionar em preferences.json paper.execution")
    
    print(f"\n4. MELHORAR R:R RATIO:")
    print(f"   • Atual: {rr_ratio:.2f}:1")
    print(f"   • Recomendado: >2:1")
    print(f"   • Ação: Aumentar TP ou reduzir SL, ou ambos")
    
    print(f"\n5. REDUZIR IMPACTO DE FEES:")
    print(f"   • Problema: Fees representam {fee_ratio:.1f}% do PnL")
    print(f"   • Solução: Aumentar margem + reduzir frequência de trades")
    
    print(f"\n" + "=" * 80)

if __name__ == "__main__":
    analyze_leaks()

# Made with Bob
