import httpx
import pytest

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    ClaudeClient,
    GeminiClient,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)


class AIServiceClientFalso:
    def __init__(self, resposta: str = '{"pontuacao": 80, "observacoes": "ok"}'):
        self.resposta = resposta
        self.prompts_recebidos: list[str] = []

    def gerar_resposta(self, prompt: str, **kwargs) -> str:
        self.prompts_recebidos.append(prompt)
        return self.resposta


def test_comparar_curriculo_vaga_envia_prompt_com_curriculo_e_vaga():
    cliente_falso = AIServiceClientFalso()
    adapter = AIServiceAdapter(cliente=cliente_falso)

    resultado = adapter.comparar_curriculo_vaga("Experiência com Python.", "Vaga para dev Python.")

    assert resultado == cliente_falso.resposta
    assert "Experiência com Python." in cliente_falso.prompts_recebidos[0]
    assert "Vaga para dev Python." in cliente_falso.prompts_recebidos[0]


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
