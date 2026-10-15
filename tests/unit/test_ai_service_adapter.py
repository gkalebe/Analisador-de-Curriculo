import logging

import httpx
import pytest

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    ClaudeClient,
    GeminiClient,
    GroqClient,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
    MistralClient,
)


class AIServiceClientFalso:
    def __init__(self, resposta: str = '{"pontuacao": 80, "observacoes": "ok"}'):
        self.resposta = resposta
        self.prompts_recebidos: list[str] = []

    def gerar_resposta(self, prompt: str, **kwargs) -> str:
        self.prompts_recebidos.append(prompt)
        return self.resposta


def test_comparar_curriculo_vaga_envia_prompt_com_curriculo_e_vaga_sem_registrar_conteudo(caplog):
    caplog.set_level(logging.INFO, logger="app.adapters.ai_service.ai_service_adapter")
    cliente_falso = AIServiceClientFalso()
    adapter = AIServiceAdapter(cliente=cliente_falso)

    resultado = adapter.comparar_curriculo_vaga("Experiência com Python.", "Vaga para dev Python.")

    assert resultado == cliente_falso.resposta
    assert "Experiência com Python." in cliente_falso.prompts_recebidos[0]
    assert "Vaga para dev Python." in cliente_falso.prompts_recebidos[0]
    assert "ai_call_succeeded" in caplog.text
    assert "comparar_curriculo_vaga" in caplog.text
    assert "Experiência com Python." not in caplog.text
    assert "Vaga para dev Python." not in caplog.text


def test_comparar_curriculo_vaga_pede_curriculo_estruturado_e_trechos_literais_para_reescrita_sem_ia():
    cliente = AIServiceClientFalso()
    adapter = AIServiceAdapter(cliente=cliente)

    adapter.comparar_curriculo_vaga("texto do currículo", "texto da vaga")

    prompt = cliente.prompts_recebidos[0]
    # Contrato com reescrita_curriculo.aplicar_sugestoes_sem_ia: o currículo estruturado vem na
    # mesma resposta e os trechos/itens a remover são cópias idênticas de itens dele.
    assert '"curriculo_estruturado"' in prompt
    assert "secoes_adicionais" in prompt
    assert "cópia IDÊNTICA" in prompt
    assert "ITENS INTEIROS" in prompt
    # Palavras-chave entram só via reescrita e só com sustentação no currículo.
    assert "JÁ SUSTENTA" in prompt and "NUNCA entram em uma" in prompt
    # Termo vago dentro de frase vira reescrita, não remoção.
    assert "NÃO o coloque em 'o_que_retirar'" in prompt
    assert "entre 4 e 10 sugestões" in prompt


def test_analisar_curriculo_envia_prompt_com_curriculo():
    cliente_falso = AIServiceClientFalso()
    adapter = AIServiceAdapter(cliente=cliente_falso)

    adapter.analisar_curriculo("Experiência com Python.")

    assert "Experiência com Python." in cliente_falso.prompts_recebidos[0]


def test_gemini_client_sem_api_key_lanca_erro_de_configuracao():
    cliente = GeminiClient(api_key="")

    with pytest.raises(IAConfiguracaoAusenteError):
        cliente.gerar_resposta("prompt qualquer")


def test_claude_client_sem_api_key_lanca_erro_de_configuracao():
    cliente = ClaudeClient(api_key="")

    with pytest.raises(IAConfiguracaoAusenteError):
        cliente.gerar_resposta("prompt qualquer")


def test_gemini_client_lanca_ia_indisponivel_quando_api_falha_ou_estoura_tempo(monkeypatch):
    import google.api_core.exceptions
    import google.generativeai as genai

    class ModeloFalso:
        def generate_content(self, prompt, **kwargs):
            raise google.api_core.exceptions.DeadlineExceeded("tempo esgotado")

    monkeypatch.setattr(genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: ModeloFalso())

    cliente = GeminiClient(api_key="chave-qualquer")

    with pytest.raises(IAIndisponivelError):
        cliente.gerar_resposta("prompt qualquer")


def test_gemini_client_tenta_novamente_e_recupera_apos_indisponibilidade_transitoria(monkeypatch):
    import google.api_core.exceptions
    import google.generativeai as genai

    from app.adapters.ai_service import ai_service_adapter

    class RespostaFalsa:
        text = '{"pontuacao": 90, "observacoes": "ok"}'

    class ModeloFalso:
        def __init__(self):
            self.chamadas = 0

        def generate_content(self, prompt, **kwargs):
            self.chamadas += 1
            if self.chamadas == 1:
                raise google.api_core.exceptions.ServiceUnavailable("modelo sobrecarregado")
            return RespostaFalsa()

    modelo_falso = ModeloFalso()
    monkeypatch.setattr(genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: modelo_falso)
    monkeypatch.setattr(ai_service_adapter.time, "sleep", lambda segundos: None)

    cliente = GeminiClient(api_key="chave-qualquer")
    resultado = cliente.gerar_resposta("prompt qualquer")

    assert resultado == RespostaFalsa.text
    assert modelo_falso.chamadas == 2


def test_gemini_client_lanca_ia_indisponivel_apos_esgotar_tentativas_de_indisponibilidade(monkeypatch):
    import google.api_core.exceptions
    import google.generativeai as genai

    from app.adapters.ai_service import ai_service_adapter

    class ModeloFalso:
        def __init__(self):
            self.chamadas = 0

        def generate_content(self, prompt, **kwargs):
            self.chamadas += 1
            raise google.api_core.exceptions.ServiceUnavailable("modelo sobrecarregado")

    modelo_falso = ModeloFalso()
    monkeypatch.setattr(genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: modelo_falso)
    monkeypatch.setattr(ai_service_adapter.time, "sleep", lambda segundos: None)

    cliente = GeminiClient(api_key="chave-qualquer")

    with pytest.raises(IAIndisponivelError):
        cliente.gerar_resposta("prompt qualquer")

    assert modelo_falso.chamadas == ai_service_adapter.MAX_TENTATIVAS_GEMINI


def test_claude_client_lanca_ia_indisponivel_quando_api_falha_ou_estoura_tempo(monkeypatch):
    import anthropic

    class MensagensFalso:
        def create(self, model, max_tokens, messages, **kwargs):
            requisicao_falsa = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise anthropic.APIError("tempo esgotado", request=requisicao_falsa, body=None)

    class ClienteAnthropicFalso:
        def __init__(self, api_key=None, timeout=None, max_retries=None):
            self.messages = MensagensFalso()

    monkeypatch.setattr(anthropic, "Anthropic", ClienteAnthropicFalso)

    cliente = ClaudeClient(api_key="chave-qualquer")

    with pytest.raises(IAIndisponivelError):
        cliente.gerar_resposta("prompt qualquer")


@pytest.mark.parametrize(
    ("cliente_type", "endpoint", "provider", "model"),
    [
        (GroqClient, "https://api.groq.com/openai/v1/chat/completions", "groq", "openai/gpt-oss-120b"),
        (MistralClient, "https://api.mistral.ai/v1/chat/completions", "mistral", "mistral-large-latest"),
    ],
)
def test_client_openai_compatibles_envia_prompt_e_le_usage(monkeypatch, cliente_type, endpoint, provider, model):
    chamadas = []

    class RespostaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            }

    def post(url, **kwargs):
        chamadas.append((url, kwargs))
        return RespostaFalsa()

    monkeypatch.setattr(httpx, "post", post)
    cliente = cliente_type(api_key="chave-teste", model_name=model)

    completion = cliente.gerar_resposta_com_metadados("prompt teste", temperatura=0.2, timeout_segundos=17)

    assert chamadas[0][0] == endpoint
    assert chamadas[0][1]["headers"]["Authorization"] == "Bearer chave-teste"
    assert chamadas[0][1]["json"]["model"] == model
    assert chamadas[0][1]["json"]["messages"] == [{"role": "user", "content": "prompt teste"}]
    assert completion.text == '{"ok": true}'
    assert completion.input_tokens == 12
    assert completion.output_tokens == 7
    assert cliente.provider_name == provider


@pytest.mark.parametrize("cliente_type", [GroqClient, MistralClient])
def test_client_openai_compatibles_usa_modo_json_em_resposta_estruturada(monkeypatch, cliente_type):
    from pydantic import BaseModel

    class Contrato(BaseModel):
        ok: bool

    payloads = []

    class RespostaFalsa:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"ok": true}'}}], "usage": {}}

    def post(url, **kwargs):
        payloads.append(kwargs["json"])
        return RespostaFalsa()

    monkeypatch.setattr(httpx, "post", post)
    cliente = cliente_type(api_key="chave-teste")

    cliente.gerar_resposta_estruturada("retorne JSON", Contrato)

    assert payloads[0]["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in payloads[0]["messages"][0]["content"]


@pytest.mark.parametrize("cliente_type", [GroqClient, MistralClient])
def test_client_openai_compatibles_mapeia_falha_http_para_erro_de_provider(monkeypatch, cliente_type):
    def post(url, **kwargs):
        raise httpx.TimeoutException("erro com conteudo sensivel")

    monkeypatch.setattr(httpx, "post", post)
    cliente = cliente_type(api_key="chave-teste")

    with pytest.raises(IAIndisponivelError):
        cliente.gerar_resposta("prompt qualquer")
