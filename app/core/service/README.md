# core/service/

Regras de negócio. Cada service recebe repositórios e adapters via injeção de dependência no `__init__` e não conhece nada de HTTP, FastAPI ou banco diretamente — isso é responsabilidade de `web/` e `core/persistencia/`, respectivamente.

Os construtores já estão montados na Sprint 0 (o "fio" entre service, repository e adapter já existe). O que falta é o método de cada US.

## Services e donos por Sprint

| Arquivo | US | Sprint | Dev | Depende de |
|---|---|---|---|---|
| `auth_service.py` | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan | `usuario_repository` |
| `analisador_service.py` | US-004 a US-007, US-019 | 1-2 | Gustavo Souto Pereira, Allan, Kevin, Gabriel Kalebe, Carlos | `curriculo_repository`, `vaga_repository`, `analise_repository`, `curriculo_parser`, `ai_service_adapter` |
| `diagnostico_service.py` | US-008, US-009 | 2 | Gabriel Kalebe, Allan | `analise_repository`, `ai_service_adapter` |
| `simulador_service.py` | US-010, US-011 | 3 | Kevin, Gabriel Kalebe | `vaga_repository`, `ai_service_adapter` |
| `template_service.py` | US-012, US-013 | 3 | Allan, Carlos | `curriculo_repository` |
| `plano_service.py` | US-014, US-015 | 4 | Kevin, Gabriel Kalebe | `analise_repository` |

## Convenção ao implementar uma US

1. Escreva o método no service correspondente (ex.: `AuthService.cadastrar_usuario(...)` para US-001).
2. Use os métodos de repositório já com assinatura pronta em `core/persistencia/` (eles hoje lançam `NotImplementedError` — implemente-os junto, na mesma branch, se sua US depender disso).
3. Não retorne modelos ORM direto para o router quando o critério de aceite pedir um formato específico de resposta — trate isso no service.
4. Erros de negócio (ex.: e-mail já cadastrado, formato de arquivo inválido) devem ser exceções específicas, capturadas depois no router e convertidas em `HTTPException` — não deixe o service devolver `dict` de erro.

Referência de critérios de aceite (DADO/QUANDO/ENTÃO) por US: Levantamento de Requisitos v1.1, Seção 6.2. Referência de decisão arquitetural: Documento de Arquitetura de Software, Seção 4.

## US-003 — Recuperar senha via e-mail (concluída)

`AuthService` ganhou `solicitar_recuperacao_senha(email)` e `redefinir_senha(token, nova_senha)`, além das exceções `TokenRecuperacaoInvalidoError` e `UsuarioNaoEncontradoError`. Abordagem escolhida: token assinado (JWT, `python-jose`, expira em `password_reset_expire_minutes` — configurável em `app/core/config.py`) em vez de gravar um campo novo em `models.py`. Isso evita mexer no schema (área sensível, ver Plano de Ação Seção 1.4) e mantém a validação sem estado — quem quiser trocar por token opaco persistido no banco mais adiante, avise o time antes de alterar `Usuario`.

`US-001`, `US-002` e `US-017` continuam pendentes neste mesmo arquivo (Kevin e Allan).
