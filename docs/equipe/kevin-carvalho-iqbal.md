# Kevin Carvalho Iqbal

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Depende de |
|---|---|---|---|---|
| US-001 | Cadastrar conta de usuário | 5 | `web/auth`, `core/service/auth_service`, `core/persistencia/usuario_repository` | — |
| US-002 | Realizar login com e-mail e senha | 3 | `web/auth`, `core/service/auth_service` | US-001 |

Entregue US-001 nos primeiros 2-3 dias: Gabriel Kalebe, Gustavo e Allan dependem dela para destravar US-003, US-004 e US-017 (e US-002, que por sua vez destrava US-004 e a US-005 do Vitor).

## Sprint 2 (Semanas 3-4)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-007 | Comparar currículo com vaga e ver aderência | 13 | `core/service/analisador_service` (Fuzzy Matching/Tokenização) |

Depende da entrega de US-006 (Carlos).

## Sprint 3 (Semanas 5-6)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-010 | Simular entrevista com perguntas por vaga (IA) | 13 | `adapters/ai_service`, `core/service/simulador_service` |

Sua segunda US com integração direta à API generativa (a primeira foi US-007). US-011 (Gabriel Kalebe) depende desta entrega.

## Sprint 4 (Semanas 7-8)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-014 | Receber recomendações para evidenciar competências | 5 | `core/service/plano_service` |

US-015 (Gabriel Kalebe) depende desta entrega.

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
