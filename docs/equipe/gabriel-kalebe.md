# Gabriel Kalebe

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Status |
|---|---|---|---|---|
| US-003 | Recuperar senha via e-mail | 3 | `core/service/auth_service` | Concluída — back (issue #4: `solicitar_recuperacao_senha`/`redefinir_senha` + endpoints `POST /usuarios/recuperar-senha` e `POST /usuarios/redefinir-senha`) e front (issue #23: tela `GET /usuarios/recuperar-senha` + `POST /usuarios/recuperar-senha/formulario`, com mensagem genérica e opção de reenvio) |
| US-019 | Cadastrar informações de vaga no banco | 5 | `core/persistencia/vaga_repository`, `web/analise` | Concluída — back (issue #5: `criar`, `buscar_por_id`, `listar_por_usuario`) e front (issue #38: tela `GET /analises/vagas/nova` + `POST /analises/vagas`, com listagem de vagas salvas para reuso) |

Ambas dependiam de US-001 (Kevin) só para a base de `usuario_repository`/autenticação existir. Como US-002 (login, Kevin) ainda não está pronta, a tela de US-019 identifica o usuário por e-mail (campo temporário no formulário) — trocar por sessão/JWT assim que o login estiver disponível. A tela de US-003 não depende de login (é justamente para quem esqueceu a senha), então não tem esse problema. Testes em `tests/unit/test_auth_service.py`, `tests/unit/test_auth_router.py`, `tests/unit/test_analisador_service.py`, `tests/unit/test_analise_router.py` e `tests/integration/test_vaga_repository.py`. Pendência fora do código: provedor de e-mail transacional para disparar o link de recuperação (Plano de Ação, Seção 4, item 1 — ainda não definido pelo time); o front já está pronto para quando isso for decidido.

**Sprint 1 concluída** — issues #4, #5, #23 e #38 (as quatro atribuídas a mim) estão fechadas/prontas para revisão.

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
