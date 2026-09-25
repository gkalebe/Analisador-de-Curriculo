"""Orquestração das 3 etapas do pipeline de geração estruturada de currículo.

Este service NÃO reimplementa nenhuma das 3 etapas — só as encadeia, na
ordem Etapa 1 (`GeradorCurriculoEstruturadoIA`) → Etapa 2
(`ValidadorCurriculoEstruturado`) → Etapa 3 (`MontadorDocumentoCurriculo`).
Cada etapa continua podendo ser testada, chamada ou substituída de forma
independente — este service é só a "cola" para o caso de uso comum de ponta
a ponta (texto bruto do usuário → arquivo .docx/.pdf final).
"""

import uuid
from pathlib import Path

from app.adapters.ai_service.curriculo_estruturado_client import GeradorCurriculoEstruturadoIA
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado
from app.adapters.curriculo_exporter.curriculo_template_exporter import (
    TEMPLATES_DOCXTPL,
    MontadorDocumentoCurriculo,
    TemplateCurriculoNaoEncontradoError,
)
from app.core.service.curriculo_validador import ValidadorCurriculoEstruturado

FORMATOS_SUPORTADOS = {"docx", "pdf"}


class FormatoDocumentoInvalidoError(Exception):
    pass


class CurriculoEstruturadoService:
    def __init__(
        self,
        gerador: GeradorCurriculoEstruturadoIA | None = None,
        validador: ValidadorCurriculoEstruturado | None = None,
        montador: MontadorDocumentoCurriculo | None = None,
    ):
        self._gerador = gerador or GeradorCurriculoEstruturadoIA()
        self._validador = validador or ValidadorCurriculoEstruturado(self._gerador)
        self._montador = montador or MontadorDocumentoCurriculo()

    def gerar_curriculo_documento(
        self,
        informacoes_brutas: str,
        id_template: str,
        formato: str,
        diretorio_saida: str,
    ) -> tuple[str, list[str]]:
        """Roda as 3 etapas de ponta a ponta.

        Retorna (caminho_arquivo_gerado, campos_que_precisaram_de_retry).

        Levanta `FormatoDocumentoInvalidoError` (formato fora de
        `FORMATOS_SUPORTADOS`), `IAConfiguracaoAusenteError`/
        `IAIndisponivelError`/`IARespostaInvalidaError` (Etapa 1),
        `CurriculoInvalidoError` (Etapa 2) ou
        `TemplateCurriculoNaoEncontradoError`/`ConversaoPdfError` (Etapa 3) —
        cada uma definida no módulo da etapa correspondente, para o chamador
        (router/CLI) tratar cada falha de forma específica.
        """
        if formato not in FORMATOS_SUPORTADOS:
            raise FormatoDocumentoInvalidoError(formato)

        dados_brutos_ia = self._gerador.gerar(informacoes_brutas).model_dump()
        dados_validados, campos_com_retry = self._validador.validar_e_reparar(dados_brutos_ia, informacoes_brutas)

        caminho_docx = str(Path(diretorio_saida) / f"{uuid.uuid4()}.docx")
        self._montador.gerar_docx(dados_validados, id_template, caminho_docx)

        if formato == "docx":
            return caminho_docx, campos_com_retry

        caminho_pdf = self._montador.converter_para_pdf(caminho_docx, diretorio_saida)
        return caminho_pdf, campos_com_retry

    def gerar_documento_a_partir_de_dados(
        self,
        dados: DadosCurriculoEstruturado,
        id_template: str,
        formato: str,
        diretorio_saida: str,
    ) -> str:
        """Roda só a Etapa 3, para quem já tem `DadosCurriculoEstruturado`
        validados (ex.: vindos de um formulário preenchido manualmente, sem
        passar pelas Etapas 1/2 de geração por IA)."""
        if formato not in FORMATOS_SUPORTADOS:
            raise FormatoDocumentoInvalidoError(formato)
        if id_template not in TEMPLATES_DOCXTPL:
            raise TemplateCurriculoNaoEncontradoError(id_template)

        caminho_docx = str(Path(diretorio_saida) / f"{uuid.uuid4()}.docx")
        self._montador.gerar_docx(dados, id_template, caminho_docx)
        if formato == "docx":
            return caminho_docx
        return self._montador.converter_para_pdf(caminho_docx, diretorio_saida)
