# adapters/

Isola o `core` de qualquer dependência externa (API de IA, bibliotecas de parsing de arquivo), aplicando o Princípio da Inversão de Dependência — o `core` conhece só a interface, nunca a implementação concreta. Isso é o que permite trocar Gemini por Claude, ou trocar a biblioteca de parsing de PDF, sem alterar nenhum service.

## `ai_service/ai_service_adapter.py`

US-006, US-007, US-010 — Sprint 2 (Carlos) e Sprint 3 (Kevin).

Já está montada a estrutura: `AIServiceClient` (interface abstrata), `GeminiClient` e `ClaudeClient` (implementações concretas) e `AIServiceAdapter` (escolhe o cliente pela variável de ambiente configurada). O que falta implementar:

- `GeminiClient.gerar_resposta` / `ClaudeClient.gerar_resposta`: a chamada real à API (usar as libs `google-generativeai` e `anthropic`, já no `requirements.txt`).
- `AIServiceAdapter._montar_prompt_analise` e `_montar_prompt_comparacao`: o prompt engineering em si — como pedir para o modelo devolver diagnóstico, percentual de aderência, palavras-chave ausentes etc. Ver os critérios de aceite de US-006/US-007 no Levantamento de Requisitos para saber exatamente o que a resposta da IA precisa conter.
- Tratamento de indisponibilidade do serviço (RNF-008: mensagem amigável, sem expor erro técnico, com opção de nova tentativa).

## `curriculo_parser/curriculo_parser.py`

US-004 — Sprint 1 (Gustavo Souto Pereira).

O dispatch por extensão (`extrair_texto`) e a exceção `FormatoNaoSuportadoError` já estão prontos. Falta implementar:

- `_extrair_texto_pdf`: extração de texto usando `pymupdf` (import `fitz`).
- `_extrair_texto_docx`: extração de texto usando `python-docx`.

Ambas as libs já estão no `requirements.txt`. Ver critérios de aceite de US-004 (formatos aceitos, limite de 5MB — a validação de tamanho é responsabilidade do router/service, não do parser).
