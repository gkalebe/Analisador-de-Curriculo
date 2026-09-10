# Gabriel Kalebe

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Status |
|---|---|---|---|---|
| US-003 | Recuperar senha via e-mail | 3 | `core/service/auth_service` | Concluída — `solicitar_recuperacao_senha`/`redefinir_senha` + endpoints `POST /usuarios/recuperar-senha` e `POST /usuarios/redefinir-senha` |
| US-019 | Cadastrar informações de vaga no banco | 5 | `core/persistencia/vaga_repository` | Concluída — `criar`, `buscar_por_id`, `listar_por_usuario` |

Ambas dependiam de US-001 (Kevin) só para a base de `usuario_repository`/autenticação existir; implementadas com testes em `tests/unit/test_auth_service.py`, `tests/unit/test_auth_router.py` e `tests/integration/test_vaga_repository.py`. Pendência fora do código: provedor de e-mail transacional para disparar o link de recuperação (Plano de Ação, Seção 4, item 1 — ainda não definido pelo time).

## Sprint 2 (Semanas 3-4)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-008 | Receber diagnóstico crítico do currículo | 8 | `core/service/diagnostico_service` |

Depende da entrega de US-006 (Carlos). US-009 (Allan) depende desta entrega.

## Sprint 3 (Semanas 5-6)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-011 | Receber feedback da resposta de entrevista | 8 | `core/service/simulador_service` |

Depende da entrega de US-010 (Kevin).

## Sprint 4 (Semanas 7-8)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-015 | Visualizar plano de desenvolvimento e certificações sugeridas | 5 | `core/service/plano_service` |

Depende da entrega de US-014 (Kevin).

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
