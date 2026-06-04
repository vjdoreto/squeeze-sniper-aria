# Backlog de Segurança e Governança

Este arquivo registra modificações temporárias nos protocolos de segurança do bot para fins de testes ou validação com capital reduzido.

## 1. Margem de Segurança de 10% (Sniper LIVE)

**Data da Mudança:** 2026-05-29 (Sprint 12.5)
**Arquivo:** `src/sniper.py`

### Descrição
A trava que exigia um saldo 10% superior ao `usdt_amount` configurado foi removida para permitir o "mando do operador" em bancas pequenas (ex: testar com $20 USDT usando $18 de capital operacional).

### Mudança Realizada
**Antes:**
```python
if balance < self.usdt_amount * 1.1:
```
**Atual:**
```python
if balance < self.usdt_amount:
```

### Critério para Reversão (Voltar ao Original)
- **Gatilho:** Quando o capital operacional (`usdt_amount`) for superior a **$100 USDT**.
- **Motivo:** Garantir que existam fundos para cobrir taxas de rede (fees) e flutuações de margem sem causar rejeição de ordens pela Binance.