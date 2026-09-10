# web/

Camada de apresentação: rotas FastAPI (`routers/`), templates Jinja2 (`templates/`) e estáticos (`static/`).

Regra da Clean Architecture simplificada: esta camada conhece o `core`, mas o `core` nunca importa nada daqui. Um router só orquestra: recebe a requisição, chama o service correspondente via `Depends`, devolve a resposta. Nenhuma regra de negócio deve morar em um router.

## Routers e donos por Sprint

| Arquivo | Módulo | US | Sprint | Dev |
|---|---|---|---|---|
| `auth_router.py` | Autenticação | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan |
| `analise_router.py` | Análise | US-004, US-005, US-006, US-007, US-019 | 1-2 | Gustavo Souto Pereira, Allan, Kevin, Carlos |
| `diagnostico_router.py` | Diagnóstico | US-008, US-009 | 2 | Gabriel Kalebe, Allan |
| `simulador_router.py` | Simulador | US-010, US-011 | 3 | Kevin, Gabriel Kalebe |
| `templates_router.py` | Templates ATS | US-012, US-013 | 3 | Allan, Carlos |
| `painel_router.py` | Plano Dev. / Painel / Biblioteca | US-014 a US-016, US-018 | 4 | Kevin, Gabriel Kalebe, Carlos, Allan |

Cada router já está registrado em `app/main.py`. Ao implementar uma US, adicione o endpoint no arquivo correspondente — não crie um router novo sem necessidade, para não fragmentar módulos que já existem.

## O que falta (Sprint 0 entregou só o esqueleto)

- Endpoints reais (hoje os routers só têm a função `get_*_service` de injeção de dependência).
- Templates HTML das telas de cada módulo (hoje só existe `index.html`).
- Validação de payload com Pydantic (schemas de request/response) — criar em `app/web/schemas.py` quando a primeira US precisar.
- Autenticação via JWT nos endpoints que exigem usuário logado (US-002 em diante).

Referência de critérios de aceite: Levantamento de Requisitos v1.1, Seção 6.2.
