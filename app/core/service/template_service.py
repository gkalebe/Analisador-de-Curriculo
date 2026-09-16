import json
import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)
from app.adapters.curriculo_exporter.curriculo_exporter import CurriculoExporter
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository


class NenhumaAnaliseEncontradaError(Exception):
    pass


class CurriculoNaoEncontradoError(Exception):
    pass


class TemplateNaoEncontradoError(Exception):
    pass


class FormatoExportacaoInvalidoError(Exception):
    pass


TEMPLATES = [
    {
        "id_template": "moderno",
        "nome": "Moderno",
        "descricao": "Layout com destaque em verde e seções bem demarcadas — indicado para tecnologia e design.",
        "preview_ficticio": {
            "nome": "Ana Beatriz Souza",
            "email": "ana.souza@email.com",
            "telefone": "(61) 99999-0000",
            "resumo": "Desenvolvedora backend pleno com 4 anos de experiência em Python e sistemas distribuídos.",
            "experiencia_profissional": (
                "Desenvolvedora Backend Pleno — Empresa XPTO (2023-atual)\n"
                "Desenvolvedora Backend Júnior — Empresa ABC (2021-2023)"
            ),
            "formacao": "Bacharelado em Ciência da Computação — Universidade Exemplo (2017-2021)",
            "habilidades": "Python, FastAPI, PostgreSQL, Docker, SQLAlchemy",
        },
    },
    {
        "id_template": "classico",
        "nome": "Clássico",
        "descricao": "Layout formal, centralizado e em preto e branco — indicado para áreas jurídica e financeira.",
        "preview_ficticio": {
            "nome": "Carlos Eduardo Lima",
            "email": "carlos.lima@email.com",
            "telefone": "(61) 98888-0000",
            "resumo": "Analista financeiro com sólida experiência em controladoria e planejamento orçamentário.",
            "experiencia_profissional": (
                "Analista Financeiro Sênior — Empresa Delta (2020-atual)\n"
                "Analista Financeiro Júnior — Empresa Gama (2018-2020)"
            ),
            "formacao": "Bacharelado em Ciências Contábeis — Universidade Exemplo (2014-2018)",
            "habilidades": "Excel avançado, SAP, análise de indicadores, orçamento empresarial",
        },
    },
    {
        "id_template": "minimalista",
        "nome": "Minimalista",
        "descricao": "Layout compacto, sem cores e com tipografia leve — indicado para quem prefere ir direto ao ponto.",
        "preview_ficticio": {
            "nome": "Fernanda Alves",
            "email": "fernanda.alves@email.com",
            "telefone": "(61) 97777-0000",
            "resumo": "Designer gráfica com foco em identidade visual e branding para pequenas empresas.",
            "experiencia_profissional": (
                "Designer Gráfica Freelancer (2019-atual)\n" "Estagiária de Design — Agência Criativa (2018-2019)"
            ),
            "formacao": "Tecnólogo em Design Gráfico — Universidade Exemplo (2016-2019)",
            "habilidades": "Adobe Illustrator, Photoshop, Figma, branding",
        },
    },
]

TEMPLATES_POR_ID = {template["id_template"]: template for template in TEMPLATES}

FORMATOS_SUPORTADOS = {"pdf", "docx"}


class TemplateService:
    def __init__(self, db: Session):
        self.curriculo_repository = CurriculoRepository(db)
        self.analise_repository = AnaliseRepository(db)
        self.ai_service_adapter = AIServiceAdapter()
        self.curriculo_exporter = CurriculoExporter()

    def listar_templates(self, id_usuario: uuid.UUID) -> list[dict]:
        analises = self.analise_repository.listar_por_usuario(id_usuario)
        if not analises:
            raise NenhumaAnaliseEncontradaError
        return TEMPLATES

    def exportar_curriculo(
        self,
        id_usuario: uuid.UUID,
        id_curriculo: uuid.UUID,
        id_template: str,
        formato: str,
    ) -> tuple[bytes, str, str]:
        if id_template not in TEMPLATES_POR_ID:
            raise TemplateNaoEncontradoError(id_template)
        if formato not in FORMATOS_SUPORTADOS:
            raise FormatoExportacaoInvalidoError(formato)

        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        dados = self._extrair_dados_curriculo(curriculo.texto_extraido or "")

        if formato == "pdf":
            conteudo = self.curriculo_exporter.gerar_pdf(dados, id_template)
            media_type = "application/pdf"
        else:
            conteudo = self.curriculo_exporter.gerar_docx(dados, id_template)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        nome_base = (dados.get("nome") or curriculo.nome_arquivo.rsplit(".", 1)[0] or "curriculo").strip()
        nome_arquivo = f"{nome_base} - {TEMPLATES_POR_ID[id_template]['nome']}.{formato}"
        return conteudo, nome_arquivo, media_type

    def _extrair_dados_curriculo(self, texto_extraido: str) -> dict:
        dados_vazios = {
            "nome": "",
            "email": "",
            "telefone": "",
            "resumo": "",
            "formacao": "",
            "experiencia_profissional": "",
            "habilidades": "",
            "texto_bruto": texto_extraido,
        }
        if not texto_extraido.strip():
            return dados_vazios

        try:
            resultado_ia = self.ai_service_adapter.extrair_dados_estruturados(texto_extraido)
        except (IAConfiguracaoAusenteError, IAIndisponivelError):
            return dados_vazios

        texto = (resultado_ia or "").strip()
        if texto.startswith("```"):
            texto = texto.strip("`").strip()
            if texto.lower().startswith("json"):
                texto = texto[4:].strip()

        try:
            dados_ia = json.loads(texto)
        except (json.JSONDecodeError, TypeError):
            return dados_vazios

        return {
            "nome": str(dados_ia.get("nome") or ""),
            "email": str(dados_ia.get("email") or ""),
            "telefone": str(dados_ia.get("telefone") or ""),
            "resumo": str(dados_ia.get("resumo") or ""),
            "formacao": str(dados_ia.get("formacao") or ""),
            "experiencia_profissional": str(dados_ia.get("experiencia_profissional") or ""),
            "habilidades": str(dados_ia.get("habilidades") or ""),
            "texto_bruto": texto_extraido,
        }
