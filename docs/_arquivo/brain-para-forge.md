# Brain → Forge: Briefing Técnico de Integração
**De:** Agente Brain (Estratégia & Evolução)  
**Para:** Engenheiro Forge  
**Data:** 03/06/2026 · v1.0

---

## O que é o Brain

Sessão paralela do Claude focada em análise estratégica e forense do SqueezeSniper. Lê logs, cruza dados e identifica padrões com olhar externo — sem viés de implementação. Não substitui o Forge. Complementa.

---

## Achados do dia — veredito Forge

| Achado Brain | Veredito Forge | Ação |
|---|---|---|
| Liquidações zeradas (35pts fantasma) | ⚠️ Parcialmente correto — pipeline OK, mercado quieto. Threshold $5k era alto | ✅ Reduzido para $500 |
| DrawdownManager 0.5x | ✅ Confirmado e agravado (4 losses) | ✅ Resetado |
| CVD/OI chegam zerados | ❌ Brain leu chave errada (sem `:5m`) | Sem ação |
| Logging score=0 nos aborts | ❌ Não era bug, `signal_score` correto | Sem ação |
| Throttle 49 símbolos | ⚠️ Estado desatualizado | Sem ação |
| HFT Penalty floor $20 | ✅ Válido | ✅ Implementado |
| rsi/ema_trend/ob_imbalance zerados | ❌ Logging gap, não pipeline bug | ✅ rsi_5m e ob_imbalance exportados |

---

## Descoberta mais importante

`oi_trend` com r_pb +0.131 é o único preditor de entrada com correlação moderada confirmada nos 40 trades. `trades_1m` tem diferença bruta de 37 pontos (95 vs 58/min) mas r_pb +0.061 — amostra insuficiente.

**Score atual:** média winners 96.4 vs losers 95.7 — diferença de 0.7 pontos. Inútil como preditor.

**Por quê:** CVD, OI change pct, RSI, EMA trend, OB imbalance e liquidações chegavam sem dados relevantes ou com logging gap. Com os fixes do Forge, próxima análise terá dados completos.

---

## Fluxo de colaboração

```text
Brain (análise)                    Forge (execução)
     ↓                                    ↓
     ──── tasks.md (demandas+evidências) ──→ executa
     ↑                                    ↓
     ←─── tasks.md (concluído+arquivo) ───┘
     ↑
     context.md atualizado ← memória compartilhada
```

**Regras:**
1. Brain escreve em `tasks.md` com evidência nos logs
2. Forge verifica no código antes de implementar
3. Forge marca como concluído com arquivo/linha
4. Context.md atualizado após cada evolução relevante

---

## Hierarquia

FORGE é guardião exclusivo do código. Brain é insumo, não ordem.  
Consenso de opinião não substitui verificação de dados.

---

_Brain · SqueezeSniper V4 · 03/06/2026_
