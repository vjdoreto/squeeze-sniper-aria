Auditoria Técnica — SqueezeSniper V4
Data: 2026-05-30 | Modo auditado: Paper + LIVE

🔴 BUGS CRÍTICOS (bloqueadores para LIVE)
BUG 1 — Saldo LIVE não atualiza em tempo real
Arquivo: main.py linhas 882–894

Causa raiz confirmada:
O live_monitor_loop usa o user-data websocket stream para capturar ACCOUNT_UPDATE.
O evento chave é "a" (account update), mas o filtro de eventos está errado:

python

# linha 842: só captura ORDER_TRADE_UPDATE

event = msg.get("e")

# 

data = msg.get("a") or {}  # Tenta pegar "a" de QUALQUER mensagem, não só ACCOUNT_UPDATE
balance_updates = data.get("B") or []
Problema: msg.get("a") só existe quando event == "ACCOUNT_UPDATE". Em mensagens de ORDER_TRADE_UPDATE, "a" é None, então balance_updates é sempre vazio.
O saldo carrega uma vez no boot (REST), mas nunca mais atualiza via stream porque o filtro de evento está faltando.

Fix:

python

# Antes de processar balanço, checar se é ACCOUNT_UPDATE

if event == "ACCOUNT_UPDATE":
    data = msg.get("a") or {}
    balance_updates = data.get("B") or []
    pos_updates = data.get("P") or []
    # ... processar ...
BUG 2 — liq_history acumula entradas duplicadas a cada bind_market()
Arquivo: src/bot_state.py linhas 165–167

python

if not self._liq_history or abs(...) > 1000:
    self._liq_history.append(...)  # condicional
self._liq_history.append(...)     # SEMPRE appenda — bug duplica tudo
A segunda linha está fora do if. A cada ciclo do trading loop (~1s), são appended 2 entradas. Com maxlen=500, o histórico satura e deforma o gráfico de liquidações.

Fix: Remover o segundo append fora do bloco if.

BUG 3 — Persistência JSON perde dados ao reiniciar (paper_opportunities.json / live_opportunities.json)
Causa raiz: O LiveTracker._persist() funciona corretamente (escrita atômica via .tmp). Mas o PaperTradeTracker (não auditado aqui, mas inferido do padrão) grava no json_path sem o closed_jsonl.

Ponto crítico: O preferences.json não tem json_path explícito para o paper:

json

"paper": {
    "closed_jsonl": "logs/paper_closed.jsonl"
    // faltam: "json_path" e "csv_path"
}
Sem json_path, o tracker usa o default logs/paper_opportunities.json, mas após reset ou reinício, se o arquivo não existir ou estiver corrompido (truncado por Ctrl+C durante escrita), os trades abertos são perdidos.

Fix: Adicionar escrita atômica via .tmp em PaperTradeTracker._persist() se ainda não tiver, e adicionar json_path explícito no preferences.json.

BUG 4 — Alertas recentes não aparecem (sinais não chegam ao sniper)
Análise das gates em signal_engine.py:

Com os valores atuais do preferences.json:

min_exp: 0.008 — OK, muito relaxado
max_lsr_trend: -0.006 — RESTRITIVO DEMAIS. Exige que LSR caia 0.006 por intervalo. Na prática a maioria dos ativos em compressão real tem lsr_trend entre -0.001 e -0.004.
max_lsr_change_pct: -0.1 — RESTRITIVO. Exige queda de 0.1% no LSR em 5m.
min_oi_change_pct: 0.02 — OK.
cooldown_seconds: 90 — OK.
Gating em cascata que mata sinais:

lsr_trend <= max_lsr_trend (-0.006): para maioria das moedas, lsr_trend está entre -0.002 e -0.004. Gate bloqueando quase tudo.
lsr_change_pct >= 0 → retorna None. Se LSR não está caindo no delta 5m, descarta.
trading_mode != "paper" → vol_adaptive_gating ativo em LIVE com min_vol_adaptive_ratio: 0.03 (ok, muito relaxado).
pc_5m > 1.5 → entrada tardia. Correto.
Conclusão: O max_lsr_trend: -0.006 é o principal assassino de sinais. Para squeezes reais, um LSR caindo 0.002–0.004 já é forte. Mudar para -0.002 vai liberar muito mais oportunidades legítimas.

BUG 5 — Trailing stop loop faz REST a cada 5s para TODAS as posições abertas
Arquivo: src/sniper.py linhas 489–564

O _trailing_stop_loop chama:

futures_position_information() — REST
futures_mark_price(symbol) — REST por posição
futures_funding_rate(symbol) — REST por posição
futures_get_open_orders(symbol) — REST por posição
A cada 5 segundos. Se tiver 3 posições abertas = 4 chamadas REST × 3 = ~12 REST/5s = 144 REST/min só do trailing stop. Binance limita a 1200 requisições/min para futuros, mas em conjunto com o DataEngine já está pesado.

Risco real: Atingir rate limit em momento crítico → ban REST de 1 min → trailing stop não funciona → SL não move para breakeven → perda de lucro ou ativação de SL antigo.

Fix: Aumentar intervalo do trailing para 30s em modo normal e 10s só quando pnl_pct >= breakeven_threshold * 0.5.

🟡 PROBLEMAS MÉDIOS (não bloqueadores mas afetam qualidade)
P1 — trading_loop passa cfg.trading_mode em vez de state.trading_mode
Arquivo: main.py linha 1935

python

asyncio.create_task(
    trading_loop(
        engine, signal_engine, sniper, state, journal,
        cfg.trading_mode,  # ← ERRADO: usa o modo do CONFIG (estático)
        inflight, telegram=telegram,
    )
)
O trading_loop recebe trading_mode como parâmetro mas usa state.trading_mode internamente (linha 393, 454, 498). Então não há problema de execução — o parâmetro trading_mode no trading_loop é apenas passado para o journal.log_signal() mas o state.trading_mode é quem comanda a lógica. Verificar se journal.log_signal usa isso corretamente.

P2 — _on_set_mode chama future.result() bloqueando a thread do dashboard
Arquivo: main.py linhas 1655–1659

python

future = asyncio.run_coroutine_threadsafe(
    _validate_live_account(engine_client, min_bal), loop
)
if not future.result():  # ← BLOQUEANTE — trava a thread do dashboard
Se a validação demorar (timeout de rede), a thread do web dashboard trava. O usuário vê o botão "LIVE" sem resposta. Timeout de 10s recomendado: future.result(timeout=10).

P3 — Sniper usa futures_exchange_info() em cada execute_long para novos símbolos
Arquivo: src/sniper.py linha 76

python

info = await self.client.futures_exchange_info()  # REST pesado (~500KB)
Para símbolos nunca vistos, puxar o exchange_info inteiro a cada trade novo. Em LIVE com múltiplas entradas rápidas (cascata), isso gera latência de 300–800ms na execução.

Fix: Pre-carregar o exchange_info do DataEngine no boot do Sniper para preencher o_symbol_filters cache de uma vez.

P4 — bot_state.py duplica append em liq_history (mencionado no BUG 2 acima)
P5 — max_open_positions: 12 para LIVE com capital de 18 USDT
Margem por trade = 18 USDT × 0.05 (risk) = 0.9 USDT. Notional = 0.9 × 8 = 7.2 USDT.
Binance tem mínimo notional de ~5 USDT para maioria das moedas — isso passa.
Mas 12 posições simultâneas × 7.2 USDT = 86.4 USDT de notional total, que requer ~10.8 USDT de margem. Com capital de 18 USDT, a margem disponível cai rapidamente.
Recomendação: Reduzir max_open_positions para 3–4 no LIVE com esse capital.

🟢 O QUE ESTÁ CORRETO
Warmup Gate 300s — implementado e funcionando. Correto.
Escrita atômica de prefs (tmp → replace) — correto em _save_prefs().
LiveTracker._persist() — escrita atômica. Correto.
Trailing SL/TP server-side — correto. Proteção real na Binance.
Single-instance lock — correto. Evita dupla execução.
DNA: RSI alto NÃO bloqueia — correto. O gate é RSI mínimo, não máximo.
Sorted_symbols por liq_cascade + score — correto. Prioriza cascata.
Retry de SL/TP (3 tentativas) — correto. Se falhar fecha posição.
Breakeven via trailing — lógica correta (70% do TP → move SL para +0.1%).
Compound mode — lógica correta via live_tracker.current_capital.
📋 PLANO DE AÇÃO — PRIORIDADE

# Bug Impacto Arquivo Ação

1 Saldo não atualiza no stream CRÍTICO main.py:842 Fix filtro ACCOUNT_UPDATE
2 max_lsr_trend muito restritivo CRÍTICO preferences.json Mudar de -0.006 para -0.002
3 liq_history append duplicado Médio bot_state.py:167 Remover linha duplicada
4 trailing_stop REST a cada 5s Médio sniper.py:481 Aumentar intervalo para 30s
5 future.result() sem timeout Baixo main.py:1659 Adicionar timeout=10
6 max_open_positions=12 em 18 USDT Baixo preferences.json Reduzir para 3–4
⚠️ CONFORTO PARA LIVE
Antes de ativar LIVE com dinheiro real:

Confirmar que a API Binance tem permissão Futures Trading habilitada
Confirmar que o IP atual está na Whitelist da API
Aplicar fix do BUG 1 (saldo) — sem isso o dashboard mostra capital desatualizado e o compound mode vai usar número errado
Aplicar ajuste do BUG 4 (max_lsr_trend: -0.002) — sem isso nenhum sinal vai disparar em LIVE (gates muito rígidas)
Testar com 1 posição primeiro (max_open_positions: 1) até confirmar fluxo end-to-end
