#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Análise rápida da sessão de trading atual."""

import json
import sys
from datetime import datetime
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_session():
    """Analisa a sessão atual de trading."""
    
    # Carregar dados
    data_path = Path("logs/paper_opportunities.json")
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print('='*80)
    print('RESUMO EXECUTIVO - SESSAO DE TRADING v4.2.3')
    print('='*80)
    
    # Capital e Performance
    initial = data["initial_capital"]
    current = data["current_capital"]
    peak = data["peak_capital"]
    pnl = current - initial
    pnl_pct = ((current/initial)-1)*100
    
    print(f'\n[CAPITAL]:')
    print(f'  Inicial: ${initial:.2f}')
    print(f'  Atual: ${current:.2f}')
    print(f'  Pico: ${peak:.2f}')
    print(f'  P&L Total: ${pnl:.2f} ({pnl_pct:+.2f}%)')
    
    # Estatísticas
    stats = data['stats']
    print(f'\n[ESTATISTICAS GERAIS]:')
    print(f'  Trades Abertos: {stats["open_count"]}')
    print(f'  Trades Fechados: {stats["closed_count"]}')
    print(f'  Wins: {stats["wins"]} | Losses: {stats["losses"]}')
    print(f'  Win Rate: {stats["win_rate_pct"]}%')
    print(f'  P&L Médio: {stats["avg_closed_pnl_pct"]:.2f}%')
    print(f'  Eficiência de Captura: {stats["capture_efficiency_pct"]:.2f}%')
    
    # Win rate por símbolo
    print(f'\n[WIN RATE POR SIMBOLO]:')
    for symbol, wr in sorted(stats['win_rate_by_symbol'].items()):
        print(f'  {symbol}: {wr}%')
    
    # Análise detalhada dos trades
    print(f'\n[ANALISE DETALHADA DOS {len(data["closed"])} TRADES]:')
    print('='*80)
    
    total_mfe = 0
    total_capture = 0
    durations = []
    
    for i, trade in enumerate(data['closed'], 1):
        entry_time = datetime.fromtimestamp(trade['entry']['time']).strftime('%H:%M:%S')
        exit_time = datetime.fromtimestamp(trade['exit']['time']).strftime('%H:%M:%S')
        duration = trade['live']['duration_sec']
        durations.append(duration)
        
        mfe = trade['quality']['mfe_pct']
        mae = trade['quality']['mae_pct']
        pnl_pct = trade['exit']['pnl_pct']
        
        total_mfe += mfe
        if mfe > 0:
            capture_eff = (pnl_pct / mfe) * 100
            total_capture += capture_eff
        
        win_mark = '[WIN]' if trade['quality']['win'] else '[LOSS]'
        
        print(f'\n{win_mark} #{i} {trade["symbol"]} - {trade["exit"]["reason"]}')
        print(f'  Tempo: {entry_time} -> {exit_time} ({duration}s)')
        print(f'  Entry: ${trade["entry"]["price"]:.6f} | Exit: ${trade["exit"]["price"]:.6f}')
        print(f'  P&L: {pnl_pct:+.2f}% (${trade["exit"]["pnl_usdt"]:+.2f})')
        print(f'  MFE: {mfe:.2f}% | MAE: {mae:.2f}%')
        
        if mfe > 0:
            capture_eff = (pnl_pct / mfe) * 100
            print(f'  Captura MFE: {capture_eff:.1f}%')
        
        print(f'  Score: {trade["entry"]["signal"]["score"]} | EXP: {trade["entry"]["signal"]["exp"]:.4f}')
        print(f'  Entry: {trade["quality"]["entry_assertiveness"]} | Exit: {trade["quality"]["exit_assertiveness"]}')
        
        # Post-trade drift
        pt = trade.get('post_trade', {})
        drift_5m = pt.get('5m', 'N/A')
        drift_15m = pt.get('15m', 'N/A')
        drift_current = pt.get('current_drift', 0)
        
        print(f'  Drift: Atual={drift_current:+.2f}% | 5m={drift_5m} | 15m={drift_15m}')
    
    # Métricas agregadas
    print('\n' + '='*80)
    print('[METRICAS AGREGADAS]:')
    print('='*80)
    
    avg_duration = sum(durations) / len(durations) if durations else 0
    avg_mfe = total_mfe / len(data['closed']) if data['closed'] else 0
    avg_capture = total_capture / len(data['closed']) if data['closed'] else 0
    
    print(f'\n  Duração Média: {avg_duration:.0f}s ({avg_duration/60:.1f}min)')
    print(f'  MFE Médio: {avg_mfe:.2f}%')
    print(f'  Captura MFE Média: {avg_capture:.1f}%')
    
    # Análise de sinais
    signals_path = Path("logs/signals.jsonl")
    if signals_path.exists():
        with open(signals_path, 'r', encoding='utf-8') as f:
            signals = [json.loads(line) for line in f if line.strip()]
        
        print(f'\n[SINAIS GERADOS]: {len(signals)}')
        
        # Distribuição de scores
        scores = [s['score'] for s in signals]
        if scores:
            print(f'  Score Médio: {sum(scores)/len(scores):.1f}')
            print(f'  Score Min/Max: {min(scores)}/{max(scores)}')
    
    print('\n' + '='*80)
    print('[ANALISE CONCLUIDA]')
    print('='*80)

if __name__ == "__main__":
    analyze_session()

# Made with Bob
