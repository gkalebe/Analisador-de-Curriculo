import uuid

import pytest

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.core.persistencia.models.analise import Analise
from app.core.persistencia.models.curriculo import Curriculo
from app.core.service.template_service import (
    TEMPLATES,
    CurriculoNaoEncontradoError,
    FormatoExportacaoInvalidoError,
    NenhumaAnaliseEncontradaError,
    TemplateNaoEncontradoError,
    TemplateService,
)


class AnaliseRepositorioFalso:
    def __init__(self, analises: list[Analise] | None = None):
        self.analises = analises or []

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        return [analise for analise in self.analises if analise.id_usuario == id_usuario]


class CurriculoRepositorioFalso:
    def __init__(self, curriculos: list[Curriculo] | None = None):
        self.curriculos = curriculos or []

    def buscar_por_id(self, id_curriculo: uuid.UUID) -> Curriculo | None:
        return next((c for c in self.curriculos if c.id_curriculo == id_curriculo), None)


class AIServiceAdapterFalso:
    def __init__(self, resposta: str | None = None, erro: Exception | None = None):
        self.resposta = resposta
        self.erro = erro

    def extrair_dados_estruturados(self, texto_curriculo: str) -> str:
        if self.erro:
            raise self.erro
        return self.resposta


class CurriculoExporterFalso:
    def __init__(self):
        self.chamadas: list[tuple[str, dict, str]] = []

    def gerar_pdf(self, dados: dict, id_template: str) -> bytes:
        self.chamadas.append(("pdf", dados, id_template))
        return b"conteudo-pdf"

    def gerar_docx(self, dados: dict, id_template: str) -> bytes:
        self.chamadas.append(("docx", dados, id_template))
        return b"conteudo-docx"


RESPOSTA_IA_PADRAO = (
    '{"nome": "Ana Silva", "email": "ana@email.com", "telefone": "", '
    '"resumo": "Resumo.", "formacao": "Formação.", '
    '"experiencia_profissional": "Experiência.", "habilidades": "Python"}'
)


def _criar_service_com_fakes(analises=None, curriculos=None, ai_adapter=None, exporter=None) -> TemplateService:
    service = TemplateService(db=None)
    service.analise_repository = AnaliseRepositorioFalso(analises)
    service.curriculo_repository = CurriculoRepositorioFalso(curriculos)
    service.ai_service_adapter = ai_adapter or AIServiceAdapterFalso(resposta=RESPOSTA_IA_PADRAO)
    service.curriculo_exporter = exporter or CurriculoExporterFalso()
    return service


def test_listar_templates_com_analise_retorna_lista():
    id_usuario = uuid.uuid4()
    analise = Analise(id_usuario=id_usuario, id_curriculo=uuid.uuid4(), id_vaga=uuid.uuid4())
    service = _criar_service_com_fakes(analises=[analise])

    templates = service.listar_templates(id_usuario)

    assert templates == TEMPLATES
    assert len(templates) >= 3


def test_listar_templates_sem_analise_lanca_erro():
    service = _criar_service_com_fakes(analises=[])

    with pytest.raises(NenhumaAnaliseEncontradaError):
        service.listar_templates(uuid.uuid4())


def test_exportar_curriculo_com_sucesso_usa_dados_estruturados_da_ia():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(),
        id_usuario=id_usuario,
        nome_arquivo="curriculo.pdf",
        texto_extraido="texto bruto do currículo",
    )
    exporter = CurriculoExporterFalso()
    service = _criar_service_com_fakes(curriculos=[curriculo], exporter=exporter)

    conteudo, nome_arquivo, media_type = service.exportar_curriculo(
        id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="moderno", formato="pdf"
    )

    assert conteudo == b"conteudo-pdf"
    assert media_type == "application/pdf"
    assert "Ana Silva" in nome_arquivo
    assert exporter.chamadas[0][1]["nome"] == "Ana Silva"


def test_exportar_curriculo_formato_docx():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=id_usuario, nome_arquivo="curriculo.pdf", texto_extraido="texto"
    )
    service = _criar_service_com_fakes(curriculos=[curriculo])

    conteudo, _, media_type = service.exportar_curriculo(
        id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="classico", formato="docx"
    )

    assert conteudo == b"conteudo-docx"
    assert media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_exportar_curriculo_com_ia_indisponivel_usa_fallback_com_texto_bruto():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=id_usuario, nome_arquivo="curriculo.pdf", texto_extraido="texto bruto"
    )
    exporter = CurriculoExporterFalso()
    ai_adapter = AIServiceAdapterFalso(erro=IAIndisponivelError("timeout"))
    service = _criar_service_com_fakes(curriculos=[curriculo], ai_adapter=ai_adapter, exporter=exporter)

    conteudo, _, _ = service.exportar_curriculo(
        id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="minimalista", formato="pdf"
    )

    assert conteudo == b"conteudo-pdf"
    dados_usados = exporter.chamadas[0][1]
    assert dados_usados["nome"] == ""
    assert dados_usados["texto_bruto"] == "texto bruto"


def test_exportar_curriculo_com_ia_sem_configuracao_usa_fallback():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=id_usuario, nome_arquivo="curriculo.pdf", texto_extraido="texto bruto"
    )
    ai_adapter = AIServiceAdapterFalso(erro=IAConfiguracaoAusenteError("sem chave"))
    service = _criar_service_com_fakes(curriculos=[curriculo], ai_adapter=ai_adapter)

    conteudo, _, _ = service.exportar_curriculo(
        id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="moderno", formato="pdf"
    )

    assert conteudo == b"conteudo-pdf"


def test_exportar_curriculo_com_curriculo_de_outro_usuario_lanca_erro():
    dono = uuid.uuid4()
    outro = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=dono, nome_arquivo="curriculo.pdf", texto_extraido="texto"
    )
    service = _criar_service_com_fakes(curriculos=[curriculo])

    with pytest.raises(CurriculoNaoEncontradoError):
        service.exportar_curriculo(
            id_usuario=outro, id_curriculo=curriculo.id_curriculo, id_template="moderno", formato="pdf"
        )


def test_exportar_curriculo_com_template_inexistente_lanca_erro():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=id_usuario, nome_arquivo="curriculo.pdf", texto_extraido="texto"
    )
    service = _criar_service_com_fakes(curriculos=[curriculo])

    with pytest.raises(TemplateNaoEncontradoError):
        service.exportar_curriculo(
            id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="inexistente", formato="pdf"
        )


def test_exportar_curriculo_com_formato_invalido_lanca_erro():
    id_usuario = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(), id_usuario=id_usuario, nome_arquivo="curriculo.pdf", texto_extraido="texto"
    )
    service = _criar_service_com_fakes(curriculos=[curriculo])

    with pytest.raises(FormatoExportacaoInvalidoError):
        service.exportar_curriculo(
            id_usuario=id_usuario, id_curriculo=curriculo.id_curriculo, id_template="moderno", formato="jpg"
        )
