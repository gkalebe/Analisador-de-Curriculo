"""Etapa 3 do pipeline: montagem do documento final (100% determinística, sem IA).

Esta etapa NUNCA chama IA — de propósito. O único contrato de entrada é o
schema Pydantic (`DadosCurriculoEstruturado`) já validado pela Etapa 2, nunca
texto solto vindo direto da IA. Isso é o que elimina o corte/perda de
informação do fluxo antigo (`curriculo_exporter.py`): lá, a IA reescrevia o
currículo em texto livre e esse texto era encaixado em seções fixas; aqui, a
IA só preenche campos de um schema, e o Jinja2 (via `docxtpl`) só substitui
esses campos num template .docx pronto — nenhuma etapa "reescreve" nada.

Isolada da Etapa 1 (não importa nada de `google.generativeai`) e da Etapa 2
(não importa `curriculo_validador`): só entende `DadosCurriculoEstruturado`.
Isso permite trocar o motor de template (docxtpl por outro) ou adicionar um
3º template visual sem tocar em uma linha da geração ou da validação.
"""

import shutil
import subprocess
from pathlib import Path

from docxtpl import DocxTemplate

from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado

DIRETORIO_TEMPLATES = Path(__file__).parent / "templates_estruturados"

TEMPLATES_DOCXTPL = {
    "moderno": DIRETORIO_TEMPLATES / "curriculo_moderno.docx",
    "classico": DIRETORIO_TEMPLATES / "curriculo_classico.docx",
}

TIMEOUT_CONVERSAO_PDF_SEGUNDOS = 60


class TemplateCurriculoNaoEncontradoError(Exception):
    pass


class ConversaoPdfError(Exception):
    pass


class MontadorDocumentoCurriculo:
    def __init__(self, caminho_libreoffice: str | None = None):
        # Permite injetar o binário do LibreOffice (ex.: em testes, ou se o
        # servidor tiver um caminho não padrão); em produção usa o "soffice"
        # já no PATH do servidor — sem depender de MS Word instalado.
        self._caminho_libreoffice = caminho_libreoffice or shutil.which("soffice") or "soffice"

    def gerar_docx(self, dados: DadosCurriculoEstruturado | dict, id_template: str, caminho_saida: str) -> str:
        """Popula o template .docx do `id_template` com `dados` e salva em `caminho_saida`."""
        caminho_template = TEMPLATES_DOCXTPL.get(id_template)
        if caminho_template is None or not caminho_template.exists():
            raise TemplateCurriculoNaoEncontradoError(id_template)

        documento = DocxTemplate(str(caminho_template))
        documento.render(self._construir_contexto(dados))

        Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
        documento.save(caminho_saida)
        return caminho_saida

    def converter_para_pdf(self, caminho_docx: str, diretorio_saida: str | None = None) -> str:
        """Converte um .docx já gerado para PDF via LibreOffice headless
        (`soffice --headless --convert-to pdf`) — cross-platform e adequado
        para servidor, sem depender de MS Word instalado."""
        caminho_docx_abs = Path(caminho_docx).resolve()
        diretorio_saida_abs = Path(diretorio_saida).resolve() if diretorio_saida else caminho_docx_abs.parent
        diretorio_saida_abs.mkdir(parents=True, exist_ok=True)

        try:
            resultado = subprocess.run(
                [
                    self._caminho_libreoffice,
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(diretorio_saida_abs),
                    str(caminho_docx_abs),
                ],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_CONVERSAO_PDF_SEGUNDOS,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as erro:
            raise ConversaoPdfError(
                "LibreOffice (soffice) não encontrado ou não respondeu a tempo. "
                "Instale o LibreOffice no servidor para habilitar exportação em PDF."
            ) from erro

        caminho_pdf = diretorio_saida_abs / (caminho_docx_abs.stem + ".pdf")
        if resultado.returncode != 0 or not caminho_pdf.exists():
            raise ConversaoPdfError(
                f"Falha ao converter '{caminho_docx_abs.name}' para PDF via LibreOffice "
                f"(código {resultado.returncode}): {resultado.stderr.strip()}"
            )
        return str(caminho_pdf)

    def _construir_contexto(self, dados: DadosCurriculoEstruturado | dict) -> dict:
        """Monta o dicionário de contexto do Jinja2 usando `.get()` com
        fallback para o valor padrão do schema em cada campo.

        Como a Etapa 2 sempre entrega um `DadosCurriculoEstruturado` completo
        (todo campo tem um valor padrão "" ou [], nunca fica ausente), isso
        praticamente nunca é exercido nesse caminho — mas protege o único
        outro caminho de entrada desta função, quando alguém chama
        `gerar_docx` direto com um `dict` cru (ex.: vindo de um teste, de uma
        migração de dados antiga, ou de uma fonte externa que pulou a Etapa
        2), evitando um `jinja2.exceptions.UndefinedError` no meio da
        renderização por causa de uma chave ausente.
        """
        bruto = dados.model_dump() if isinstance(dados, DadosCurriculoEstruturado) else dict(dados)
        padrao = DadosCurriculoEstruturado().model_dump()
        return {chave: bruto.get(chave, valor_padrao) for chave, valor_padrao in padrao.items()}
