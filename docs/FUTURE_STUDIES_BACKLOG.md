# Backlog de Estudos Futuros — SqueezeSniper V4

Este arquivo registra hipóteses e melhorias técnicas para investigação futura, visando otimização de custos e performance sem comprometer a estabilidade atual do sistema.

## 1. Otimização de Taxas: Market vs. Limit Orders
**Data de Registro:** 2026-05-29

### Contexto
O Sniper opera atualmente 100% via ordens a mercado (Market Orders) para garantir a captura imediata da ignição do Squeeze. Isso incorre em taxas de **Taker** (~0.04%).

### Hipótese de Estudo
- **Entrada via Limit Offset:** Avaliar o uso de ordens `LIMIT` com um pequeno *offset* positivo (ex: Preço do Sinal + 0.05%). O objetivo é testar se o sistema consegue ser executado como **Maker** (taxa de ~0.02%) sem perder o rastro da subida exponencial.
- **Saída Passiva (TP Limit):** Implementar `TAKE_PROFIT_LIMIT` no motor do Sniper. Investigar se, em Short Squeezes, a liquidez no topo é suficiente para fechar a posição passivamente ou se o preço "salta" o nível de ordens limitadas, gerando trades enforcados.

### Riscos Detectados
- **Sinal Fantasma:** Preço bate o sinal, mas a ordem limite não é preenchida.
- **Alpha Decay:** O tempo gasto esperando o preenchimento da ordem limite pode resultar em uma entrada em preço pior do que uma ordem a mercado imediata.

### Métrica de Sucesso
Aumento do lucro líquido (Net PnL) por trade em pelo menos 0.04% (economia de taxas) sem reduzir o Win Rate global do sistema.

---
*Documento de Governança V1.0 - Estudo de Latência e Custos.*