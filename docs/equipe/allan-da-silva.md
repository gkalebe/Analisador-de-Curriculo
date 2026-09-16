# Allan da Silva

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Depende de |
|---|---|---|---|---|
| US-017 | Excluir conta e dados (LGPD) | 5 | `core/service/auth_service`, `core/persistencia` | US-001 (Kevin) |

US-005 (Colar descrição textual de uma vaga) saiu da sua lista: passou para Vitor Bittencourt dos Santos, que entrou direto na Sprint 1. Nenhuma outra mudança no resto do seu plano.

## Sprint 2 (Semanas 3-4)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-009 | Obter sugestões de reescrita de trechos fracos | 8 | `core/service/diagnostico_service` |

Já criada e atribuída a você no board: issue #11 (back) e #28 (front). Depende da entrega de US-008 (Gabriel Kalebe), que por sua vez depende de US-006 (Carlos) — Carlos está pausado nesta sprint por decisão do Tech Lead, então as duas issues ficam em Backlog (não Ready) até a esteira destravar. Pode adiantar leitura/design enquanto isso, mas não há bloqueio para você resolver sozinho.

## Sprint 3 (Semanas 5-6)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-012 | Acessar templates de currículo ATS-friendly | 5 | `web/templates`, `core/service/template_service` |

US-013 (Carlos) depende desta entrega. Nesta sprint você assume o fluxo de telas/exportação, equilibrando o trabalho mais backend/IA que teve nas Sprints 1 e 2.

**Atualização:** as issues #31/#32 (US-012/US-013) acabaram indo para o kanban atribuídas diretamente a Gabriel Kalebe (rótulo `[FRONT]`), não para você/Carlos como esta tabela original previa. Gabriel implementou as duas de ponta a ponta (front + back) com autorização do time — ver `docs/equipe/gabriel-kalebe.md` e `app/web/README.md` para o que foi entregue. Se você já tinha começado algo em `template_service.py`/`templates_router.py`, avise o time antes de mesclar para evitar conflito.

## Sprint 4 (Semanas 7-8)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-018 | Acessar biblioteca de currículos | 5 | `web/painel`, `core/persistencia/curriculo_repository` |

Depende de US-004 já entregue na Sprint 1 (Gustavo).

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
