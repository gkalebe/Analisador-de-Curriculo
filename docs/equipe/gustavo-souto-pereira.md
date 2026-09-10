# Gustavo Souto Pereira

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Depende de |
|---|---|---|---|---|
| US-004 | Fazer upload do currículo (PDF/DOCX) | 5 | `adapters/curriculo_parser`, `web/analise` | US-002 (Kevin) |
| — | Apoio técnico: Docker, CI, Alembic (migração inicial) | — | Infraestrutura | — |

Você entrou já na Sprint 1 assumindo a fatia que seria de Carlos (US-004 + apoio de infraestrutura); Carlos volta a partir da Sprint 2 com o que já estava previsto para ele, sem nenhuma outra mudança no plano.

A migração inicial do Alembic (`alembic revision --autogenerate -m "..."` a partir de `core/persistencia/models.py`, que já está completo) e a validação do `docker-compose.yml`/CI são a sua entrega de infraestrutura desta sprint — sem elas, ninguém do time consegue rodar migração real contra o Postgres em nuvem.

## Sprints 2 a 4

O Plano de Ação não define uma US fixa para você além da Sprint 1 — seu ponto de entrada foi pensado para dar flexibilidade ao time. Alinhe com o Tech Lead/Scrum Master no fim da Sprint 1 se você continua reforçando infraestrutura (Docker, deploy, Alembic) ao longo do projeto ou se assume uma US de sprint futura, dependendo de como a carga do time estiver distribuída.

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
