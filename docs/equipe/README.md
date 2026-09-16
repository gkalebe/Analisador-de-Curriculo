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

Panorama rápido do board (`@gkalebe's untitled project`), mantido pelo Tech Lead conforme o projeto avança — não substitui o board, é só um resumo para quem não quer abrir o GitHub. Última atualização: Sprint 4.

| Pessoa | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 | Observação |
|---|---|---|---|---|---|
| Kevin | Concluída | US-007 — issues #9/#26, depende de US-006 | A definir com o Tech Lead | A definir com o Tech Lead | — |
| Gabriel Kalebe | Concluída (issues #4, #5, #23, #38) | US-008 — issues #10/#27, depende de US-006 | US-012/US-013 — issues #31/#32, concluídas (front + back, com autorização do time) | US-016 (back) — issue #20, concluída | Ver `docs/equipe/gabriel-kalebe.md` |
| Allan | Concluída | US-009 — issues #11/#28 atribuídas, em Backlog (bloqueada atrás de US-008 → US-006) | US-012 nominalmente atribuída a você no plano original, mas as issues #31/#32 foram para Gabriel Kalebe no board | A definir com o Tech Lead | Ver nota em `docs/equipe/allan-da-silva.md` |
| Carlos | Sem entrega (cedeu a fatia a Gustavo) | US-006 — issue #8 existe (Sprint 2) mas **pausada**: sem atribuição, em Backlog | US-013 nominalmente atribuída a você no plano original, mas as issues #31/#32 foram para Gabriel Kalebe no board | A definir com o Tech Lead | Ver nota em `docs/equipe/carlos-eduardo-oliveira.md`; US-006 (Sprint 2) segue aberta/pausada e é sua para concluir |
| Gustavo | Concluída (US-004 + infra) | Apoio técnico — issue #46, atribuída, em Ready | A definir com o Tech Lead | A definir com o Tech Lead | — |
| Vitor | Concluída (US-005) | A definir com o Tech Lead | A definir com o Tech Lead | A definir com o Tech Lead | — |

Cadeia de dependência da Sprint 2, de olho: US-006 (Carlos, pausada) → US-007 (Kevin) e US-008 (Gabriel Kalebe) → US-009 (Allan). Enquanto Carlos estiver pausado, Kevin/Gabriel/Allan ficam com a US formalmente atribuída mas sem poder concluir a parte que depende da IA — o apoio técnico do Gustavo (issue #46: provedor de IA + CI) adianta o terreno para quando a esteira destravar.

Sprint 3: as issues #31/#32 (US-012/US-013, template ATS + exportação) chegaram no kanban já atribuídas a Gabriel Kalebe com o rótulo `[FRONT]`, embora o plano original (e a tabela de ownership em `app/web/README.md`) previsse Allan (US-012) e Carlos (US-013). Gabriel pediu e recebeu autorização do time para implementar as duas de ponta a ponta, já que as issues envolviam tanto tela quanto o back que ainda não existia. Como parte dessa entrega, as issues `[BACK] US-012`/`[BACK] US-013` (#12/#13, que estavam com Gustavo, sem trabalho iniciado) foram reatribuídas a Gabriel e fechadas junto, já que o back das duas foi implementado na mesma entrega. US-006 (Carlos) continua a pendência mais antiga em aberto do projeto — a comparação currículo x vaga em si já funciona (implementada por Gabriel com autorização, ver Sprint 2), mas os critérios de aceite completos de US-006 (percentual de aderência detalhado, palavras-chave específicas ausentes) ainda não foram feitos por ninguém.

Sprint 4: a issue #20 (`[BACK] US-016`, histórico de análises e lacunas recorrentes) veio atribuída a Gabriel Kalebe e foi concluída. A issue irmã `[FRONT] US-016` (#35, dashboard/gráfico) segue sem dono no kanban — não foi implementada agora porque não estava atribuída a Gabriel; alguém do time precisa assumi-la (ou pedir autorização para o Gabriel seguir com ela também).
