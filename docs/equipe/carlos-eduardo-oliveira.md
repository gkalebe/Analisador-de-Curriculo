# Carlos Eduardo Oliveira

Sprint 0: participação no kickoff técnico coletivo (repositório, estrutura de pastas, CI/CD, Docker) — sem dono individual.

## Sprint 1 (Semanas 1-2)

Sem entrega nesta sprint. Gustavo Souto Pereira assumiu a fatia inicial que seria sua (US-004 + apoio de infraestrutura) para você entrar direto na Sprint 2 com o núcleo de IA, que já estava previsto para você. Nenhuma outra mudança no restante do seu plano.

## Sprint 2 (Semanas 3-4)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-006 | Analisar conteúdo do currículo (IA) | 13 | `adapters/ai_service`, `core/service/analisador_service` |

Sprint mais pesada do projeto (42 pts) por concentrar o núcleo de IA. US-008 (Gabriel Kalebe) depende desta entrega — recomenda-se pareamento pontual nos primeiros dias para não travar a esteira. Você constrói o `AIServiceAdapter` (Arquitetura, Seção 4.2/4.3) já pensando em ser reaproveitado por US-010 na Sprint 3 (Kevin).

**Status atual:** a issue #8 já existe no board (tag Sprint 2), mas está em pausa — sem atribuição e em Backlog, não Ready. Por ora não há trabalho ativo esperado de você; quando isso mudar, o Tech Lead reatribui a issue e ela volta para Ready. Enquanto isso, Gustavo segue configurando o provedor de IA (Gemini x Claude) e estendendo o CI para os testes de integração, então a base vai estar pronta para quando você retomar.

## Sprint 3 (Semanas 5-6)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-013 | Aplicar currículo a template e exportar PDF/DOCX | 8 | `core/service/template_service` |

Depende da entrega de US-012 (Allan).

**Atualização:** as issues #31/#32 (US-012/US-013) acabaram indo para o kanban atribuídas diretamente a Gabriel Kalebe (rótulo `[FRONT]`), não para Allan/você como esta tabela original previa. Gabriel implementou as duas de ponta a ponta (front + back) com autorização do time — ver `docs/equipe/gabriel-kalebe.md` e `app/core/service/README.md` para o que foi entregue. Se você já tinha começado algo em `template_service.py`, avise o time antes de mesclar para evitar conflito.

## Sprint 4 (Semanas 7-8)

| US | Título | Pontos | Módulo |
|---|---|---|---|
| US-016 | Acessar painel com histórico e evolução das análises | 8 | `web/painel`, `core/persistencia/analise_repository` |

Depende de US-007 já entregue na Sprint 2.

Critérios de aceite (DADO/QUANDO/ENTÃO) de cada US: Levantamento de Requisitos v1.1, Seção 6.2.
