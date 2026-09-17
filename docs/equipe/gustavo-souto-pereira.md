# Gustavo Souto Pereira

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Depende de |
|---|---|---|---|---|
| US-004 | Fazer upload do currículo (PDF/DOCX) | 5 | `adapters/curriculo_parser`, `web/analise` | US-002 (Kevin) |
| — | Apoio técnico: Docker, CI, Alembic (migração inicial) | — | Infraestrutura | — |

Você entrou já na Sprint 1 assumindo a fatia que seria de Carlos (US-004 + apoio de infraestrutura); Carlos volta a partir da Sprint 2 com o que já estava previsto para ele, sem nenhuma outra mudança no plano.

A migração inicial do Alembic (`alembic revision --autogenerate -m "..."` a partir de `core/persistencia/models/`, que já está completo) e a validação do `docker-compose.yml`/CI são a sua entrega de infraestrutura desta sprint — sem elas, ninguém do time consegue rodar migração real contra o Postgres em nuvem.

## Sprint 2 (Semanas 3-4)

Definido: você segue reforçando infraestrutura, agora com foco no núcleo de IA que arranca nesta sprint (US-006, US-007, US-008). Não é uma US formal — não tem pontuação no Plano de Ação — mas é trabalho real de apoio, tracked na issue #46.

| Item | Descrição | Módulo |
|---|---|---|
| Issue #46 | Apoio técnico Sprint 2 — configurar provedor de IA do `AIServiceAdapter` (Gemini x Claude, ainda em aberto), estender CI para testes de integração de IA, apoiar Carlos no início do `AIServiceAdapter` | `adapters/ai_service`, CI |

O pareamento com Carlos (item 3 da issue) só acontece quando ele retomar a US-006 — por ora, foque na configuração do provedor de IA e na extensão do CI, que não dependem dele.

## Sprints 3 e 4

Ainda em aberto. Alinhe com o Tech Lead/Scrum Master no fim da Sprint 2 se você continua reforçando infraestrutura ou se assume uma US de sprint futura, dependendo de como a carga do time estiver distribuída.

**Atualização (Sprint 3):** as issues `[BACK] US-012` (#12) e `[BACK] US-013` (#13) estavam atribuídas a você no board (em Ready, sem trabalho iniciado). Gabriel Kalebe recebeu as issues `[FRONT] US-012`/`[FRONT] US-013` (#31/#32) e, com autorização do time, implementou os dois lados (front + back) na mesma entrega — as issues #12/#13 foram reatribuídas a ele e fechadas como concluídas para refletir isso, sem que você precisasse iniciar esse trabalho. Se você já tinha algo em andamento em `template_service.py`/`templates_router.py`, avise o time para evitar retrabalho.

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
