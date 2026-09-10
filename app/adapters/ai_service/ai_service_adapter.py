from abc import ABC, abstractmethod

from app.core.config import get_settings


class AIServiceClient(ABC):
    @abstractmethod
    def gerar_resposta(self, prompt: str) -> str: ...


class GeminiClient(AIServiceClient):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def gerar_resposta(self, prompt: str) -> str:
        raise NotImplementedError


class ClaudeClient(AIServiceClient):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def gerar_resposta(self, prompt: str) -> str:
        raise NotImplementedError


class AIServiceAdapter:
    def __init__(self, cliente: AIServiceClient | None = None):
        if cliente is not None:
            self.cliente = cliente
        else:
            settings = get_settings()
            if settings.anthropic_api_key:
                self.cliente = ClaudeClient(settings.anthropic_api_key)
            else:
                self.cliente = GeminiClient(settings.gemini_api_key)

    def analisar_curriculo(self, texto_curriculo: str) -> str:
        prompt = self._montar_prompt_analise(texto_curriculo)
        return self.cliente.gerar_resposta(prompt)

    def comparar_curriculo_vaga(self, texto_curriculo: str, texto_vaga: str) -> str:
        prompt = self._montar_prompt_comparacao(texto_curriculo, texto_vaga)
        return self.cliente.gerar_resposta(prompt)

    def _montar_prompt_analise(self, texto_curriculo: str) -> str:
        raise NotImplementedError

    def _montar_prompt_comparacao(self, texto_curriculo: str, texto_vaga: str) -> str:
        raise NotImplementedError
