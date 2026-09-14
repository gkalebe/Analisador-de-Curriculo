# adapters/

Isola o `core` de qualquer dependência externa (API de IA, bibliotecas de parsing de arquivo), aplicando o Princípio da Inversão de Dependência — o `core` conhece só a interface, nunca a implementação concreta. Isso é o que permite trocar Gemini por Claude, ou trocar a biblioteca de parsing de PDF, sem alterar nenhum service.

## `ai_service/ai_service_adapter.py`

US-006, US-007, US-010 — Sprint 2 (Carlos) e Sprint 3 (Kevin).

Já está montada a estrutura: `AIServiceClient` (interface abstrata), `GeminiClient` e `ClaudeClient` (implementações concretas) e `AIServiceAdapter` (escolhe o cliente pela variável de ambiente configurada). O que falta implementar:

- `GeminiClient.gerar_resposta` / `ClaudeClient.gerar_resposta`: a chamada real à API (usar as libs `google-generativeai` e `anthropic`, já no `requirements.txt`).
- `AIServiceAdapter._montar_prompt_analise` e `_montar_prompt_comparacao`: o prompt engineering em si — como pedir para o modelo devolver diagnóstico, percentual de aderência, palavras-chave ausentes etc. Ver os critérios de aceite de US-006/US-007 no Levantamento de Requisitos para saber exatamente o que a resposta da IA precisa conter.
- Tratamento de indisponibilidade do serviço (RNF-008: mensagem amigável, sem expor erro técnico, com opção de nova tentativa).

## `curriculo_parser/curriculo_parser.py`

US-004 — Sprint 1 (Gustavo Souto Pereira). Concluído: `_extrair_texto_pdf` (via `pymupdf`/`fitz`) e `_extrair_texto_docx` (via `python-docx`) já implementados. `FormatoNaoSuportadoError` é capturada em `analise_router.py` e convertida em `400`. Validação de tamanho (limite de `max_upload_size_mb`, `app/core/config.py`) é feita no router, não no parser.

## `email/` (`email_adapter.py`, `sendgrid_client.py`)

US-003 — provedor de e-mail transacional (recuperação de senha e confirmação de cadastro). `EmailAdapter` escolhe entre SendGrid (via `sendgrid_client.py`, usado quando `SENDGRID_API_KEY` está configurada no `.env`), SMTP puro (`smtp_host` configurado) ou log local em desenvolvimento (nenhum dos dois configurado) — nessa ordem. Erros de envio (timeout, credencial inválida, indisponibilidade do provedor) são capturados e logados, nunca propagados para o chamador: uma falha de e-mail não deve derrubar o cadastro ou a recuperação de senha. O envio de confirmação de cadastro roda como `BackgroundTask` (agendado em `auth_router.py`) para não bloquear a resposta HTTP.
