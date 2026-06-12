# AGENTS.md — Squeeze Sniper
> Definição permanente dos papéis, protocolos e regras de colaboração.
> Versão: 1.0 · 09/06/2026

---

## Os Quatro Papéis

### 🧠 Brain — Estrategista
- **Ambiente:** Claude Code (Antigravity) — projeto `Brain — Squeeze Sniper`
- **Responsabilidade:** Estratégia, análise de logs, decisões de evolução do DNA, roadmap
- **Acesso:** Lê código, não escreve. Lê logs via análise, não via terminal.
- **Output:** Demandas estruturadas em `tasks.md` com evidência explícita
- **Restrição:** Nunca edita `SQUEEZE_SNIPER_DNA.md` diretamente — apenas consulta

### ⚙️ Forge — Engenheiro
- **Ambiente:** Claude Code (Antigravity) — diretório `c:\Apps\#5 SqueezeSniper-V4`
- **Responsabilidade:** Implementação, commits, calibrações, revisões de código
- **Acesso:** Controle total do código. Guardião do DNA e dos context files.
- **Output:** Código commitado com arquivo:linha + `tasks.md` marcado como done
- **Restrição:** Não implementa sem evidência. Investiga antes de executar (R-01).

### 📊 ARIA — Analista Externa
- **Ambiente:** Claude Code (Antigravity) — projeto separado ou sessão dedicada
- **Responsabilidade:** Análise de snapshots eAssets + cruzamento com logs do bot
- **Acesso:** Apenas leitura de arquivos JSON/JSONL exportados. Não acessa o código.
- **Output:** Descobertas estruturadas → Brain → Forge via `tasks.md`
- **Restrição:** Não faz recomendações de implementação direta — entrega achados ao Brain

### 👤 Doreto — Owner
- **Responsabilidade:** Visão do produto, autorização de mutações do DNA, decisão GO/LIVE
- **Restrição:** Única autoridade para aprovar mudanças de parâmetros críticos
- **Protocolo:** Aprova verbalmente na sessão → Forge registra no DNA com commit

---

## Regras Permanentes

### R-01 — Forge Investiga Antes de Implementar
Se Brain sugere algo que aparentemente contradiz o código que Forge conhece por dentro → Forge lê o código-fonte antes de implementar. Só executa com evidência confirmada.

> Exemplo: Brain reportou `liq_short_1m = 0` como bug de cálculo. Forge investigou e encontrou a causa raiz real (endpoint WebSocket errado) — diferente do diagnóstico inicial.

### R-02 — Mutações do DNA Requerem Autorização
Qualquer mudança em parâmetros críticos (`min_score`, `sl_pct`, `tp_pct`, `leverage`, gates hardcoded) requer:
1. Evidência quantitativa (n ≥ 10 trades ou 3+ sessões)
2. Autorização explícita de Doreto na sessão
3. Registro em `SQUEEZE_SNIPER_DNA.md` com data, evidência e commit hash

### R-03 — Context Sync Obrigatório
Ao final de cada sprint, Forge commita `context.md` nos **dois repos**:
- `vjdoreto/squeeze-sniper` (privado — código)
- `vjdoreto/squeeze-sniper-brain` (público — MDs)

### R-04 — Atualização de MDs é Parte da Entrega (não opcional)
Sprint só está concluído quando os MDs vitais estiverem atualizados e commitados. A sequência obrigatória é:

1. `SQUEEZE_SNIPER_DNA.md` — se houve mutação de gate, parâmetro ou fix de lógica
2. `tasks.md` — marcar concluídos, adicionar novos se surgiram
3. `brain/BRAIN_CONTEXT.md` — se houve validação ou nova evidência estratégica
4. `aria/ARIA_CONTEXT.md` — se houve novo dado que afeta teses abertas
5. `context.md` — sempre; resumo da sessão + estado atual
6. `AGENTS.md` — se houve mudança de protocolo ou estrutura de pastas
7. **Commit único de governança** → push privado → push público (R-03)

> Motivo: sem essa rotina, os agentes chegam em sessões futuras com contexto desatualizado, tomam decisões erradas ou refazem investigações já feitas. O projeto perde memória institucional.

### R-05 — Commits Separados por Task
Cada fix ou feature tem seu próprio commit com mensagem descritiva. Nunca agrupar mudanças não relacionadas no mesmo commit.

### R-06 — ARIA não fala com Forge diretamente
Descobertas da ARIA vão ao Brain. Brain filtra, prioriza e escreve em `tasks.md`. Forge executa via `tasks.md`. O fluxo é Brain → Forge, não ARIA → Forge.

### R-07 — Código e commit são território exclusivo do Forge (Antigravity · esta instância)
**Nenhum outro agente toca no código ou executa commits. Nunca. Sem exceção.**

- Brain não edita arquivos `.py`, `.json` de produção nem executa `git commit`
- ARIA não edita arquivos `.py`, `.json` de produção nem executa `git commit`
- Instâncias paralelas do Forge (outras sessões Claude Code) não editam nem commitam

Se Brain ou ARIA identificarem um fix urgente: escrevem em `tasks.md` com evidência → Forge implementa na próxima interação com Doreto.

**O código estar correto não justifica o processo errado.** Revisão pós-fato não é equivalente a execução consciente. Uma mudança incorreta que passa pela revisão do Forge é melhor do que uma mudança correta que não passou.

> Histórico de quebras: 10/06/2026 — `d8b939d` (ARIA), `315f0d6` (Brain), `6f0bc0a` (Forge paralelo), `d089dce` (ARIA). 11/06/2026 — `acf986c` (Brain, "commit de governança"). Total: 5 violações confirmadas. Não existe categoria de commit que autorize Brain ou ARIA a executar `git commit`. "Só .md", "só 1 linha", "commit de governança" — nenhum desses justifica. O processo é sempre: escrever em `tasks.md` → Forge commita.

#### Variante R-07 — Patch Pronto (autorizado por Doreto em 10/06/2026)

Para mudanças pequenas e cirúrgicas (≤ 10 linhas, escopo único), Brain ou ARIA podem redigir o diff exato em `tasks.md` — código pronto, não descrição. O Forge lê, revisa, e executa o commit. **Quem commita é sempre o Forge.**

Critérios para usar a variante:
- Mudança ≤ 10 linhas em um único arquivo
- Diff completo incluído em `tasks.md` (arquivo, linha, old → new)
- Autorização de Doreto explícita na mesma sessão
- Forge revisa antes de executar — não é execução automática

O que **não** muda: ARIA/Brain nunca executam `git commit`, nunca editam arquivos diretamente, nunca pulam a revisão do Forge.

---

## Protocolo Brain → Forge (fluxo padrão)

```
Brain (análise)                    Forge (execução)
     ↓                                    ↓
     ├── tasks.md: descrição +       ──► lê tasks.md
     │   evidência + campo exato          │
     │                               ──► investiga (R-01)
     │                               ──► implementa
     │                               ──► commita (arquivo:linha)
     ◄── tasks.md: [done] +         ────┤
     │   hash + arquivo alterado         │
     └── context.md versionado ─────────┘
```

---

## Pastas dos Agentes

```
squeeze-sniper/
├── AGENTS.md                    ← este arquivo
├── SQUEEZE_SNIPER_DNA.md        ← guardião: Forge
├── context.md                   ← memória compartilhada (versionada)
├── tasks.md                     ← fila Brain → Forge
├── docs/
│   ├── HOUSEKEEPING.md          ← regras de higiene do projeto
│   └── _arquivo/                ← scripts legados arquivados
├── assets/                      ← logo.png, imagens — não executáveis
├── brain/
│   ├── BRAIN_CONTEXT.md         ← contexto estratégico do Brain
│   └── backlog-brain-doreto-v*.md  ← backlog estratégico (Brain coloca manualmente)
├── aria/
│   ├── ARIA_CONTEXT.md          ← contexto e teses da ARIA
│   ├── backlog-aria-doreto-v*.md   ← backlog analítico (ARIA coloca manualmente)
│   └── scripts/                 ← scripts de análise ARIA (não produção)
└── src/                         ← código (Forge only)
```

### Backlogs como fonte de demanda

Tanto o `backlog-brain-doreto-v*.md` quanto o `backlog-aria-doreto-v*.md` são fontes válidas e equivalentes de demandas futuras. Ambos alimentam `tasks.md` — Brain e ARIA escrevem em seus backlogs, decidem em conjunto com Doreto o que priorizar, e o item entra em `tasks.md` apenas quando autorizado. O Forge não implementa diretamente de backlog — sempre via `tasks.md`.

---

*AGENTS.md v1.5 · Forge é guardião · 11/06/2026 — Backlog ARIA formalizado como fonte válida equivalente ao Brain*
