# core/service/

Regras de negócio. Cada service recebe repositórios e adapters via injeção de dependência no `__init__` e não conhece nada de HTTP, FastAPI ou banco diretamente — isso é responsabilidade de `web/` e `core/persistencia/`, respectivamente.

Os construtores já estão montados na Sprint 0 (o "fio" entre service, repository e adapter já existe). O que falta é o método de cada US.

## Services e donos por Sprint

| Arquivo | US | Sprint | Dev | Depende de |
|---|---|---|---|---|
| `auth_service.py` | US-001, US-002, US-003, US-017 | 1 | Kevin, Gabriel Kalebe, Allan | `usuario_repository` |
| `analisador_service.py` | US-004 a US-007, US-019 | 1-2 | Gustavo Souto Pereira, Vitor Bittencourt dos Santos, Kevin, Gabriel Kalebe, Carlos | `curriculo_repository`, `vaga_repository`, `analise_repository`, `curriculo_parser`, `ai_service_adapter` |
| `diagnostico_service.py` | US-008, US-009 | 2 | Gabriel Kalebe, Allan | `analise_repository`, `ai_service_adapter` |
| `simulador_service.py` | US-010, US-011 | 3 | Kevin, Gabriel Kalebe | `vaga_repository`, `ai_service_adapter` |
| `template_service.py` | US-012, US-013 | 3 | Allan, Carlos (implementado por Gabriel Kalebe, com autorização do time) | `curriculo_repository`, `analise_repository`, `ai_service_adapter`, `curriculo_exporter` |
| `plano_service.py` | US-014, US-015, US-016 | 4 | Kevin, Gabriel Kalebe (US-016, concluído) | `analise_repository` |

## Convenção ao implementar uma US

1. Escreva o método no service correspondente (ex.: `AuthService.cadastrar_usuario(...)` para US-001).
2. Use os métodos de repositório já com assinatura pronta em `core/persistencia/` (eles hoje lançam `NotImplementedError` — implemente-os junto, na mesma branch, se sua US depender disso).
3. Não retorne modelos ORM direto para o router quando o critério de aceite pedir um formato específico de resposta — trate isso no service.
4. Erros de negócio (ex.: e-mail já cadastrado, formato de arquivo inválido) devem ser exceções específicas, capturadas depois no router e convertidas em `HTTPException` — não deixe o service devolver `dict` de erro.

Referência de critérios de aceite (DADO/QUANDO/ENTÃO) por US: Levantamento de Requisitos v1.1, Seção 6.2. Referência de decisão arquitetural: Documento de Arquitetura de Software, Seção 4.

## US-001/US-002 — Cadastro e login (concluídas)

`AuthService` tem `cadastrar_usuario(nome, data_nascimento, email, senha, enviar_email=True)` e `autenticar(email, senha)`. O parâmetro `enviar_email` existe para o router poder criar o usuário e agendar o e-mail de confirmação como `BackgroundTask` sem bloquear a resposta HTTP nos ~segundos que o envio (SendGrid/SMTP) pode levar — chamado diretamente (`enviar_email=True`, o padrão) o método continua enviando de forma síncrona, como nos testes existentes.

`US-017` continua pendente neste mesmo arquivo (Allan).

## US-003 — Recuperar senha via e-mail (concluída)

`AuthService` ganhou `solicitar_recuperacao_senha(email)` e `redefinir_senha(token, nova_senha)`, além das exceções `TokenRecuperacaoInvalidoError` e `UsuarioNaoEncontradoError`. Abordagem escolhida: token assinado (JWT, `python-jose`, expira em `password_reset_expire_minutes` — configurável em `app/core/config.py`) em vez de gravar um campo novo em `models/`. Isso evita mexer no schema (área sensível, ver Plano de Ação Seção 1.4) e mantém a validação sem estado — quem quiser trocar por token opaco persistido no banco mais adiante, avise o time antes de alterar `Usuario`.

Provedor de e-mail transacional definido: SendGrid (`app/adapters/email/`), com fallback para SMTP puro ou log local quando `SENDGRID_API_KEY` não está configurada.

## US-019 — Cadastrar informações de vaga no banco (concluída)

`AnalisadorService` ganhou `cadastrar_vaga(id_usuario, descricao, titulo="", requisitos="", area="")` e `listar_vagas_usuario(id_usuario)`, além das exceções `DescricaoVagaObrigatoriaError` (descrição vazia/só espaços) e `DescricaoVagaMuitoLongaError` (acima de `max_vaga_description_chars`, em `app/core/config.py`). `cadastrar_vaga` valida e delega a persistência para `VagaRepository.criar` (já implementado, US-019 back); `listar_vagas_usuario` delega para `VagaRepository.listar_por_usuario`, usado pela tela de reaproveitamento de vagas salvas. Testado em `tests/unit/test_analisador_service.py` com um fake de repositório em memória.

## US-005/US-006/US-007 — Comparar currículo com vaga (concluída)

`AnalisadorService` ganhou `analisar_curriculo_para_vaga(id_usuario, id_vaga, conteudo, nome_arquivo, extensao)` e `listar_analises_usuario(id_usuario)`, além da exceção `VagaNaoEncontradaError`. O método busca a vaga do usuário, extrai o texto do currículo (`CurriculoParser`), chama `AIServiceAdapter.comparar_curriculo_vaga` (implementado — ver `app/adapters/README.md`) e persiste o resultado via `AnaliseRepository.criar` (implementado — ver `app/core/persistencia/README.md`).

`_interpretar_resultado_ia` decodifica o JSON `{"pontuacao", "observacoes"}` que o `AIServiceAdapter` devolve, removendo blocos de markdown (```json ... ```) que o modelo às vezes adiciona mesmo sendo instruído a não fazer isso; se o texto não vier num JSON válido, cai num fallback (`pontuacao=None`, `observacoes=<texto cru>`) em vez de quebrar a análise.

Erros tratados no router (`analise_router.py`): `VagaNaoEncontradaError` → `404`, `FormatoNaoSuportadoError` → `400`, `IAConfiguracaoAusenteError` (sem `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` no `.env`) → `503` com mensagem amigável.

Feito por Gabriel Kalebe (fora do que estava originalmente atribuído a ele nessas US — `analisador_service.py`/`analise_router.py` já eram compartilhados com Gustavo/Vitor/Kevin/Carlos, mas a parte de `analise_repository.py` e `ai_service_adapter.py` era deles; time autorizou antes de mexer). Testes: `tests/unit/test_analisador_service.py` e `tests/unit/test_ai_service_adapter.py`.

## US-012/US-013 — Galeria de templates e exportação de currículo (concluída)

Feito por Gabriel Kalebe, fora do que estava originalmente atribuído a ele (`template_service.py`/`templates_router.py` eram de Allan/Carlos; time autorizou antes de mexer, mesmo padrão das US-005/006/007 acima).

`TemplateService` ganhou `listar_templates(id_usuario)` (lança `NenhumaAnaliseEncontradaError` se o usuário ainda não tiver nenhuma análise) e `exportar_curriculo(id_usuario, id_curriculo, id_template, formato)`, além das exceções `CurriculoNaoEncontradoError`, `TemplateNaoEncontradoError` e `FormatoExportacaoInvalidoError`.

`exportar_curriculo` busca o currículo (confere que pertence ao usuário), chama `_extrair_dados_curriculo` — que usa `AIServiceAdapter.extrair_dados_estruturados` sobre `Curriculo.texto_extraido` para tentar obter nome/email/telefone/resumo/formação/experiência/habilidades em JSON, com fallback para um dicionário "vazio" (só com `texto_bruto` preenchido) se a IA não estiver configurada ou disponível — e delega a geração do arquivo para `CurriculoExporter` (`app/adapters/curriculo_exporter/`, ver `app/adapters/README.md`), devolvendo `(conteudo_bytes, nome_arquivo, media_type)`.

A lista `TEMPLATES` (3 templates fixos: `moderno`, `classico`, `minimalista`, cada um com `preview_ficticio` para a galeria) fica hardcoded no próprio módulo — não há tabela no banco para isso, decisão deliberada para não adicionar complexidade sem necessidade nesta fase do projeto.

Erros tratados no router (`templates_router.py`): `NenhumaAnaliseEncontradaError` → `403`, `CurriculoNaoEncontradoError`/`TemplateNaoEncontradoError` → `404`, `FormatoExportacaoInvalidoError` → `400`. Testes: `tests/unit/test_template_service.py` e `tests/unit/test_templates_router.py`.

## US-016 (back) — Histórico de análises e lacunas recorrentes (concluída)

Feito por Gabriel Kalebe — issue #20 (`[BACK] US-016`) atribuída a ele no kanban.

`PlanoService` ganhou `obter_historico_e_lacunas(id_usuario)`, que devolve um `dict` com duas chaves:

- `historico`: uma entrada por análise do usuário (`id_analise`, `data_analise`, `vaga_titulo`, `pontuacao`), reaproveitando `AnaliseRepository.listar_por_usuario` (já implementado, US-007) e as relações `Analise.vaga`/`Analise.curriculo` do SQLAlchemy — nenhum método novo de repositório foi necessário.
- `lacunas_recorrentes`: calculada por `_competencias_em_lacuna`, que separa `Vaga.requisitos` em itens e marca como lacuna todo item que não aparece (substring, case-insensitive) em `Curriculo.texto_extraido`; depois soma a frequência de cada lacuna com `collections.Counter` em todas as análises do usuário e ordena da mais para a menos frequente.

Decisão deliberada: essa contagem de lacunas **não usa IA** — é heurística de texto simples sobre campos que já existem (`Vaga.requisitos`, `Curriculo.texto_extraido`), evitando 1 chamada de IA por análise só para montar o painel (custo, latência e mais um ponto de falha) e mantendo o painel disponível mesmo sem `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` configurada. Se o time decidir que a extração precisa ser semântica (sinônimos, etc.) em vez de substring, isso é uma evolução futura, não um requisito da issue #20.

Testes: `tests/unit/test_plano_service.py`.
