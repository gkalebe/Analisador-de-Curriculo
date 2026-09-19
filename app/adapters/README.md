# adapters/

Isola o `core` de qualquer dependência externa (API de IA, bibliotecas de parsing de arquivo), aplicando o Princípio da Inversão de Dependência — o `core` conhece só a interface, nunca a implementação concreta. Isso é o que permite trocar Gemini por Claude, ou trocar a biblioteca de parsing de PDF, sem alterar nenhum service.

## `ai_service/ai_service_adapter.py`

US-006, US-007, US-010 — Sprint 2 (Carlos) e Sprint 3 (Kevin) originalmente; a implementação abaixo foi feita por Gabriel Kalebe fora dessas duas US, com autorização do time (avise se o prompt/contrato precisar mudar).

`AIServiceClient` (interface abstrata), `GeminiClient` e `ClaudeClient` (implementações concretas, usando as libs `google-generativeai` e `anthropic` já no `requirements.txt`) e `AIServiceAdapter` (escolhe Claude se `ANTHROPIC_API_KEY` estiver definida no `.env`, senão Gemini) estão implementados:

- `GeminiClient.gerar_resposta` / `ClaudeClient.gerar_resposta`: chamam a API de verdade. Sem `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` configurada, lançam `IAConfiguracaoAusenteError` (capturada em `analise_router.py` como `503`, com mensagem amigável — RNF-008 — em vez de erro técnico cru).
- `AIServiceAdapter._montar_prompt_analise` e `_montar_prompt_comparacao`: pedem ao modelo uma resposta em JSON estrito `{"pontuacao": 0-100, "observacoes": "..."}`. `AnalisadorService._interpretar_resultado_ia` (`core/service/`) consome esse contrato — combine com quem mexer aqui antes de mudar o formato.
- `AIServiceAdapter.extrair_dados_estruturados` (novo, US-012/US-013): pede ao modelo um JSON estrito `{"nome", "email", "telefone", "resumo", "formacao", "experiencia_profissional", "habilidades"}` a partir do texto bruto do currículo. Consumido por `TemplateService._extrair_dados_curriculo` (`core/service/`) para montar o currículo exportável — mesmas regras de tolerância a bloco markdown ao redor do JSON que os outros dois prompts.
- Modelo usado: `GEMINI_MODEL_NAME`/`ANTHROPIC_MODEL_NAME` no `.env` (padrão `gemini-1.5-flash` / `claude-3-5-haiku-20241022`), configurável sem mudar código.
- Testes: `tests/unit/test_ai_service_adapter.py` (com um `AIServiceClient` fake, não chama API de verdade).
- Ainda falta (US-006/US-007 propriamente ditas, fora do escopo do que foi feito agora): validar o prompt contra os critérios de aceite completos (percentual de aderência detalhado, palavras-chave ausentes específicas) e retry em caso de indisponibilidade momentânea do provedor.

## `curriculo_parser/curriculo_parser.py`

US-004 — Sprint 1 (Gustavo Souto Pereira). Concluído: `_extrair_texto_pdf` (via `pymupdf`/`fitz`) e `_extrair_texto_docx` (via `python-docx`) já implementados. `FormatoNaoSuportadoError` é capturada em `analise_router.py` e convertida em `400`. Validação de tamanho (limite de `max_upload_size_mb`, `app/core/config.py`) é feita no router, não no parser.

## `curriculo_exporter/curriculo_exporter.py`

US-012, US-013 — Sprint 3 (Allan, Carlos); implementado por Gabriel Kalebe fora dessas duas US, com autorização do time.

`CurriculoExporter` gera o arquivo final do currículo em 2 formatos (`gerar_pdf`, `gerar_docx`) e 3 templates visuais (`moderno`, `classico`, `minimalista`), a partir de um dicionário de dados (nome, email, telefone, resumo, formação, experiência, habilidades) já extraído pelo `TemplateService` (`core/service/`):

- PDF via `fpdf2` (novo em `requirements.txt`). Importante: as fontes core do fpdf2 (`Helvetica`/`Times`) só suportam Latin-1 — qualquer caractere Unicode fora disso (travessão "—", aspas curvas, reticências "…", "•") quebra a geração com `FPDFUnicodeEncodingException`. `_sanitizar_dados_pdf`/`_sanitizar_texto_pdf` tratam isso: trocam os caracteres tipográficos mais comuns por equivalentes ASCII e, por segurança, fazem um `encode("latin-1", errors="replace")` no final. Essa sanitização só se aplica ao caminho do PDF — o DOCX (via `python-docx`) suporta Unicode nativamente, sem tratamento.
- Se não houver dados estruturados da IA (ver `TemplateService._extrair_dados_curriculo`), cai num fallback com uma única seção "Currículo" contendo o texto bruto extraído do upload (`Curriculo.texto_extraido`) — nunca gera um arquivo vazio.
- Testes: exercido indiretamente via `tests/unit/test_template_service.py` (fakes) e validado manualmente gerando os 3 templates × 2 formatos × 2 cenários (com/sem dados estruturados) — sem teste unitário dedicado ao `CurriculoExporter` em si ainda; quem for mexer no layout, considere adicionar.

## `ai_service/curriculo_schema.py`, `ai_service/curriculo_estruturado_client.py`, `curriculo_exporter/curriculo_template_exporter.py`

Pipeline de geração estruturada de currículo (independente do `curriculo_exporter.py`/`extracao_curriculo.py` acima), pensado para eliminar o corte/perda de informação: em vez de a IA reescrever o currículo em texto livre para depois encaixar em seções fixas, a IA só preenche um schema Pydantic fixo (JSON mode + `response_schema` da própria API do Gemini), e a montagem do `.docx`/`.pdf` é 100% determinística via `docxtpl` — nenhuma etapa "reescreve" nada.

3 etapas isoladas, cada uma testável e substituível de forma independente (ver docstring de cada módulo para o porquê da separação):

- **Etapa 1 — geração (IA)**: `curriculo_schema.py` define o contrato (`DadosCurriculoEstruturado` e submodelos `ContatoCurriculo`, `ExperienciaCurriculo`, `FormacaoCurriculo`, `IdiomaCurriculo`). `curriculo_estruturado_client.py` (`GeradorCurriculoEstruturadoIA`) chama o Gemini com `response_mime_type="application/json"` e `response_schema=DadosCurriculoEstruturado`. Importante: o `google-generativeai==0.8.3` não aceita todas as chaves que `model_json_schema()` do Pydantic v2 gera (`default`, `$ref`/`$defs` dos submodelos aninhados) — por isso `_schema_compativel_com_gemini` resolve as referências e remove essas chaves antes de enviar; sem isso a API recusa com `ValueError: Unknown field for Schema: default`. `regenerar_campo` faz o retry cirúrgico de um único campo (schema `_CampoUnico`, prompt mínimo).
- **Etapa 2 — validação (sem IA)**: `app/core/service/curriculo_validador.py` (`ValidadorCurriculoEstruturado`) — ver `app/core/service/README.md`.
- **Etapa 3 — montagem (sem IA)**: `curriculo_template_exporter.py` (`MontadorDocumentoCurriculo`) usa `docxtpl` sobre os templates em `curriculo_exporter/templates_estruturados/*.docx` (gerados por `gerar_templates.py`, nunca editados no Word diretamente — edite o gerador e rode de novo) e converte para PDF via `soffice --headless` (LibreOffice; sem dependência de MS Word). `_construir_contexto` usa `.get()` com fallback para o valor padrão do schema em cada campo, defendendo contra `dict` cru incompleto vindo de fora da Etapa 2.

Orquestração de ponta a ponta em `app/core/service/curriculo_estruturado_service.py` (`CurriculoEstruturadoService.gerar_curriculo_documento`). Exemplo completo rodando as 3 etapas com dados fictícios: `exemplo_pipeline_curriculo.py` (raiz do projeto). Testes: `tests/unit/test_curriculo_estruturado_client.py`, `tests/unit/test_curriculo_validador.py`, `tests/unit/test_curriculo_template_exporter.py`, `tests/unit/test_curriculo_estruturado_service.py`.

Ainda não tem router/endpoint HTTP — só a biblioteca do pipeline. Quem for expor isso na API deve capturar `IAConfiguracaoAusenteError`/`IAIndisponivelError`/`IARespostaInvalidaError` (Etapa 1), `CurriculoInvalidoError` (Etapa 2) e `TemplateCurriculoNaoEncontradoError`/`ConversaoPdfError` (Etapa 3) no router, como já é feito com as exceções do fluxo antigo.

## `email/` (`email_adapter.py`, `sendgrid_client.py`)

US-003 — provedor de e-mail transacional (recuperação de senha e confirmação de cadastro). `EmailAdapter` escolhe entre SendGrid (via `sendgrid_client.py`, usado quando `SENDGRID_API_KEY` está configurada no `.env`), SMTP puro (`smtp_host` configurado) ou log local em desenvolvimento (nenhum dos dois configurado) — nessa ordem. Erros de envio (timeout, credencial inválida, indisponibilidade do provedor) são capturados e logados, nunca propagados para o chamador: uma falha de e-mail não deve derrubar o cadastro ou a recuperação de senha. O envio de confirmação de cadastro roda como `BackgroundTask` (agendado em `auth_router.py`) para não bloquear a resposta HTTP.
