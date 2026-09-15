# adapters/

Isola o `core` de qualquer dependência externa (API de IA, bibliotecas de parsing de arquivo), aplicando o Princípio da Inversão de Dependência — o `core` conhece só a interface, nunca a implementação concreta. Isso é o que permite trocar Gemini por Claude, ou trocar a biblioteca de parsing de PDF, sem alterar nenhum service.

## `ai_service/ai_service_adapter.py`

US-006, US-007, US-010 — Sprint 2 (Carlos) e Sprint 3 (Kevin) originalmente; a implementação abaixo foi feita por Gabriel Kalebe fora dessas duas US, com autorização do time (avise se o prompt/contrato precisar mudar).

`AIServiceClient` (interface abstrata), `GeminiClient` e `ClaudeClient` (implementações concretas, usando as libs `google-generativeai` e `anthropic` já no `requirements.txt`) e `AIServiceAdapter` (escolhe Claude se `ANTHROPIC_API_KEY` estiver definida no `.env`, senão Gemini) estão implementados:

- `GeminiClient.gerar_resposta` / `ClaudeClient.gerar_resposta`: chamam a API de verdade, com timeout de `TIMEOUT_SEGUNDOS` (30s). Sem `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` configurada, lançam `IAConfiguracaoAusenteError`; se a API estourar o timeout ou recusar a requisição, lançam `IAIndisponivelError`. Ambas capturadas em `analise_router.py` como `503`, com mensagem amigável — RNF-008 — em vez de erro técnico cru ou tela travada indefinidamente.
- `AIServiceAdapter._montar_prompt_analise` e `_montar_prompt_comparacao`: pedem ao modelo uma resposta em JSON estrito `{"pontuacao": 0-100, "observacoes": "..."}`. `AnalisadorService._interpretar_resultado_ia` (`core/service/`) consome esse contrato — combine com quem mexer aqui antes de mudar o formato.
- Modelo usado: `GEMINI_MODEL_NAME`/`ANTHROPIC_MODEL_NAME` no `.env` (padrão `gemini-flash-latest` — alias mantido pelo Google que sempre aponta para o flash recomendado atual, evitando quebra quando um nome de modelo pontual é descontinuado — / `claude-3-5-haiku-20241022`), configurável sem mudar código.
- Testes: `tests/unit/test_ai_service_adapter.py` (com um `AIServiceClient` fake para os testes de prompt, e monkeypatch dos SDKs do Gemini/Claude para cobrir `IAIndisponivelError`; não chama API de verdade).
- Ainda falta (US-006/US-007 propriamente ditas, fora do escopo do que foi feito agora): validar o prompt contra os critérios de aceite completos (percentual de aderência detalhado, palavras-chave ausentes específicas) e retry em caso de indisponibilidade momentânea do provedor.

## `curriculo_parser/curriculo_parser.py`

US-004 — Sprint 1 (Gustavo Souto Pereira). Concluído: `_extrair_texto_pdf` (via `pymupdf`/`fitz`) e `_extrair_texto_docx` (via `python-docx`) já implementados. `FormatoNaoSuportadoError` é capturada em `analise_router.py` e convertida em `400`. Validação de tamanho (limite de `max_upload_size_mb`, `app/core/config.py`) é feita no router, não no parser.

## `email/` (`email_adapter.py`, `sendgrid_client.py`)

US-003 — provedor de e-mail transacional (recuperação de senha e confirmação de cadastro). `EmailAdapter` escolhe entre SendGrid (via `sendgrid_client.py`, usado quando `SENDGRID_API_KEY` está configurada no `.env`), SMTP puro (`smtp_host` configurado) ou log local em desenvolvimento (nenhum dos dois configurado) — nessa ordem. Erros de envio (timeout, credencial inválida, indisponibilidade do provedor) são capturados e logados, nunca propagados para o chamador: uma falha de e-mail não deve derrubar o cadastro ou a recuperação de senha. O envio de confirmação de cadastro roda como `BackgroundTask` (agendado em `auth_router.py`) para não bloquear a resposta HTTP.
