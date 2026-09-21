import pytest

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.adapters.ai_service.curriculo_estruturado_client import (
    GeradorCurriculoEstruturadoIA,
    IARespostaInvalidaError,
)

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


class ModeloFalso:
    def __init__(self, texto_resposta: str):
        self.texto_resposta = texto_resposta
        self.chamadas: list[dict] = []

    def generate_content(self, prompt, generation_config=None, request_options=None):
        self.chamadas.append({"prompt": prompt, "generation_config": generation_config})
        return type("Resposta", (), {"text": self.texto_resposta})()


def _configurar_genai_falso(monkeypatch, modelo_falso: ModeloFalso):
    import google.generativeai as genai

    monkeypatch.setattr(genai, "configure", lambda *args, **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: modelo_falso)


def test_gerar_sem_api_key_lanca_erro_de_configuracao():
    gerador = GeradorCurriculoEstruturadoIA(api_key="", model_name="gemini-3.6-flash")

    with pytest.raises(IAConfiguracaoAusenteError):
        gerador.gerar("informações brutas quaisquer")


def test_gerar_com_sucesso_retorna_dados_estruturados(monkeypatch):
    modelo_falso = ModeloFalso(JSON_CURRICULO_COMPLETO)
    _configurar_genai_falso(monkeypatch, modelo_falso)
    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    dados = gerador.gerar("Ana trabalhou na XPTO como dev backend desde 2023.")

    assert dados.nome_completo == "Ana Beatriz Souza"
    assert dados.experiencias[0].empresa == "XPTO"
    assert "Ana trabalhou" in modelo_falso.chamadas[0]["prompt"]
    # garante que a chamada usa JSON mode + response_schema, nunca prompt livre
    assert modelo_falso.chamadas[0]["generation_config"].response_mime_type == "application/json"


def test_gerar_com_json_malformado_lanca_erro_de_resposta_invalida(monkeypatch):
    modelo_falso = ModeloFalso("isso não é um JSON")
    _configurar_genai_falso(monkeypatch, modelo_falso)
    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    with pytest.raises(IARespostaInvalidaError):
        gerador.gerar("informações brutas")


def test_gerar_com_json_fora_do_schema_lanca_erro_de_resposta_invalida(monkeypatch):
    modelo_falso = ModeloFalso('{"campo_que_nao_existe": 123}')
    _configurar_genai_falso(monkeypatch, modelo_falso)
    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    dados = gerador.gerar("informações brutas")
    # campos extras/ausentes caem nos defaults do schema (tudo opcional) —
    # só um valor de TIPO errado (ex.: número onde se espera string) invalida.
    assert dados.nome_completo == ""


def test_gerar_com_tipo_de_campo_invalido_lanca_erro_de_resposta_invalida(monkeypatch):
    modelo_falso = ModeloFalso('{"nome_completo": 123}')
    _configurar_genai_falso(monkeypatch, modelo_falso)
    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    with pytest.raises(IARespostaInvalidaError):
        gerador.gerar("informações brutas")


def test_gerar_lanca_ia_indisponivel_quando_api_falha(monkeypatch):
    import google.api_core.exceptions
    import google.generativeai as genai

    class ModeloComErro:
        def generate_content(self, prompt, generation_config=None, request_options=None):
            raise google.api_core.exceptions.DeadlineExceeded("tempo esgotado")

    monkeypatch.setattr(genai, "configure", lambda *args, **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", lambda model_name: ModeloComErro())

    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    with pytest.raises(IAIndisponivelError):
        gerador.gerar("informações brutas")


def test_regenerar_campo_retorna_apenas_o_valor_do_campo(monkeypatch):
    modelo_falso = ModeloFalso('{"valor": "Desenvolvedora Backend Pleno"}')
    _configurar_genai_falso(monkeypatch, modelo_falso)
    gerador = GeradorCurriculoEstruturadoIA(api_key="chave-qualquer")

    valor = gerador.regenerar_campo("Ana é desenvolvedora backend.", "titulo_profissional")

    assert valor == "Desenvolvedora Backend Pleno"
    assert "titulo_profissional" in modelo_falso.chamadas[0]["prompt"]
