# Plano de Ação - Evolução SqueezeSniper V4

Este documento serve como rastro para a evolução estratégica do bot, focando em reverter o Win Rate negativo e proteger o capital no modo LIVE.

## 1. Pilar de Monetização: "Stop the Giveback"
- **Saídas Parciais (PTP):** Implementar realização de lucro em níveis iniciais para pagar taxas e garantir "Risk-Free trades".
- **Trailing Stop ATR:** Substituir gatilhos fixos por volatilidade real do ativo.
- **Breakeven Dinâmico:** Blindagem imediata do capital após atingir ROI de segurança.

## 2. Pilar de Seleção: "Refinamento da Peneira"
- **Ajuste de LSR:** Reduzir a régua de `max_lsr_trend` para patamares realistas (-0.002 a -0.004).
- **Gate de CVD:** Retomar a exigência de agressão compradora real (CVD > 0) para validar o squeeze.
- **Macro Correlation:** Bloquear excesso de ativos do mesmo setor para evitar risco sistêmico.

## 3. Pilar de Infraestrutura: "Performance e Resiliência"
- **Otimização REST:** Unificar a telemetria do Trailing Stop com o fluxo de WebSockets do DataEngine para evitar Rate Limits.
- **Cache de Exchange Info:** Eliminar latência de milissegundos no boot de novos trades.

## 4. Pilar de Mirroring: "Paper vs Live"
- **Slippage Realista:** Simular execuções no Paper com atraso/spread para espelhar o mundo real.
- **Escrita Atômica:** Garantir que nenhuma queda de energia ou reinício corrompa os arquivos de trades abertos.

---
**Status:** Aguardando discussão técnica para implementação.
**Objetivo:** Elevar Win Rate de 14% para > 40% através de filtragem rigorosa e saída inteligente.