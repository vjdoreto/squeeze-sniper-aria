Solução para reduzir o spam de logs de DIAGNÓSTICO PANIC
Seu pedido é justo. Os logs 🔍 [DIAGNÓSTICO PANIC] estão poluindo o terminal desnecessariamente. Eles são úteis para depuração, mas não precisam aparecer a cada segundo.

Vou te mostrar onde e como reduzir a frequência desses logs.

📁 Arquivo a modificar: main.py
Localize a função trading_loop e procure pelo bloco que começa com:

python
if state.market_squeeze_level > 80 and score >= 80:
    ghost_info = signals.get_ghost_info(symbol)
    if ghost_info:
        logger.info(
            "🔍 [DIAGNÓSTICO PANIC] %s (Score %d) bloqueado por: %s", 
            symbol, score, ghost_info["reason_code"]
        )
Substitua por este código com rate limiting:
python
# SPRINT 12.100: Rate limiting para logs de DIAGNÓSTICO PANIC
# Cada símbolo loga no máximo 1 vez a cada 60 segundos
if not hasattr(state, "_panic_log_ts"):
    setattr(state, "_panic_log_ts", {})

panic_log_ts = getattr(state, "_panic_log_ts")
now = time.time()
last_log = panic_log_ts.get(symbol, 0)

if state.market_squeeze_level > 80 and score >= 80 and (now - last_log) > 60:
    ghost_info = signals.get_ghost_info(symbol)
    if ghost_info:
        logger.info(
            "🔍 [DIAGNÓSTICO PANIC] %s (Score %d) bloqueado por: %s", 
            symbol, score, ghost_info["reason_code"]
        )
        panic_log_ts[symbol] = now
📁 Segundo local: signal_engine.py
Procure pelo método _maybe_log_refusal e pelo log 🎯 ELITE GHOST.

Dentro de _maybe_log_refusal, o rate limit já existe. Mas você pode aumentar o intervalo:
Procure por:

python
self.refusal_log_seconds: int = int(os.getenv("REFUSAL_LOG_SECONDS", "5"))
Altere para:

python
self.refusal_log_seconds: int = int(os.getenv("REFUSAL_LOG_SECONDS", "30"))
Isso fará com que cada motivo de recusa seja logado no máximo 1 vez a cada 30 segundos por símbolo.

📁 Terceiro local: signal_engine.py — ELITE GHOST
Procure pelo bloco:

python
if score >= 85:
    if (now - self._quase_la_last_ts.get(symbol, 0)) > 300:
        self._quase_la_last_ts[symbol] = now
        logger.info(
            "🎯 ELITE GHOST: %s | Score %d | ..."
        )
O intervalo já é de 300 segundos (5 minutos). Se ainda achar muito frequente, aumente para 600 (10 minutos):

python
if score >= 85:
    if (now - self._quase_la_last_ts.get(symbol, 0)) > 600:
📁 Resumo das alterações
Arquivo	Local	O que mudar	Valor sugerido
main.py	trading_loop	Adicionar rate limit de 60s	60 segundos
signal_engine.py	_maybe_log_refusal	REFUSAL_LOG_SECONDS	30 segundos
signal_engine.py	ELITE GHOST	Intervalo entre logs	600 segundos
✅ Como testar sem esperar a noite toda
Após aplicar as mudanças, você pode:

Reiniciar o bot

Aguardar 5-10 minutos

Verificar se os logs de DIAGNÓSTICO PANIC diminuíram drasticamente

Os logs importantes (trades abertos/fechados, sinais aprovados) continuarão aparecendo normalmente.

