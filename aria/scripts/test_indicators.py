"""
test_indicators.py — Testes e exemplos dos indicadores proprietários
Doreto Squeeze Sniper · v1.0

Rodar com:
    python test_indicators.py

Sem dependências externas para os testes síncronos.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indicators import (
    calculate_crm, calculate_grm, calculate_btc_reset,
    CRMInput, GRMInput, BTCResetInput,
    RiskLevel, ResetState,
)
from indicators.btc_reset import calculate_rsi, detect_v_pattern


def separator(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print('═'*60)


# ─── Teste CRM ────────────────────────────────────────────────────────────────

def test_crm():
    separator("CRM — Crypto Risk Meter")

    # Cenário 1: mercado em medo extremo (sessão atual)
    print("\n[1] Cenário atual — BTC -4.27%, FGI=12, USDT.D=8.7%")
    result = calculate_crm(CRMInput(
        usdt_dominance=8.7,
        fear_greed_index=12,
        btc_change_24h=-4.27,
        funding_rate_avg=0.00005,
        eth_dominance=8.8,
    ))
    print(f"    Score: {result.score} | Nível: {result.level.value}")
    print(f"    {result.summary}")
    # FGI=12 (Medo Extremo) = OPORTUNIDADE para o operador = score de risco BAIXO (lógica invertida)
    # Logo USDT.D alto + BTC negativo puxam para cima, mas FGI baixo puxa para baixo
    # Score moderado ~54 é o resultado correto desta lógica
    assert result.score >= 40, "Score deveria refletir ambiente adverso parcialmente"
    assert result.level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL)

    # Cenário 2: mercado bull saudável
    print("\n[2] Cenário bull — BTC +3%, FGI=65, USDT.D=4.5%")
    result2 = calculate_crm(CRMInput(
        usdt_dominance=4.5,
        fear_greed_index=65,
        btc_change_24h=3.0,
        funding_rate_avg=0.0002,
        eth_dominance=15.0,
    ))
    print(f"    Score: {result2.score} | Nível: {result2.level.value}")
    print(f"    {result2.summary}")
    assert result2.score <= 40, "Esperado BAIXO/MODERADO em bull"

    # Cenário 3: dados parciais (só BTC e FGI)
    print("\n[3] Dados parciais — só BTC e FGI")
    result3 = calculate_crm(CRMInput(
        btc_change_24h=-2.0,
        fear_greed_index=25,
    ))
    print(f"    Score: {result3.score} | Faltando: {result3.missing}")
    assert len(result3.missing) == 3, "Esperado 3 campos faltando"

    # Cenário 4: FGI na inversão — ganância extrema = risco alto
    print("\n[4] Ganância extrema — FGI=90 (risco por excesso de longs)")
    result4 = calculate_crm(CRMInput(
        usdt_dominance=4.0,
        fear_greed_index=90,
        btc_change_24h=5.0,
        funding_rate_avg=0.0008,
        eth_dominance=14.0,
    ))
    print(f"    Score: {result4.score} | Nível: {result4.level.value}")
    print(f"    Nota: FGI alto = mercado alavancado = risco real para o operador")

    print("\n✅ CRM: todos os testes passaram")


# ─── Teste GRM ────────────────────────────────────────────────────────────────

def test_grm():
    separator("GRM — Global Risk Meter")

    # Cenário 1: mercado global em stress
    print("\n[1] Mercado em stress — VIX=28, DXY=106, S&P -1.5%")
    result = calculate_grm(GRMInput(
        vix=28.0,
        dxy=106.0,
        sp500_change=-1.5,
        nasdaq_change=-2.1,
        gold_change=0.9,
    ))
    print(f"    Score: {result.score} | Nível: {result.level.value}")
    print(f"    {result.summary}")
    assert result.score >= 60, "Esperado ELEVADO/CRÍTICO com VIX alto"

    # Cenário 2: fuga dupla Gold + DXY
    print("\n[2] Fuga dupla — Gold +1.2%, DXY +0.5%, S&P -1.8%")
    result2 = calculate_grm(GRMInput(
        vix=24.0,
        dxy=105.0,
        sp500_change=-1.8,
        nasdaq_change=-2.5,
        gold_change=1.2,
    ))
    print(f"    Score: {result2.score} | Nível: {result2.level.value}")
    print(f"    Nota: Gold + S&P negativo ativa bônus de correlação")

    # Cenário 3: risk-on total
    print("\n[3] Risk-on — VIX=12, DXY=99, S&P +1.2%")
    result3 = calculate_grm(GRMInput(
        vix=12.0,
        dxy=99.0,
        sp500_change=1.2,
        nasdaq_change=1.8,
        gold_change=-0.3,
    ))
    print(f"    Score: {result3.score} | Nível: {result3.level.value}")
    assert result3.score <= 25, "Esperado BAIXO em risk-on"
    assert result3.level == RiskLevel.LOW

    # Cenário 4: dados parciais
    print("\n[4] Só VIX disponível")
    result4 = calculate_grm(GRMInput(vix=32.0))
    print(f"    Score: {result4.score} | Faltando: {result4.missing}")

    print("\n✅ GRM: todos os testes passaram")


# ─── Teste BTC Reset ──────────────────────────────────────────────────────────

def test_btc_reset():
    separator("BTC Reset Monitor")

    # Teste RSI calculator
    print("\n[0] RSI Calculator")
    closes_bull = [100 + i*0.5 for i in range(30)]   # tendência alta
    closes_bear = [100 - i*0.5 for i in range(30)]   # tendência baixa
    rsi_bull = calculate_rsi(closes_bull)
    rsi_bear = calculate_rsi(closes_bear)
    print(f"    RSI bull: {rsi_bull:.1f} (esperado > 70)")
    print(f"    RSI bear: {rsi_bear:.1f} (esperado < 30)")
    assert rsi_bull > 70, f"RSI bull deveria ser > 70, foi {rsi_bull}"
    assert rsi_bear < 30, f"RSI bear deveria ser < 30, foi {rsi_bear}"

    # Teste padrão V
    print("\n[1] Detecção padrão V")
    history_v     = [60.0, 45.0, 28.0, 35.0, 55.0]   # tocou < 30, voltou > 50
    history_no_v  = [60.0, 55.0, 50.0, 45.0, 40.0]   # descendo mas não V
    history_stuck = [28.0, 25.0, 22.0, 18.0, 15.0]   # preso abaixo de 30
    assert detect_v_pattern(history_v, 30.0)    == True,  "V não detectado"
    assert detect_v_pattern(history_no_v, 30.0) == False, "Falso positivo V"
    assert detect_v_pattern(history_stuck, 30.0) == False, "V com RSI atual < 50"
    print("    ✅ Padrão V detectado corretamente nos 3 cenários")

    # Cenário 1: RESET da sessão atual (print do dashboard)
    print("\n[2] Sessão atual — 6 TFs em reset, RSI 1D=10.6")
    result = calculate_btc_reset(BTCResetInput(
        rsi_by_tf={
            "5m":  13.9,
            "15m": 30.7,   # watch, não reset
            "30m": 29.5,
            "1h":  27.5,
            "4h":  18.1,
            "12h": 11.5,
            "1d":  10.6,
        },
        liq_usd_1h=8_000_000,    # 8M (abaixo do threshold de 10M)
        liq_threshold=10_000_000,
        rsi_threshold=30.0,
    ))
    print(f"    Score: {result.score} | Estado: {result.state.value}")
    print(f"    TFs em reset: {result.reset_count} | Multiplicador liq: {result.liq_multiplier}")
    print(f"    {result.summary}")
    assert result.state in (ResetState.STRONG, ResetState.EXTREME)

    # Cenário 2: RESET EXTREMO com liquidações massivas
    print("\n[3] RESET EXTREMO — todos TFs < 30, liq=50M")
    result2 = calculate_btc_reset(BTCResetInput(
        rsi_by_tf={"5m": 15.0, "15m": 18.0, "30m": 22.0,
                   "1h": 19.0, "4h": 14.0, "12h": 11.0, "1d": 8.0},
        liq_usd_1h=50_000_000,
        liq_threshold=10_000_000,
        rsi_threshold=30.0,
    ))
    print(f"    Score: {result2.score} | Estado: {result2.state.value}")
    print(f"    Multiplicador: {result2.liq_multiplier} (esperado 1.30)")
    assert result2.state == ResetState.EXTREME
    assert result2.liq_multiplier == 1.30

    # Cenário 3: V RELÂMPAGO
    print("\n[4] V RELÂMPAGO — RSI tocou 25, voltou para 55")
    result3 = calculate_btc_reset(BTCResetInput(
        rsi_by_tf={"5m": 55.0, "15m": 52.0, "1h": 53.0},
        rsi_history_by_tf={
            "5m":  [60.0, 42.0, 25.0, 38.0, 55.0],
            "15m": [58.0, 40.0, 27.0, 42.0, 52.0],
            "1h":  [55.0, 35.0, 24.0, 45.0, 53.0],
        },
        liq_usd_1h=15_000_000,
        liq_threshold=10_000_000,
        rsi_threshold=30.0,
    ))
    print(f"    Score: {result3.score} | Estado: {result3.state.value}")
    print(f"    V detectado em: {result3.v_tfs}")
    assert result3.v_detected == True
    assert result3.state == ResetState.V_LIGHTNING

    # Cenário 4: NEUTRO
    print("\n[5] NEUTRO — mercado normal")
    result4 = calculate_btc_reset(BTCResetInput(
        rsi_by_tf={"5m": 62.0, "15m": 58.0, "1h": 55.0, "4h": 52.0},
        liq_usd_1h=1_000_000,
        liq_threshold=10_000_000,
        rsi_threshold=30.0,
    ))
    print(f"    Score: {result4.score} | Estado: {result4.state.value}")
    assert result4.state == ResetState.NEUTRAL

    # Cenário 5: closes brutos (Opção B)
    print("\n[6] Closes brutos — RSI calculado internamente")
    closes_reset = [45000 - i * 200 for i in range(35)]   # queda
    result5 = calculate_btc_reset(BTCResetInput(
        closes_by_tf={"1h": closes_reset},
        liq_usd_1h=5_000_000,
        liq_threshold=10_000_000,
    ))
    print(f"    RSI calculado: {result5.tf_statuses[0].rsi:.1f}")
    print(f"    Estado: {result5.state.value}")

    print("\n✅ BTC Reset: todos os testes passaram")


# ─── Teste integração ─────────────────────────────────────────────────────────

def test_integration():
    separator("Integração — leitura combinada dos 3 indicadores")

    print("\nCenário: mercado em RESET FORTE + ambiente de risco")

    crm = calculate_crm(CRMInput(
        usdt_dominance=8.7,
        fear_greed_index=12,
        btc_change_24h=-4.27,
        funding_rate_avg=0.00005,
        eth_dominance=8.8,
    ))

    grm = calculate_grm(GRMInput(
        vix=28.0,
        dxy=105.0,
        sp500_change=-1.5,
        nasdaq_change=-2.0,
        gold_change=0.8,
    ))

    reset = calculate_btc_reset(BTCResetInput(
        rsi_by_tf={"5m": 13.9, "15m": 30.7, "30m": 29.5,
                   "1h": 27.5, "4h": 18.1, "12h": 11.5, "1d": 10.6},
        liq_usd_1h=8_000_000,
        liq_threshold=10_000_000,
        rsi_threshold=30.0,
    ))

    print(f"\n  CRM:   {crm.score:5.1f}/100  [{crm.level.value:9}]")
    print(f"  GRM:   {grm.score:5.1f}/100  [{grm.level.value:9}]")
    print(f"  RESET: {reset.score:5.1f}/100  [{reset.state.value}]")

    print("\n  Interpretação combinada:")
    if reset.state in (ResetState.STRONG, ResetState.EXTREME, ResetState.V_LIGHTNING):
        print("  → RESET detectado: tempestade em curso ou recém-passada")
        if crm.score >= 70:
            print("  → CRM CRÍTICO: mercado cripto em fuga — aguardar estabilização")
        print("  → Monitorar ativos com EXP_BTC positivo para entrada pós-reset")
    elif crm.score >= 70 and grm.score >= 60:
        print("  → Ambiente adverso: CRM e GRM altos — máxima seletividade")
    elif crm.score <= 30 and reset.state == ResetState.NEUTRAL:
        print("  → Ambiente favorável: CRM baixo + mercado estável = oportunidade")

    print("\n✅ Integração: interpretação combinada funcionando")


# ─── Runner ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Doreto Squeeze Sniper — Teste dos Indicadores Proprietários")
    print("v1.0 · 05/06/2026")

    try:
        test_crm()
        test_grm()
        test_btc_reset()
        test_integration()

        separator("RESULTADO FINAL")
        print("\n  ✅ Todos os testes passaram com sucesso!")
        print("  Módulos prontos para avaliação do Brain e implementação pelo Forge.\n")

    except AssertionError as e:
        print(f"\n  ❌ FALHA: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
