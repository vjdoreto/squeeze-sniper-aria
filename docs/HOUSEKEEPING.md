# HOUSEKEEPING — Regras de Higiene do Projeto
> Guardião: Forge · Autoridade: Bob Doreto · Versão: 1.0 · 09/06/2026

---

## 1. Estrutura Autorizada de Pastas

```
squeeze-sniper/
├── src/               ← código de produção (Forge only)
├── brain/             ← BRAIN_CONTEXT.md + backlog (Brain escreve, Forge commita)
├── aria/
│   ├── ARIA_CONTEXT.md
│   └── scripts/       ← scripts de análise (não vão para produção)
├── assets/            ← logo.png e imagens — sem código executável
├── docs/
│   ├── HOUSEKEEPING.md (este arquivo)
│   └── _arquivo/      ← scripts legados e docs obsoletos arquivados aqui
├── logs/              ← gitignored — gerado em runtime
├── context.md         ← memória mestre compartilhada
├── tasks.md           ← fila Brain → Forge
├── AGENTS.md          ← protocolo dos agentes
├── SQUEEZE_SNIPER_DNA.md ← guardião do DNA (Forge)
├── preferences.json   ← configuração runtime
└── requirements.txt
```

---

## 2. O Que Nunca Vai na Raiz

| Proibido na raiz | Onde vai |
|-----------------|----------|
| Scripts de análise one-shot | `docs/_arquivo/` |
| Imagens e logos | `assets/` |
| Logs e JSONlines | `logs/` (gitignored) |
| Scripts ARIA | `aria/scripts/` |
| Docs de roadmap antigos | `docs/_arquivo/` |
| Sugestões de preferences | `docs/_arquivo/` |

**Regra:** se um arquivo não é código de produção, não fica na raiz. Se não é código nenhum, não fica em `src/`.

---

## 3. Protocolo Fim de Sprint

Ao final de cada sprint, Forge executa nesta ordem:

1. Commita todas as mudanças de código com mensagem descritiva
2. Atualiza `context.md` com resumo do sprint (fixes, decisões, evidências)
3. Atualiza `SQUEEZE_SNIPER_DNA.md` se houve mutação de gates ou parâmetros
4. Atualiza `tasks.md` marcando tasks concluídas e adicionando novas
5. Atualiza `brain/BRAIN_CONTEXT.md` e `aria/ARIA_CONTEXT.md` se há novos dados
6. **Commit e push para o repo privado** (vjdoreto/squeeze-sniper)
7. **Push de `context.md` para o repo público** (vjdoreto/squeeze-sniper-brain) — regra R-03

---

## 4. Protocolo dos Agentes

| Agente | Escreve em | Nunca toca |
|--------|-----------|-----------|
| **Brain** | `tasks.md` (demandas) · `brain/backlog-*.md` | `src/` · `SQUEEZE_SNIPER_DNA.md` |
| **ARIA** | análises para Brain | qualquer arquivo do projeto |
| **Forge** | `src/` · todos os MDs de contexto | nada fora do escopo autorizado por Doreto |
| **Doreto** | autoriza mutações · aprova push live | — |

---

## 5. Git — Mensagens de Commit

Formato padrão:
```
tipo(escopo): descrição curta

Ex: fix(signal_engine): ema_4h_bearish remove AND que anulava gate
    feat(dashboard): placeholder visual para charts sem dados
    chore(docs): atualiza context.md + DNA pós Sprint 5
```

Tipos: `fix` · `feat` · `chore` · `refactor` · `docs`

---

## 6. Regras de Blacklist

**Filosofia:** a blacklist em `preferences.json` deve estar **vazia por padrão**.

Gates dinâmicos substituem listas estáticas:
- `ema_4h_bearish` — bloqueia ativos com tendência bearish em 4h
- `spread_too_high` — bloqueia ativos com spread excessivo
- `cvd_not_confirming` — bloqueia ativos sem confirmação de CVD
- `trades_1m_too_low` — bloqueia ativos sem liquidez suficiente

Se um ativo específico está causando problemas, investigar **qual gate deveria ter bloqueado** e corrigir o gate — não adicionar à blacklist.

---

## 7. O Que Não Commitar

- `logs/` — gitignored, gerado em runtime
- `.env` ou qualquer arquivo com API keys
- Arquivos de cache (`.pkl`, `.db` temporários)
- Screenshots ou outputs de análise one-shot

---

*HOUSEKEEPING.md v1.0 · Forge é guardião · 09/06/2026*
