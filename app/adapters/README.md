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

## `email/` (`email_adapter.py`, `sendgrid_client.py`)

US-003 — provedor de e-mail transacional (recuperação de senha e confirmação de cadastro). `EmailAdapter` escolhe entre SendGrid (via `sendgrid_client.py`, usado quando `SENDGRID_API_KEY` está configurada no `.env`), SMTP puro (`smtp_host` configurado) ou log local em desenvolvimento (nenhum dos dois configurado) — nessa ordem. Erros de envio (timeout, credencial inválida, indisponibilidade do provedor) são capturados e logados, nunca propagados para o chamador: uma falha de e-mail não deve derrubar o cadastro ou a recuperação de senha. O envio de confirmação de cadastro roda como `BackgroundTask` (agendado em `auth_router.py`) para não bloquear a resposta HTTP.
