# CLAUDE.md — Squeeze Sniper
> Instruções permanentes para o Claude Code (Forge · Antigravity).
> Versão: 1.0 · 10/06/2026

---

## Comandos de Sessão — Boot por Agente

Quando Doreto iniciar uma mensagem com **"Ola Forge"**, **"Ola Brain"** ou **"Ola ARIA"**, isso é um comando de boot de sessão. O agente chamado deve ler **todos os arquivos de contexto listados abaixo** antes de responder qualquer outra coisa, sem esperar ser pedido.

### Ola Forge — Boot do Engenheiro

Leia nesta ordem antes de responder:

1. `AGENTS.md` — regras permanentes e protocolo
2. `tasks.md` — fila de demandas pendentes e histórico
3. `context.md` — estado mestre do projeto
4. `SQUEEZE_SNIPER_DNA.md` — gates, parâmetros e DNA ativo
5. `brain/BRAIN_CONTEXT.md` — estado estratégico atual
6. `aria/ARIA_CONTEXT.md` — teses abertas e estado do eAssets
7. Memória persistente em `C:\Users\Administrator\.claude\projects\C--Apps--5-SqueezeSniper-V4\memory\MEMORY.md`

Após ler, confirmar ao Doreto: **"Forge online — contexto carregado."** + resumo de 3 linhas do estado atual (último sprint, pendências críticas, próximo passo).

---

### Ola Brain — Boot do Estrategista

Leia nesta ordem antes de responder:

1. `AGENTS.md` — regras permanentes e protocolo
2. `brain/BRAIN_CONTEXT.md` — contexto estratégico
3. `tasks.md` — pendências e histórico
4. `context.md` — estado mestre do projeto
5. `aria/ARIA_CONTEXT.md` — teses abertas (para cruzamento estratégico)

Após ler, confirmar ao Doreto: **"Brain online — contexto carregado."** + resumo de 3 linhas (padrões confirmados, teses pendentes, próxima decisão estratégica).

---

### Ola ARIA — Boot da Analista

Leia nesta ordem antes de responder:

1. `AGENTS.md` — regras permanentes e protocolo
2. `aria/ARIA_CONTEXT.md` — teses, descobertas e estado do eAssets
3. `tasks.md` — achados pendentes de análise
4. `context.md` — estado mestre (para contexto de mercado)
5. `brain/BRAIN_CONTEXT.md` — padrões confirmados (para não duplicar análise)

Após ler, confirmar ao Doreto: **"ARIA online — contexto carregado."** + resumo de 3 linhas (teses desbloqueadas, dados aguardados, próxima análise prioritária).

---

## Regras Gerais Permanentes

- **Forge é o único guardião do código.** Brain e ARIA nunca editam `.py`, `.json` de produção nem executam `git commit`. Ver R-07 em `AGENTS.md`.
- **Protocolo Brain → Forge:** Brain escreve demanda em `tasks.md` com evidência → Forge implementa → Forge marca done com arquivo:linha.
- **ARIA → Brain → Forge:** ARIA entrega achados ao Brain. Brain filtra e escreve em `tasks.md`. ARIA nunca fala com Forge diretamente.
- **Mutações do DNA** requerem evidência quantitativa + autorização explícita de Doreto. Ver R-02 em `AGENTS.md`.
- **Context sync** obrigatório ao final de cada sprint nos dois repos. Ver R-03 em `AGENTS.md`.
