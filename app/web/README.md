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

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.
