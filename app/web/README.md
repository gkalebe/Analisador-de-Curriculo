# web/

Camada de apresentação: rotas FastAPI (`routers/`), templates Jinja2 (`templates/`) e estáticos (`static/`).

Regra da Clean Architecture simplificada: esta camada conhece o `core`, mas o `core` nunca importa nada daqui. Um router só orquestra: recebe a requisição, chama o service correspondente via `Depends`, devolve a resposta. Nenhuma regra de negócio deve morar em um router.

## Routers e donos por Sprint

| Arquivo | Módulo | US | Sprint | Dev |
|---|---|---|---|---|
| `auth_router.py` | Autenticação | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan |
| `analise_router.py` | Análise | US-004, US-005, US-006, US-007, US-019 | 1-2 | Gustavo Souto Pereira, Allan, Kevin, Gabriel Kalebe, Carlos |
| `diagnostico_router.py` | Diagnóstico | US-008, US-009 | 2 | Gabriel Kalebe, Allan |
| `simulador_router.py` | Simulador | US-010, US-011 | 3 | Kevin, Gabriel Kalebe |
| `templates_router.py` | Templates ATS | US-012, US-013 | 3 | Allan, Carlos |
| `painel_router.py` | Plano Dev. / Painel / Biblioteca | US-014 a US-016, US-018 | 4 | Kevin, Gabriel Kalebe, Carlos, Allan |

Cada router já está registrado em `app/main.py`. Ao implementar uma US, adicione o endpoint no arquivo correspondente — não crie um router novo sem necessidade, para não fragmentar módulos que já existem.

## O que falta (Sprint 0 entregou só o esqueleto)

- Endpoints reais (hoje os routers só têm a função `get_*_service` de injeção de dependência) — exceto `auth_router.py`, que já tem `POST /usuarios/recuperar-senha` e `POST /usuarios/redefinir-senha` (US-003, ver abaixo).
- Templates HTML das telas de cada módulo (hoje só existe `index.html`).
- Validação de payload com Pydantic (schemas de request/response) — `app/web/schemas.py` já existe, criado junto com US-003; adicione os schemas das próximas US aqui, não crie um segundo arquivo.
- Autenticação via JWT nos endpoints que exigem usuário logado (US-002 em diante).

## US-003 — Recuperar senha via e-mail (concluída nesta camada)

- `POST /usuarios/recuperar-senha`: recebe `{"email": "..."}`, sempre responde `202` com mensagem genérica (não revela se o e-mail existe, por segurança) e dispara `AuthService.solicitar_recuperacao_senha`.
- `POST /usuarios/redefinir-senha`: recebe `{"token": "...", "nova_senha": "..."}` (mínimo 8 caracteres), responde `200` em caso de sucesso ou `400` se o token for inválido/expirado.
- Pendência fora do escopo de código: qual provedor de e-mail transacional vai efetivamente enviar o link com o token (Seção 4, item 1 do Plano de Ação — SendGrid, Resend etc. ainda não definido). Hoje o service só gera o token; o disparo do e-mail em si entra quando isso for decidido.
- `GET /usuarios/recuperar-senha`: renderiza `templates/recuperar_senha.html` — formulário com um campo de e-mail.
- `POST /usuarios/recuperar-senha/formulario`: recebe o e-mail do formulário, chama `AuthService.solicitar_recuperacao_senha` e volta a renderizar a mesma tela com a mensagem genérica de sucesso ("se o e-mail estiver cadastrado...") — nunca confirma nem nega se o e-mail existe, conforme critério de aceite da issue #23. O botão vira "Reenviar link" após o primeiro envio, cobrindo o critério de reenvio (o link expira em 60 minutos, `password_reset_expire_minutes` em `app/core/config.py`).
- Essa rota é separada da `POST /usuarios/recuperar-senha` (JSON, usada por clientes que não são o formulário HTML) para não misturar `Form(...)` com o `SolicitarRecuperacaoSenhaRequest` no mesmo path.

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.

## US-019 — Cadastrar informações de vaga no banco (front concluído nesta camada)

- `GET /analises/vagas/nova`: renderiza `templates/vagas_nova.html` — formulário de cadastro de vaga (título opcional, descrição obrigatória, requisitos e área opcionais) e, quando `?email=` é informado e corresponde a um usuário existente, lista as vagas já salvas por ele para reaproveitar dados sem digitar tudo de novo.
- `POST /analises/vagas`: recebe os campos do formulário, chama `AnalisadorService.cadastrar_vaga` e volta a renderizar a mesma tela com mensagem de sucesso ou erro (`400` se e-mail não encontrado, descrição vazia ou acima do limite configurado em `max_vaga_description_chars`).
- Identificação do usuário: como US-002 (login, Kevin) ainda não existe, a tela usa um campo de e-mail (form/query string) resolvido via `UsuarioRepository.buscar_por_email` como identificador temporário — trocar por sessão/JWT assim que o login estiver pronto. Isso foi proposital para não invadir a US-002, que não é escopo desta entrega.
- Testes: `tests/unit/test_analisador_service.py` (regras de negócio) e `tests/unit/test_analise_router.py` (HTTP, com fakes via `app.dependency_overrides`).

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.
