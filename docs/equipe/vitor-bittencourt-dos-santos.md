# Vitor Bittencourt dos Santos

Entrou direto na Sprint 1, assumindo a US-005 que era do Allan (nenhuma mudança no restante do plano dele — ele segue normalmente com US-017 nesta sprint e o que já estava previsto a partir da Sprint 2).

## Sprint 1 (Semanas 1-2)

| US | Título | Pontos | Módulo | Depende de |
|---|---|---|---|---|
| US-005 | Colar descrição textual de uma vaga | 3 | `web/analise` | US-002 (Kevin) |

Como US-005 depende de US-002 (login), alinhe com o Kevin a previsão de entrega antes de começar — enquanto isso, dá pra já ler `app/web/README.md` e `app/core/service/README.md` pra entender a Clean Architecture simplificada do projeto (rota → service → repositório) e ver o que a Sprint 0 já deixou pronto no `analise_router.py`/`analisador_service.py`.

## A partir da Sprint 2

Ainda não fixado no Plano de Ação. Quando chegar a Sprint 2, alinhe com o Tech Lead/Scrum Master se você continua reforçando o módulo de análise (`web/analise`, `analisador_service`) ou assume um módulo novo — o plano original sugeria Sprint 3/4 com um módulo completo (ex.: Painel + Biblioteca) e, no ciclo pós-MVP, os itens fora do escopo das 19 US (novos perfis de usuário, idiomas, certificações — Seção 6.5 do Documento de Arquitetura).

## Antes de começar

1. Siga a Seção 1.4 do Plano de Ação: uma US = uma branch (`feature/US-005-colar-descricao-vaga`) = um dono, rebase diário em cima de `develop`, PR pequeno e frequente.
2. Confira os critérios de aceite (DADO/QUANDO/ENTÃO) de US-005: Levantamento de Requisitos v1.1, Seção 6.2.
