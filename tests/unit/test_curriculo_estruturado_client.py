import pytest

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    GeminiClient,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
    IARespostaInvalidaError,
)
from app.adapters.ai_service.curriculo_estruturado_client import (
    GeradorCurriculoEstruturadoIA,
)
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado

JSON_CURRICULO_COMPLETO = """
{
  "nome_completo": "Ana Beatriz Souza",
  "titulo_profissional": "Desenvolvedora Backend Pleno",
  "contato": {"email": "ana@email.com", "telefone": "(61) 99999-0000", "linkedin": "", "cidade": "Brasília"},
  "resumo_profissional": "4 anos de experiência em Python.",
  "experiencias": [
    {"cargo": "Dev Backend", "empresa": "XPTO", "periodo_inicio": "2023", "periodo_fim": "atual", "descricao_bullets": ["Liderou migração"]}
  ],
  "formacao": [],
  "habilidades_tecnicas": ["Python"],
  "idiomas": [],
  "certificacoes": []
}
"""


class AdapterFalso:
    def __init__(self, resposta: str):
        self.resposta = resposta
        self.chamadas: list[dict] = []

    def gerar_resposta_estruturada(self, prompt, schema, **kwargs):
        self.chamadas.append({"prompt": prompt, "schema": schema, **kwargs})
        return self.resposta


def test_gerar_sem_api_key_lanca_erro_de_configuracao(monkeypatch):
    monkeypatch.setattr("app.adapters.ai_service.ai_service_adapter.get_settings", lambda: type(
        "Settings", (), {
            "anthropic_api_key": "",
            "anthropic_model_name": "claude-test",
            "gemini_api_key": "",
            "gemini_model_name": "gemini-test",
        }
    )())
    gerador = GeradorCurriculoEstruturadoIA()

    with pytest.raises(IAConfiguracaoAusenteError):
        gerador.gerar("informações brutas quaisquer")


def test_gerar_com_sucesso_usa_adapter_ativo_e_retorna_dados_estruturados():
    adapter = AdapterFalso(JSON_CURRICULO_COMPLETO)
    gerador = GeradorCurriculoEstruturadoIA(ai_service_adapter=adapter)

    dados = gerador.gerar("Ana trabalhou na XPTO como dev backend desde 2023.")

    assert dados.nome_completo == "Ana Beatriz Souza"
    assert dados.experiencias[0].empresa == "XPTO"
    assert "Ana trabalhou" in adapter.chamadas[0]["prompt"]
    assert adapter.chamadas[0]["schema"] is DadosCurriculoEstruturado
    assert adapter.chamadas[0]["operacao"] == "curriculo_estruturado"
    assert len(adapter.chamadas) == 1


@pytest.mark.parametrize("resposta", ["isso não é um JSON", '{"nome_completo": 123}'])
def test_gerar_com_resposta_invalida_lanca_erro_de_contrato(resposta):
    gerador = GeradorCurriculoEstruturadoIA(ai_service_adapter=AdapterFalso(resposta))

    with pytest.raises(IARespostaInvalidaError):
        gerador.gerar("informações brutas")


def test_gerar_com_json_fora_do_schema_usa_defaults_para_campos_ausentes():
    gerador = GeradorCurriculoEstruturadoIA(ai_service_adapter=AdapterFalso('{"campo_que_nao_existe": 123}'))

    dados = gerador.gerar("informações brutas")

    assert dados.nome_completo == ""


def test_gerar_repassa_indisponibilidade_do_provider():
    class AdapterIndisponivel:
        def gerar_resposta_estruturada(self, *args, **kwargs):
            raise IAIndisponivelError("indisponível")

    gerador = GeradorCurriculoEstruturadoIA(ai_service_adapter=AdapterIndisponivel())

    with pytest.raises(IAIndisponivelError):
        gerador.gerar("informações brutas")


def test_gemini_structured_client_usa_json_mode_e_schema(monkeypatch):
    import google.generativeai as genai

    class ModeloFalso:
        def generate_content(self, prompt, generation_config=None, request_options=None):
            self.generation_config = generation_config
            return type("Resposta", (), {"text": JSON_CURRICULO_COMPLETO})()

    modelo = ModeloFalso()
    monkeypatch.setattr(genai, "configure", lambda *args, **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: modelo)
    client = GeminiClient(api_key="chave-qualquer")

    completion = client.gerar_resposta_estruturada("prompt", DadosCurriculoEstruturado)

    assert completion.text == JSON_CURRICULO_COMPLETO
    assert modelo.generation_config.response_mime_type == "application/json"
    assert modelo.generation_config.response_schema["properties"]["nome_completo"]["type"] == "string"


def test_gemini_structured_client_converte_falha_do_sdk(monkeypatch):
    import google.api_core.exceptions
    import google.generativeai as genai

    class ModeloComErro:
        def generate_content(self, prompt, generation_config=None, request_options=None):
            raise google.api_core.exceptions.DeadlineExceeded("tempo esgotado")

    monkeypatch.setattr(genai, "configure", lambda *args, **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: ModeloComErro())

    with pytest.raises(IAIndisponivelError):
        GeminiClient(api_key="chave-qualquer").gerar_resposta_estruturada(
            "prompt", DadosCurriculoEstruturado
        )


def test_gerador_estruturado_usa_claude_selecionado_pelo_adapter_em_uma_chamada(monkeypatch):
    import anthropic
    from app.adapters.ai_service import ai_service_adapter as adapter_module

    class MensagensFalsas:
        def __init__(self):
            self.chamadas = []

        def create(self, **kwargs):
            self.chamadas.append(kwargs)
            bloco = type("BlocoTexto", (), {"type": "text", "text": JSON_CURRICULO_COMPLETO})()
            uso = type("Uso", (), {"input_tokens": 120, "output_tokens": 300})()
            return type("Resposta", (), {"content": [bloco], "usage": uso})()

    mensagens = MensagensFalsas()
    monkeypatch.setattr(
        adapter_module,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "anthropic_api_key": "anthropic-key",
                "anthropic_model_name": "claude-test",
                "gemini_api_key": "gemini-key",
                "gemini_model_name": "gemini-test",
            },
        )(),
    )
    monkeypatch.setattr(
        anthropic,
        "Anthropic",
        lambda **kwargs: type("ClienteFalso", (), {"messages": mensagens})(),
    )

    gerador = GeradorCurriculoEstruturadoIA()
    dados = gerador.gerar("currículo sintético")

    assert dados.nome_completo == "Ana Beatriz Souza"
    assert len(mensagens.chamadas) == 1
    assert mensagens.chamadas[0]["model"] == "claude-test"
    assert "JSON Schema" in mensagens.chamadas[0]["messages"][0]["content"]
    assert "nome_completo" in mensagens.chamadas[0]["messages"][0]["content"]


def test_regenerar_campo_repassa_schema_e_resposta():
    adapter = AdapterFalso('{"valor": "Desenvolvedora Backend Pleno"}')
    gerador = GeradorCurriculoEstruturadoIA(ai_service_adapter=adapter)

    valor = gerador.regenerar_campo("Ana é desenvolvedora backend.", "titulo_profissional")

    assert valor == "Desenvolvedora Backend Pleno"
    assert "titulo_profissional" in adapter.chamadas[0]["prompt"]
    assert adapter.chamadas[0]["operacao"] == "curriculo_campo_retry"


def test_adapter_mantem_selecao_automatica_claude_antes_do_gemini(monkeypatch):
    from app.adapters.ai_service import ai_service_adapter

    settings = type(
        "Settings",
        (),
        {
            "anthropic_api_key": "anthropic",
            "anthropic_model_name": "claude-test",
            "gemini_api_key": "gemini",
            "gemini_model_name": "gemini-test",
        },
    )()
    monkeypatch.setattr(ai_service_adapter, "get_settings", lambda: settings)

    adapter = AIServiceAdapter()

    assert adapter.cliente.provider_name == "anthropic"
    assert adapter.cliente.model_name == "claude-test"
