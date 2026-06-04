Sim. Depois das mudanças, para eu validar se ficou seguro, coerente e sem contaminação entre paper/live, o pacote mínimo que eu quero revisar é este, nesta ordem:

Pacote crítico sniper.py, signal_engine.py, paper_tracker.py, live_tracker.py, main.py, config.py e o arquivo de preferências realmente usado no runtime (preferences.local.json ou o path efetivo vindo de PREFERENCES_FILE). Sem esse conjunto eu consigo opinar, mas não consigo fechar a auditoria com segurança. main.py config.py paper_tracker.py live_tracker.py signal_engine.py

Pacote que fecha a análise Depois disso, eu gostaria de ver também sizing_utils.py, metric_engine.py, market_view.py e persistence.py, porque teu problema agora já não é só “entrada ruim”; pode estar espalhado entre sizing, fit score, persistência e telemetria. data_engine.py bot_state.py web_dashboard.py

Agora, indo ao que interessa de verdade: teus dados desta noite mostram um colapso operacional real, não impressão tua. O paper fechou 21 trades, com 14,29% de win rate, PnL médio de -5,07%, MFE médio de +11,03% e MAE médio de -9,35%. No recorte menor do teu audit report, os 6 trades mais recentes já estavam ruins, mas o quadro completo do JSON está pior do que o TXT resumido deixa parecer. paper_opportunities.json.txt audit_quality_report.txt audit_quality_report.json.txt

Meu veredito curto
O maior problema atual não é slippage. O maior problema é uma combinação de seleção degradada + captura de lucro quebrada + empilhamento de risco excessivo. O resultado é perverso: você pega trades que chegam a andar bem, mas devolvem quase tudo ou viram perda. backtest_results.json.txt paper_closed.jsonl

1) O motor está deixando dinheiro na mesa de forma grave
O dado mais feio da noite é este: teu sistema teve MFE médio de +11,03%, mas fechou com PnL médio de -5,07%. Isso significa que o bot frequentemente chegou a ter vantagem, só que não soube transformar impulso em lucro realizado. Pior: houve casos extremos de giveback, como MEMEUSDT com MFE +31,28% terminando em -0,64%, POLYXUSDT com MFE +29,96% terminando em -0,64%, e STEEMUSDT com MFE +14,56% terminando em -5,37%. Isso é assinatura clássica de trailing/breakeven mal calibrado, não de “mercado impossível”. paper_closed.jsonl paper_opportunities.csv

2) O papel do trailing/breakeven está claramente errado para teu DNA
No paper_tracker.py, o stop vai para breakeven + 0,1% quando o trade atinge 70% do TP, e o nome do evento continua trailing_stop mesmo quando o resultado líquido vira negativo por taxa ou devolução. Com alavancagem 8x, esse lock é raso demais para um bot que quer capturar ignição e expansão. Na prática, teu sistema deixa o trade provar que estava certo, mas protege lucro de forma tímida demais. Foi exatamente isso que teus dados mostraram. paper_tracker.py paper_closed.jsonl

3) A seleção perdeu pureza de fluxo institucional
Os dados mostram que trades aceitos com CVD de entrada negativo performaram muito pior. Nos fechados desta noite, o subconjunto com cvd_1m < 0 teve desempenho claramente mais fraco; e olhando os sinais gravados, vários losers relevantes entraram com fluxo contraditório para um squeeze LONG. Isso conversa diretamente com o que existe no signal_engine.py: ali o filtro de cvd_change_pct foi relaxado e o CVD deixou de ser gate duro. Para o teu DNA, isso é perigoso, porque abre espaço para “OI subindo + LSR caindo” sem agressão compradora real sustentando o movimento. signals.jsonl signal_engine.py

4) O LSR aceito está fraco demais em vários losses
Alguns dos piores losses entraram com lsr_trend muito pouco negativo, ou seja, sem pânico verdadeiro de short. Exemplos típicos: ONDOUSDT entrou com lsr_trend perto de -0.0059, IDUSDT perto de -0.0034, ARKUSDT perto de -0.0041, e todos deram pancada. Isso indica que tua régua prática de “queda suficiente do LSR” ficou frouxa demais, seja por threshold salvo em config, seja por relaxamento do modo paper. Para o teu estilo, isso é quase anti-DNA. signals.jsonl paper_closed.jsonl signal_engine.py

5) O risco de cluster está alto demais
Teu paper_tracker_init mostra max_open_positions=12 com risk_pct_per_trade=5%. Mesmo sem contar correlação implícita entre alts, isso já é agressivo. E o timeline confirma clustering: às 04:20–04:22 o bot abriu ASTER, PUNDIX e ONDO quase em sequência; depois houve novas rajadas em blocos curtos. Se o regime de mercado muda ou o macro vira contra alts, esse modelo amplifica o estrago. E teu CORR_GROUPS é muito estreito para proteger o universo real que apanhou hoje. paper_debug.jsonl paper_closed.jsonl paper_tracker.py

6) A parte boa da notícia: nesta noite o paper/live split-brain não parece ter sido o gatilho direto do desastre
Os logs de execução mostram o Sniper chamando a branch de paper de forma consistente, e o pipeline_debug também registra state_trading_mode: "paper" nos hits desta sessão. Então, sendo honesto, o resultado terrível desta noite não parece ter sido causado principalmente pelo bug de alternância paper/live. Esse risco arquitetural ainda existe no código, mas os logs desta rodada apontam mais para lógica de seleção e de saída do que para erro de roteamento de modo. sniper_debug.jsonl pipeline_debug.jsonl

7) Slippage não explica o colapso
Teu backtest com slippage_pct = 0.1 mostra 0 trades flipped e diferença média insuficiente para justificar o massacre. Em outras palavras: o bot não quebrou porque “o mercado tirou 0,1% na execução”. Ele quebrou porque está escolhendo mal alguns contextos e monetizando pessimamente os acertos parciais. backtest_results.json.txt

O que eu faria antes de qualquer novo run
Primeiro freio de segurança: reduzir paper_max_open_positions para 3, derrubar alavancagem temporariamente para 4x ou 5x, e travar o modo “relaxed” até a curva voltar a respirar. Hoje teu sistema está com licença demais para entrar cedo e stackar risco. paper_debug.jsonl signal_engine.py

Segundo freio: reimpor filtro de fluxo. Para tua próxima rodada de saneamento, eu voltaria provisoriamente a exigir: cvd_1m > 0, oi_change_pct >= 0.5, lsr_trend <= -0.01, trades_1m >= 8 e zero relaxamento por score alto sozinho. Isso não é “a solução mágica”; é uma quarentena para o motor parar de atirar em contexto marginal. signals.jsonl signal_engine.py

Terceiro freio: corrigir a captura de lucro. Se o trade bate 70% do TP, mover SL para entry + 0.1% está pequeno demais para teu perfil. Você precisa ou de partial take real (25%~33%), ou de um lock mais agressivo sobre a distância já conquistada, ou dos dois. Do jeito atual, o motor “acerta o tema e erra a monetização”. paper_tracker.py paper_closed.jsonl