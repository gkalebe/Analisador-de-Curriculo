# adapters/

Isola o `core` de qualquer dependência externa (API de IA, bibliotecas de parsing de arquivo), aplicando o Princípio da Inversão de Dependência — o `core` conhece só a interface, nunca a implementação concreta. Isso é o que permite trocar Gemini por Claude, ou trocar a biblioteca de parsing de PDF, sem alterar nenhum service.

## `ai_service/ai_service_adapter.py`

US-006, US-007, US-010 — Sprint 2 (Carlos) e Sprint 3 (Kevin) originalmente; a implementação abaixo foi feita por Gabriel Kalebe fora dessas duas US, com autorização do time (avise se o prompt/contrato precisar mudar).

`AIServiceClient` (interface abstrata), os clientes Gemini e Claude, os clientes Groq e Mistral compatíveis com a API de chat da OpenAI, e `AIServiceAdapter` estão implementados. O adapter escolhe automaticamente o primeiro provider configurado nesta prioridade: Gemini, Groq, Mistral e Claude.

- Os clientes fazem uma única chamada lógica ao provider selecionado; não há seletor de modelo por usuário nem failover automático para outro provider em caso de falha. Chaves e modelos são configurados no servidor via `.env` (`GEMINI_*`, `GROQ_*`, `MISTRAL_*`, `ANTHROPIC_*`). Sem nenhuma chave, lançam `IAConfiguracaoAusenteError` (capturada em `analise_router.py` como `503`).
- Groq e Mistral usam endpoints de chat compatíveis com OpenAI via `httpx`, que já é dependência do projeto. Para operações estruturadas, a requisição pede JSON e inclui o JSON Schema no prompt; a saída continua sujeita à validação local do contrato.
- `AIServiceAdapter._montar_prompt_analise` e `_montar_prompt_comparacao`: pedem uma resposta JSON. A comparação é validada por `response_contracts.py` antes de persistir: pontuação deve estar entre 0 e 100, e os campos estruturados, quando presentes, precisam respeitar seus tipos. Resposta inválida gera `IARespostaInvalidaError` e HTTP 502; não vira análise com pontuação vazia.
- `AIServiceAdapter.extrair_dados_estruturados` (US-012/US-013): pede o schema completo de `DadosCurriculoEstruturado` a partir do texto bruto do currículo. Consumido por `TemplateService` para montar o currículo exportável; a resposta é normalizada e validada localmente.
- O pipeline estruturado (`curriculo_estruturado_client.py`) também usa `AIServiceAdapter`: Gemini recebe JSON mode e schema nativo; os demais clientes recebem JSON mode quando suportado, o schema no prompt e validação Pydantic. A geração padrão faz uma chamada; reparos de campo não são ativados automaticamente.
- Chamadas geram logs de operação, provedor/modelo, latência, tentativas e tokens quando fornecidos pelo SDK. Prompts, currículos, vagas e respostas não são registrados.
- Modelos usados: `GEMINI_MODEL_NAME`, `GROQ_MODEL_NAME`, `MISTRAL_MODEL_NAME` ou `ANTHROPIC_MODEL_NAME`, conforme o provider selecionado pela ordem acima.
- Testes: `tests/unit/test_ai_service_adapter.py` (com um `AIServiceClient` fake, não chama API de verdade).
- Avaliação offline: `tests/ai_evaluation/` valida contrato e se sugestões citam trechos presentes em casos sintéticos. Isso não mede julgamento semântico de recrutamento; exemplos reais só devem ser incluídos após revisão e anonimização.

## `curriculo_parser/curriculo_parser.py`

US-004 — Sprint 1 (Gustavo Souto Pereira). Concluído: `_extrair_texto_pdf` (via `pymupdf`/`fitz`) e `_extrair_texto_docx` (via `python-docx`) já implementados. `FormatoNaoSuportadoError` é capturada em `analise_router.py` e convertida em `400`. Validação de tamanho (limite de `max_upload_size_mb`, `app/core/config.py`) é feita no router, não no parser.

## `curriculo_exporter/curriculo_exporter.py`

US-012, US-013 — Sprint 3 (Allan, Carlos); implementado por Gabriel Kalebe fora dessas duas US, com autorização do time.

`CurriculoExporter` gera o arquivo final do currículo em 2 formatos (`gerar_pdf`, `gerar_docx`) e 5 templates visuais (`generico`, `tecnologia`, `estagio`, `gestao`, `setor_publico`, mesma estrutura e cor de destaque diferente), a partir do currículo estruturado completo (`DadosCurriculoEstruturado` em dict + `texto_bruto`, ver `ai_service/curriculo_schema.py`) resolvido pelo `TemplateService` (`core/service/`). Desde 07/10 renderiza TODAS as seções preenchidas — resumo, experiências com bullets, formação, habilidades, idiomas, certificações e `secoes_adicionais` com o título original — em vez das 4 seções fixas de antes; testes em `tests/unit/test_curriculo_exporter.py`:

- PDF via `fpdf2` (novo em `requirements.txt`). Importante: as fontes core do fpdf2 (`Helvetica`/`Times`) só suportam Latin-1 — qualquer caractere Unicode fora disso (travessão "—", aspas curvas, reticências "…", "•") quebra a geração com `FPDFUnicodeEncodingException`. `_sanitizar_dados_pdf`/`_sanitizar_texto_pdf` tratam isso: trocam os caracteres tipográficos mais comuns por equivalentes ASCII e, por segurança, fazem um `encode("latin-1", errors="replace")` no final. Essa sanitização só se aplica ao caminho do PDF — o DOCX (via `python-docx`) suporta Unicode nativamente, sem tratamento.
- Se não houver dados estruturados da IA (ver `TemplateService._extrair_dados_curriculo`), cai num fallback com uma única seção "Currículo" contendo o texto bruto extraído do upload (`Curriculo.texto_extraido`) — nunca gera um arquivo vazio.
- Testes: exercido indiretamente via `tests/unit/test_template_service.py` (fakes) e validado manualmente gerando os 3 templates × 2 formatos × 2 cenários (com/sem dados estruturados) — sem teste unitário dedicado ao `CurriculoExporter` em si ainda; quem for mexer no layout, considere adicionar.

## `ai_service/curriculo_schema.py`, `ai_service/curriculo_estruturado_client.py`, `curriculo_exporter/curriculo_template_exporter.py`

Pipeline de geração estruturada de currículo (independente do `curriculo_exporter.py`/`extracao_curriculo.py` acima), pensado para eliminar o corte/perda de informação: em vez de a IA reescrever texto livre para depois encaixar em seções fixas, a IA só preenche um schema Pydantic fixo. O provider ativo impõe o schema nativamente quando disponível (Gemini) ou o recebe no prompt com validação local (Claude); a montagem do `.docx`/`.pdf` é determinística via `docxtpl`.

3 etapas isoladas, cada uma testável e substituível de forma independente (ver docstring de cada módulo para o porquê da separação):

- **Etapa 1 — geração (IA)**: `curriculo_schema.py` define o contrato (`DadosCurriculoEstruturado` e submodelos `ContatoCurriculo`, `ExperienciaCurriculo`, `FormacaoCurriculo`, `IdiomaCurriculo`). `GeradorCurriculoEstruturadoIA` delega ao `AIServiceAdapter`; o cliente Gemini converte o schema para o formato do SDK e usa JSON mode nativo. Outros clientes recebem o JSON Schema no prompt e a resposta é validada localmente. `regenerar_campo` permanece disponível para uso explícito, mas o serviço padrão não o chama automaticamente.
- **Etapa 2 — validação (sem IA)**: `app/core/service/curriculo_validador.py` (`ValidadorCurriculoEstruturado`) — ver `app/core/service/README.md`.
- **Etapa 3 — montagem (sem IA)**: `curriculo_template_exporter.py` (`MontadorDocumentoCurriculo`) usa `docxtpl` sobre os templates em `curriculo_exporter/templates_estruturados/*.docx` (gerados por `gerar_templates.py`, nunca editados no Word diretamente — edite o gerador e rode de novo) e converte para PDF via `soffice --headless` (LibreOffice; sem dependência de MS Word). `_construir_contexto` usa `.get()` com fallback para o valor padrão do schema em cada campo, defendendo contra `dict` cru incompleto vindo de fora da Etapa 2.

Orquestração de ponta a ponta em `app/core/service/curriculo_estruturado_service.py` (`CurriculoEstruturadoService.gerar_curriculo_documento`). Exemplo completo rodando as 3 etapas com dados fictícios: `exemplo_pipeline_curriculo.py` (raiz do projeto). Testes: `tests/unit/test_curriculo_estruturado_client.py`, `tests/unit/test_curriculo_validador.py`, `tests/unit/test_curriculo_template_exporter.py`, `tests/unit/test_curriculo_estruturado_service.py`.

Ainda não tem router/endpoint HTTP — só a biblioteca do pipeline. Quem for expor isso na API deve capturar `IAConfiguracaoAusenteError`/`IAIndisponivelError`/`IARespostaInvalidaError` (Etapa 1), `CurriculoInvalidoError` (Etapa 2) e `TemplateCurriculoNaoEncontradoError`/`ConversaoPdfError` (Etapa 3) no router, como já é feito com as exceções do fluxo antigo.

## `email/` (`email_adapter.py`, `sendgrid_client.py`)

US-003 — provedor de e-mail transacional (recuperação de senha e confirmação de cadastro). `EmailAdapter` escolhe entre SendGrid (via `sendgrid_client.py`, usado quando `SENDGRID_API_KEY` está configurada no `.env`), SMTP puro (`smtp_host` configurado) ou log local em desenvolvimento (nenhum dos dois configurado) — nessa ordem. Erros de envio (timeout, credencial inválida, indisponibilidade do provedor) são capturados e logados, nunca propagados para o chamador: uma falha de e-mail não deve derrubar o cadastro ou a recuperação de senha. O envio de confirmação de cadastro roda como `BackgroundTask` (agendado em `auth_router.py`) para não bloquear a resposta HTTP.
