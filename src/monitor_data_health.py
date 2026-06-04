#!/usr/bin/env python3
"""
Monitor de Saúde de Dados - SqueezeSniper V4
Monitora completude de dados em tempo real e alerta sobre gaps críticos.
"""
import json
import time
from pathlib import Path
from typing import Dict, Any
from collections import Counter

def load_metric_state() -> Dict[str, Any]:
    """Carrega estado atual das métricas."""
    state_path = Path("logs/metric_state.json")
    if not state_path.exists():
        return {}
    
    with open(state_path, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_data_completeness(data: Dict[str, Dict]) -> Dict[str, Any]:
    """Analisa completude de dados para todos os símbolos."""
    if not data:
        return {"error": "Nenhum dado disponível"}
    
    total_symbols = len(data)
    metrics_status = {
        "lsr": {"present": 0, "none": 0, "zero": 0},
        "rsi_5m": {"present": 0, "none": 0},
        "funding": {"present": 0, "zero": 0},
        "oi": {"present": 0, "zero": 0},
        "cvd": {"present": 0, "zero": 0},
    }
    
    symbols_with_issues = []
    
    for symbol, metrics in data.items():
        issues = []
        
        # LSR
        lsr = metrics.get("lsr")
        if lsr is None:
            metrics_status["lsr"]["none"] += 1
            issues.append("lsr=None")
        elif lsr == 0 or lsr == 0.0:
            metrics_status["lsr"]["zero"] += 1
            issues.append("lsr=0")
        else:
            metrics_status["lsr"]["present"] += 1
        
        # RSI 5m
        rsi = metrics.get("rsi:5m")
        if rsi is None:
            metrics_status["rsi_5m"]["none"] += 1
            issues.append("rsi=None")
        else:
            metrics_status["rsi_5m"]["present"] += 1
        
        # Funding
        funding = metrics.get("funding_rate", 0)
        if funding == 0 or funding == 0.0:
            metrics_status["funding"]["zero"] += 1
            issues.append("funding=0")
        else:
            metrics_status["funding"]["present"] += 1
        
        # OI
        oi = metrics.get("oi", 0)
        if oi == 0 or oi == 0.0:
            metrics_status["oi"]["zero"] += 1
            issues.append("oi=0")
        else:
            metrics_status["oi"]["present"] += 1
        
        # CVD
        cvd = metrics.get("cvd_cumulative", 0)
        if cvd == 0 or cvd == 0.0:
            metrics_status["cvd"]["zero"] += 1
        else:
            metrics_status["cvd"]["present"] += 1
        
        if issues:
            symbols_with_issues.append({"symbol": symbol, "issues": issues})
    
    # Calcula percentuais
    completeness = {}
    for metric, status in metrics_status.items():
        present = status.get("present", 0)
        completeness[metric] = round((present / total_symbols) * 100, 1) if total_symbols > 0 else 0
    
    return {
        "total_symbols": total_symbols,
        "completeness_pct": completeness,
        "metrics_status": metrics_status,
        "symbols_with_issues": symbols_with_issues[:10],  # Top 10 com mais problemas
        "avg_completeness": round(sum(completeness.values()) / len(completeness), 1)
    }

def print_health_report(analysis: Dict[str, Any]):
    """Imprime relatório de saúde formatado."""
    print("\n" + "="*80)
    print("🔍 MONITOR DE SAÚDE DE DADOS - SqueezeSniper V4")
    print("="*80)
    
    if "error" in analysis:
        print(f"❌ Erro: {analysis['error']}")
        return
    
    total = analysis["total_symbols"]
    avg = analysis["avg_completeness"]
    
    print(f"\n📊 Resumo Geral:")
    print(f"   Total de Símbolos: {total}")
    print(f"   Completude Média: {avg}%")
    
    # Status por métrica
    print(f"\n📈 Completude por Métrica:")
    completeness = analysis["completeness_pct"]
    
    for metric, pct in completeness.items():
        status_icon = "✅" if pct >= 85 else "🟡" if pct >= 70 else "🔴"
        print(f"   {status_icon} {metric.upper()}: {pct}%")
    
    # Símbolos com problemas
    issues = analysis["symbols_with_issues"]
    if issues:
        print(f"\n⚠️  Top Símbolos com Gaps ({len(issues)}):")
        for item in issues[:5]:
            print(f"   - {item['symbol']}: {', '.join(item['issues'])}")
    
    # Diagnóstico
    print(f"\n💡 Diagnóstico:")
    if avg >= 85:
        print("   ✅ Sistema operando com alta qualidade de dados")
        print("   ✅ SignalEngine pode operar com confiança")
    elif avg >= 70:
        print("   🟡 Qualidade de dados aceitável, mas pode melhorar")
        print("   🟡 Alguns sinais podem ser perdidos")
    else:
        print("   🔴 Qualidade de dados crítica!")
        print("   🔴 SignalEngine pode estar bloqueando muitos sinais")
        print("   🔴 Recomendado: Verificar logs de pipeline_debug.jsonl")
    
    print("\n" + "="*80 + "\n")

def main():
    """Loop principal de monitoramento."""
    print("🚀 Iniciando Monitor de Saúde de Dados...")
    print("   Pressione Ctrl+C para sair\n")
    
    try:
        while True:
            state = load_metric_state()
            
            if not state or "data" not in state:
                print("⏳ Aguardando dados do MetricStore...")
                time.sleep(10)
                continue
            
            data = state["data"]
            analysis = analyze_data_completeness(data)
            print_health_report(analysis)
            
            # Aguarda 30 segundos antes da próxima verificação
            print("⏳ Próxima verificação em 30 segundos...")
            time.sleep(30)
    
    except KeyboardInterrupt:
        print("\n\n👋 Monitor encerrado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro no monitor: {e}")

if __name__ == "__main__":
    main()

# Made with Bob
