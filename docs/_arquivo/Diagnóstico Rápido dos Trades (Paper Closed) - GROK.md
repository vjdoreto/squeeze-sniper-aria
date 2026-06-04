Sim, compreendi perfeitamente o contexto. Você tem um bot sólido em estrutura (SqueezeSniper-V4), com boa telemetria (EXP, OI, LSR, CVD, etc.), mas o desempenho em paper está destruindo capital (-1.02% avg PnL, win rate 16.67% em 6 trades). Isso é inaceitável para live.
Vou direto ao diagnóstico baseado nos arquivos que você enviou (paper_closed.jsonl, paper_opportunities.csv, audit_quality_report, signals, refusals, etc.).
1. Diagnóstico Rápido dos Trades (Paper Closed)

Symbol,Entry Assert.,Exit Reason,PnL%,MFE%,MAE%,Duration,Problema Principal
ASTERUSDT,weak,trailing_stop,-0.64,12.1,-1.36,448s,Reverteu rápido
PUNDIXUSDT,good,trailing_stop,+15.17,17.35,-11.48,772s,Único winner
STGUSDT,weak,trailing_stop,-0.98,15.17,-2.34,509s,Reverteu
STGUSDT,weak,trailing_stop,-0.64,3.35,-4.65,76s,Muito curto
IDUSDT,mixed,stop_loss,-17.50,1.55,-17.18,955s,Pior drawdown
PUNDIXUSDT,weak,trailing_stop,-1.56,10.24,-1.24,226s,Reverteu
ONDOUSDT,mixed,stop_loss,-16.86,2.24,-16.55,5935s,Long hold ruim
... (resto similar),-,-,-,-,-,-,-


SymbolEntry Assert.Exit ReasonPnL%MFE%MAE%DurationProblema PrincipalASTERUSDTweaktrailing_stop-0.6412.1-1.36448sReverteu rápidoPUNDIXUSDTgoodtrailing_stop+15.1717.35-11.48772sÚnico winnerSTGUSDTweaktrailing_stop-0.9815.17-2.34509sReverteuSTGUSDTweaktrailing_stop-0.643.35-4.6576sMuito curtoIDUSDTmixedstop_loss-17.501.55-17.18955sPior drawdownPUNDIXUSDTweaktrailing_stop-1.5610.24-1.24226sReverteuONDOUSDTmixedstop_loss-16.862.24-16.555935sLong hold ruim... (resto similar)-------
Padrões Críticos:

MFE alto + MAE profundo: Entra bem, mas não protege (trailing_stop muito frouxo ou stop_loss muito distante).
Muitos stop_loss com >15% drawdown → risco assimétrico mortal.
Winners raros, mas quando acerta (PUNDIX), tem bom MFE.
Muitos trades com entry_assertiveness = "weak" ou "mixed".

2. Problemas no Filtro de Entrada (Ghost Refusals)
Top recusas:

lsr_trend_positive: 499 (muito rígido — LSR pode estar em transição)
oi_change_lt_min: 253
final_gate_fail: 180 (muitos bons sinais morrem aqui)

O "final_gate" está matando assertividade.
Recomendações Imediatas para Live (Prioridade Alta)
A. Melhoria no Risk Management & Exits (Mais Crítico)

Dynamic Trailing Stop (atual está matando winners):
Comece mais largo (0.8-1.2% ATR) e aperte após 50% do caminho até TP.
Ou use time-based + MFE-based (ex: se MFE > 8%, mova SL para breakeven + 0.3%).

Stop Loss mais inteligente:
Nunca fixe em 2%. Use ATR-based ou swing low + buffer.
Reduza max risk por trade para 1-2% (você está em 5% em alguns).

Partial Take Profit:
30-40% da posição em 50% do TP.
Resto com trailing.


B. Ajustes no Signal Gate (para mais trades de qualidade)
Python# Exemplo de ajuste no final_gate (pseudocódigo - implemente no seu filter)
def final_gate(signal):
    if signal['score'] < 85: 
        return False  # suba um pouco
    
    # Relaxar LSR um pouco em momentum forte
    if signal.get('cvd_streak', 0) > 20 and signal['lsr_trend'] > -0.03:  
        # permite LSR quase neutro se CVD forte
        pass
    elif signal['lsr_trend'] > -0.005:  # atual é muito rigoroso
        return False
    
    # OI + EXP ainda rei
    if signal['oi_trend'] < 0.01 or signal['exp'] < 0.03:
        return False
    return True
C. Outras Melhorias Rápidas

Cooldown por symbol mais inteligente (baseado em recent volatility).
Risk scaling: Reduza risk após 2 losses seguidos.
Dashboard: O WS está rodando bem (muitos snapshots), mas Telegram está com DNS timeout → use asyncio retry + fallback.
Warmup: Mantenha 300s, mas adicione "pre-warm" com dados históricos se possível.

Próximos Passos que eu recomendo agora:

Implemente primeiro o Dynamic Trailing + Partial TP — isso sozinho deve virar o PNL.
Relaxe ligeiramente o LSR no gate (mas mantenha EXP/OI fortes).
Rode mais paper com os novos parâmetros por 2-3 dias.
Só então vá para live com capital pequeno (1-2% do total).

Quer que eu gere o código específico para:

Novo trailing stop manager?
Ajuste no signal filter?
Novo risk manager?

Diga qual arquivo/modulo quer que eu revise primeiro e eu mando o patch limpo.
Estamos juntos nisso. Vamos virar esse PNL.