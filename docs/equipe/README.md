# Checklist por pessoa

Cada arquivo desta pasta é o roteiro individual de um integrante do time: só as Histórias de Usuário (US), arquivos e critérios de aceite que são dela, sprint a sprint. Isso complementa os READMEs por camada (`app/web/README.md`, `app/core/service/README.md`, `app/core/persistencia/README.md`, `app/adapters/README.md`), que mostram a visão por módulo — aqui é a visão por pessoa.

Fonte de verdade para toda a distribuição: `Plano de Ação — Projeto Analisador de Currículos`, Seção 3 (Sprints 1 a 4).

| Pessoa | Arquivo |
|---|---|
| Kevin Carvalho Iqbal | [kevin-carvalho-iqbal.md](./kevin-carvalho-iqbal.md) |
| Gabriel Kalebe | [gabriel-kalebe.md](./gabriel-kalebe.md) |
| Carlos Eduardo Oliveira | [carlos-eduardo-oliveira.md](./carlos-eduardo-oliveira.md) |
| Allan da Silva | [allan-da-silva.md](./allan-da-silva.md) |
| Gustavo Souto Pereira | [gustavo-souto-pereira.md](./gustavo-souto-pereira.md) |
| Vitor Bittencourt dos Santos | [vitor-bittencourt-dos-santos.md](./vitor-bittencourt-dos-santos.md) |

Antes de começar uma US, siga a Seção 1.4 do Plano de Ação: uma US = uma branch (`feature/US-XXX-slug`) = um dono, rebase diário em cima de `develop`, PR pequeno e frequente.

## Status atual (visão geral)

Panorama rápido do board (`@gkalebe's untitled project`), mantido pelo Tech Lead conforme o projeto avança — não substitui o board, é só um resumo para quem não quer abrir o GitHub. Última atualização: Sprint 2.

| Pessoa | Sprint 1 | Sprint 2 | Observação |
|---|---|---|---|
| Kevin | Concluída | US-007 — issues #9/#26, depende de US-006 | — |
| Gabriel Kalebe | Concluída (issues #4, #5, #23, #38) | US-008 — issues #10/#27, depende de US-006 | — |
| Allan | Concluída | US-009 — issues #11/#28 atribuídas, em Backlog (bloqueada atrás de US-008 → US-006) | — |
| Carlos | Sem entrega (cedeu a fatia a Gustavo) | US-006 — issue #8 existe (Sprint 2) mas **pausada**: sem atribuição, em Backlog | Decisão do Tech Lead; retoma quando definido |
| Gustavo | Concluída (US-004 + infra) | Apoio técnico — issue #46, atribuída, em Ready | Sem US formal; segue reforçando infraestrutura de IA |
| Vitor | Concluída (US-005) | A definir com o Tech Lead | — |

Cadeia de dependência da Sprint 2, de olho: US-006 (Carlos, pausada) → US-007 (Kevin) e US-008 (Gabriel Kalebe) → US-009 (Allan). Enquanto Carlos estiver pausado, Kevin/Gabriel/Allan ficam com a US formalmente atribuída mas sem poder concluir a parte que depende da IA — o apoio técnico do Gustavo (issue #46: provedor de IA + CI) adianta o terreno para quando a esteira destravar.
