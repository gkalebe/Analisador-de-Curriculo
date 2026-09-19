import pytest

from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado
from app.core.service.curriculo_estruturado_service import (
    CurriculoEstruturadoService,
    FormatoDocumentoInvalidoError,
)


class GeradorFalso:
    def __init__(self, dados: DadosCurriculoEstruturado):
        self.dados = dados
        self.chamadas: list[str] = []

    def gerar(self, informacoes_brutas: str) -> DadosCurriculoEstruturado:
        self.chamadas.append(informacoes_brutas)
        return self.dados


class ValidadorFalso:
    def __init__(self, campos_com_retry: list[str] | None = None):
        self.campos_com_retry = campos_com_retry or []
        self.chamadas: list[tuple[dict, str]] = []

    def validar_e_reparar(self, dados_brutos: dict, informacoes_brutas: str):
        self.chamadas.append((dados_brutos, informacoes_brutas))
        return DadosCurriculoEstruturado.model_validate(dados_brutos), self.campos_com_retry


class MontadorFalso:
    def __init__(self):
        self.chamadas_docx: list[tuple[object, str, str]] = []
        self.chamadas_pdf: list[str] = []

    def gerar_docx(self, dados, id_template: str, caminho_saida: str) -> str:
        self.chamadas_docx.append((dados, id_template, caminho_saida))
        return caminho_saida

    def converter_para_pdf(self, caminho_docx: str, diretorio_saida: str | None = None) -> str:
        self.chamadas_pdf.append(caminho_docx)
        return caminho_docx.replace(".docx", ".pdf")


def _service_com_fakes(dados=None, campos_com_retry=None):
    dados = dados or DadosCurriculoEstruturado(nome_completo="Ana")
    gerador = GeradorFalso(dados)
    validador = ValidadorFalso(campos_com_retry)
    montador = MontadorFalso()
    service = CurriculoEstruturadoService(gerador=gerador, validador=validador, montador=montador)
    return service, gerador, validador, montador


def test_gerar_curriculo_documento_docx_encadeia_as_3_etapas(tmp_path):
    service, gerador, validador, montador = _service_com_fakes()

    caminho, campos_com_retry = service.gerar_curriculo_documento(
        "informações brutas do usuário", "moderno", "docx", str(tmp_path)
    )

    assert gerador.chamadas == ["informações brutas do usuário"]
    assert len(validador.chamadas) == 1
    assert len(montador.chamadas_docx) == 1
    assert montador.chamadas_docx[0][1] == "moderno"
    assert caminho.endswith(".docx")
    assert campos_com_retry == []
    assert montador.chamadas_pdf == []


def test_gerar_curriculo_documento_pdf_tambem_converte(tmp_path):
    service, _, _, montador = _service_com_fakes()

    caminho, _ = service.gerar_curriculo_documento("informações brutas", "classico", "pdf", str(tmp_path))

    assert caminho.endswith(".pdf")
    assert len(montador.chamadas_pdf) == 1


def test_gerar_curriculo_documento_reporta_campos_com_retry(tmp_path):
    service, _, _, _ = _service_com_fakes(campos_com_retry=["titulo_profissional"])

    _, campos_com_retry = service.gerar_curriculo_documento("informações brutas", "moderno", "docx", str(tmp_path))

    assert campos_com_retry == ["titulo_profissional"]


def test_gerar_curriculo_documento_com_formato_invalido_lanca_erro(tmp_path):
    service, _, _, _ = _service_com_fakes()

    with pytest.raises(FormatoDocumentoInvalidoError):
        service.gerar_curriculo_documento("informações brutas", "moderno", "jpg", str(tmp_path))
