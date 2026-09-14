# web/

Camada de apresentação: rotas FastAPI (`routers/`) e schemas Pydantic de request/response, servindo API JSON pura — sem renderização de HTML. As telas ficam em `frontend/` (React + Vite), como uma SPA separada que consome essas rotas via `fetch`.

`templates/` e `static/` ainda existem neste diretório mas estão obsoletos: eram usados pela renderização Jinja2 anterior à migração para React e não são mais referenciados por nenhum router.

Schemas separados por domínio, em vez de um único arquivo: `schemas_auth.py` (cadastro/login/recuperação de senha), `schemas_vaga.py` (vagas) e `schemas_curriculo.py` (upload de currículo). `schemas.py` foi mantido só como um shim de compatibilidade que reexporta os três — prefira importar direto do módulo de domínio em código novo.

Regra da Clean Architecture simplificada: esta camada conhece o `core`, mas o `core` nunca importa nada daqui. Um router só orquestra: recebe a requisição, chama o service correspondente via `Depends`, devolve a resposta. Nenhuma regra de negócio deve morar em um router.

## Routers e donos por Sprint

| Arquivo | Módulo | US | Sprint | Dev |
|---|---|---|---|---|
| `auth_router.py` | Autenticação | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan |
| `analise_router.py` | Upload de currículo | US-004, US-005, US-006, US-007 | 1-2 | Gustavo Souto Pereira, Allan, Kevin, Gabriel Kalebe, Carlos |
| `vagas_router.py` | Vagas | US-019 | 1-2 | Gabriel Kalebe |
| `diagnostico_router.py` | Diagnóstico | US-008, US-009 | 2 | Gabriel Kalebe, Allan |
| `simulador_router.py` | Simulador | US-010, US-011 | 3 | Kevin, Gabriel Kalebe |
| `templates_router.py` | Templates ATS | US-012, US-013 | 3 | Allan, Carlos |
| `painel_router.py` | Plano Dev. / Painel / Biblioteca | US-014 a US-016, US-018 | 4 | Kevin, Gabriel Kalebe, Carlos, Allan |

Cada router já está registrado em `app/main.py`. Ao implementar uma US, adicione o endpoint no arquivo correspondente — não crie um router novo sem necessidade, para não fragmentar módulos que já existem.

## O que falta (routers ainda com só o esqueleto)

- Endpoints reais em `diagnostico_router.py`, `simulador_router.py`, `templates_router.py` e `painel_router.py` (hoje só têm a função `get_*_service` de injeção de dependência). `auth_router.py`, `vagas_router.py` e `analise_router.py` já estão implementados (ver seções abaixo).
- `POST /analises` (rodar uma análise) já está implementado de ponta a ponta — ver seção "Nova análise" abaixo. Devolve `503` se `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` não estiver configurada no `.env`.
- Telas React correspondentes em `frontend/src/pages/` para os módulos ainda pendentes — hoje só existem as telas de autenticação, painel, vagas e upload.
- Validação de payload com Pydantic (schemas de request/response) — já feito por domínio em `schemas_auth.py`, `schemas_vaga.py` e `schemas_curriculo.py`; siga esse padrão para os próximos módulos, não volte a usar um `schemas.py` único.
- Autenticação via JWT nos endpoints que exigem usuário logado além do login em si — hoje o token é gerado no login mas os demais endpoints ainda identificam o usuário por e-mail, não pelo token.

## US-001/US-002 — Cadastro e login (concluídas)

- `POST /usuarios`: cadastra o usuário e responde `201`, ou `409` se o e-mail já existir. O e-mail de confirmação é enviado em background (`BackgroundTasks`), não bloqueia a resposta.
- `POST /usuarios/login`: responde `200` com token JWT e dados do usuário, ou `401` genérico para credenciais inválidas (não revela se o e-mail existe).
- Consumidas pelas telas `frontend/src/pages/Cadastro.jsx` e `Login.jsx` (componente compartilhado `AuthCard.jsx`).

## US-003 — Recuperar senha via e-mail (concluída)

- `POST /usuarios/recuperar-senha`: recebe `{"email": "..."}`, sempre responde `202` com mensagem genérica (não revela se o e-mail existe, por segurança) e dispara `AuthService.solicitar_recuperacao_senha`.
- `POST /usuarios/redefinir-senha`: recebe `{"token": "...", "nova_senha": "..."}` (mínimo 8 caracteres), responde `200` em caso de sucesso ou `400` se o token for inválido/expirado.
- Provedor de e-mail transacional: SendGrid, via `app/adapters/email/`. `AuthService.solicitar_recuperacao_senha` gera o token JWT e chama `EmailAdapter`, que usa a SendGrid API quando `SENDGRID_API_KEY` está configurada no `.env`, com fallback para SMTP puro ou log local em desenvolvimento.
- As telas de formulário (antes renderizadas em `templates/recuperar_senha.html` e `redefinir_senha.html` via `GET`/`POST` com `Form(...)`) foram substituídas pelas páginas React `frontend/src/pages/RecuperarSenha.jsx` e `RedefinirSenha.jsx`, que consomem só as duas rotas JSON acima. As rotas HTML antigas foram removidas deste router.

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.

## US-019 — Cadastrar informações de vaga no banco (concluída, em `vagas_router.py`)

- `GET /api/vagas?email=...`: lista as vagas já salvas pelo usuário identificado por e-mail, `404` se o e-mail não estiver cadastrado.
- `POST /api/vagas`: recebe `{"email", "titulo", "descricao", "requisitos", "area"}` (JSON), chama `AnalisadorService.cadastrar_vaga` e responde `201` com a vaga criada, ou `400` se a descrição estiver vazia ou acima do limite configurado em `max_vaga_description_chars`.
- Identificação do usuário: como o login não gera uma sessão persistida no back (o token JWT fica só no `localStorage` do front), a tela usa o e-mail (query string) resolvido via `UsuarioRepository.buscar_por_email` como identificador — mesmo padrão usado no upload de currículo.
- Tela: `frontend/src/pages/NovaVaga.jsx` — formulário de cadastro (título opcional, descrição obrigatória, requisitos e área opcionais) e lista de vagas salvas para reaproveitar dados.
- Testes: `tests/unit/test_analisador_service.py` (regras de negócio) e `tests/unit/test_vagas_router.py` (HTTP, com fakes via `app.dependency_overrides`).

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.

## US-004 a US-007 — Upload e extração de currículo (rota concluída, em `analise_router.py`)

- `POST /analises/upload` (multipart/form-data): recebe `email` + `file` (PDF ou DOCX, até `max_upload_size_mb`), identifica o usuário por e-mail (`404` se não encontrado), extrai o texto via `CurriculoParser` e responde `201` com `{"id_curriculo", "nome_arquivo", "tamanho_texto_extraido"}`, ou `400` para formato não suportado ou arquivo acima do limite.
- Antes usava um usuário mock fixo e renderizava `templates/upload.html`; hoje é JSON puro, identificado por e-mail como os demais endpoints, consumido por `frontend/src/pages/UploadCurriculo.jsx` (drag-and-drop).
- Testes: `tests/unit/test_analise_router.py`.

### Nova análise (currículo x vaga) — concluída (Gabriel Kalebe, com autorização do time para US-006/US-007)

- `POST /analises` (multipart/form-data): recebe `email`, `id_vaga` e `file`, identifica o usuário e a vaga (`404` se algum não existir), extrai o texto do currículo e chama `AnalisadorService.analisar_curriculo_para_vaga`, que já roda a comparação por IA de verdade (`app/adapters/ai_service/ai_service_adapter.py`) e persiste em `Analise` (`app/core/persistencia/analise_repository.py`). Responde `201` com `{"id_analise", "id_curriculo", "id_vaga", "pontuacao", "observacoes", "data_analise"}`.
- `GET /analises?email=...`: lista as análises já feitas pelo usuário.
- Requer `GEMINI_API_KEY` ou `ANTHROPIC_API_KEY` no `.env` (ver `.env.example`) — sem nenhuma das duas configuradas, `POST /analises` responde `503` com mensagem explicando o que falta, em vez de um erro 500 cru. Se a API de IA não responder em 30s ou recusar a requisição, também responde `503` (em vez de a tela ficar carregando indefinidamente) — ver `IAIndisponivelError` em `app/adapters/README.md`. Modelo usado é configurável via `GEMINI_MODEL_NAME`/`ANTHROPIC_MODEL_NAME` (padrão `gemini-flash-latest`/`claude-3-5-haiku-20241022`).
- Contrato do retorno do `AIServiceAdapter.comparar_curriculo_vaga`: uma string JSON `{"pontuacao": 0-100, "observacoes": "..."}` — ver `AnalisadorService._interpretar_resultado_ia` (tolera blocos de markdown ao redor do JSON). Combine com quem mexer no prompt antes de mudar esse formato.
- Tela: `frontend/src/pages/NovaAnalise.jsx` — escolhe uma vaga salva e envia um currículo. `Cadastrar vaga` (`NovaVaga.jsx`) e `Enviar currículo` (`UploadCurriculo.jsx`) foram separadas dessa tela (antes a de vaga usava o título errado "Nova análise"); as três agora compartilham `frontend/src/components/Sidebar.jsx`.
- Testes: `tests/unit/test_analise_router.py`, `tests/unit/test_analisador_service.py`, `tests/unit/test_ai_service_adapter.py`.
