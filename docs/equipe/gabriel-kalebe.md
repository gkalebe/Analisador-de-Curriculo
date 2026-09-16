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
| US-012 | Acessar templates de currículo ATS-friendly | 5 | `web/templates`, `core/service/template_service` |
| US-013 | Aplicar currículo a template e exportar PDF/DOCX | 8 | `core/service/template_service`, `adapters/curriculo_exporter` |

Depende da entrega de US-010 (Kevin).

US-012 e US-013 chegaram para mim via issues #31 e #32 no kanban (ambas com o rótulo `[FRONT]`, atribuídas diretamente a mim pelo time), embora a tabela de ownership por módulo em `app/web/README.md` credite essas duas US a Allan/Carlos. Como as issues do board estavam comigo e envolviam tanto tela quanto o back que ainda não existia (`template_service.py`/`templates_router.py` só tinham o esqueleto), pedi e recebi autorização do time para implementar as duas pontas — mesmo padrão já usado nas US-005/006/007 (Sprint 1-2). Entregue: coluna `Curriculo.texto_extraido` (nova, com migração), `AIServiceAdapter.extrair_dados_estruturados`, o adapter `curriculo_exporter/` (PDF via fpdf2 + DOCX via python-docx, 3 templates), `TemplateService` e `templates_router.py` completos, e as telas `GaleriaTemplates.jsx`/`PreviewExportarCurriculo.jsx`. De passagem, corrigi também um bug pré-existente em `analise_router.py`: `GET /analises` não convertia `NotImplementedError` em `501` (só `POST /analises` fazia isso) — não relacionado a US-012/013, mas notado ao rodar a suíte de testes completa antes de entregar. Ver `app/adapters/README.md`, `app/web/README.md` e `app/core/service/README.md` para detalhes técnicos.

## Sprint 4 (Semanas 7-8)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-015 | Visualizar plano de desenvolvimento e certificações sugeridas | 5 | `core/service/plano_service` |

Depende da entrega de US-014 (Kevin).

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
