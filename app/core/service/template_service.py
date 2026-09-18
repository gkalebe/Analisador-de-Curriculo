import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_exporter.curriculo_exporter import CurriculoExporter
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.service.extracao_curriculo import (
    extrair_dados_estruturados_curriculo,
    normalizar_dados_editados,
)


class NenhumaAnaliseEncontradaError(Exception):
    pass


class CurriculoNaoEncontradoError(Exception):
    pass


class TemplateNaoEncontradoError(Exception):
    pass


class FormatoExportacaoInvalidoError(Exception):
    pass


class VersaoExportacaoInvalidaError(Exception):
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
    {
        "id_template": "executivo",
        "nome": "Executivo",
        "descricao": (
            "Layout de alto contraste com títulos de seção em barra sólida azul-marinho — indicado para cargos "
            "de liderança e gestão."
        ),
        "preview_ficticio": {
            "nome": "Rafael Menezes Costa",
            "email": "rafael.costa@email.com",
            "telefone": "(61) 96666-0000",
            "resumo": "Gerente de Operações com 10 anos de experiência liderando equipes multidisciplinares.",
            "experiencia_profissional": (
                "Gerente de Operações — Empresa Prisma (2021-atual)\n"
                "Coordenador de Operações — Empresa Vetor (2016-2021)"
            ),
            "formacao": "MBA em Gestão Empresarial — Universidade Exemplo (2015-2016)",
            "habilidades": "Gestão de equipes, planejamento estratégico, KPIs, negociação",
        },
    },
    {
        "id_template": "criativo",
        "nome": "Criativo",
        "descricao": (
            "Layout com barra de destaque na lateral e habilidades em tags coloridas — indicado para marketing "
            "e comunicação."
        ),
        "preview_ficticio": {
            "nome": "Juliana Prado Martins",
            "email": "juliana.prado@email.com",
            "telefone": "(61) 95555-0000",
            "resumo": "Analista de Marketing com foco em redes sociais e campanhas de performance.",
            "experiencia_profissional": (
                "Analista de Marketing Pleno — Empresa Vívido (2022-atual)\n"
                "Analista de Marketing Júnior — Agência Nexo (2020-2022)"
            ),
            "formacao": "Bacharelado em Publicidade e Propaganda — Universidade Exemplo (2016-2020)",
            "habilidades": "Redes sociais, Google Ads, copywriting, análise de métricas",
        },
    },
]

TEMPLATES_POR_ID = {template["id_template"]: template for template in TEMPLATES}

FORMATOS_SUPORTADOS = {"pdf", "docx"}
VERSOES_SUPORTADAS = {"original", "editada"}


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
        versao: str = "original",
    ) -> tuple[bytes, str, str]:
        if id_template not in TEMPLATES_POR_ID:
            raise TemplateNaoEncontradoError(id_template)
        if formato not in FORMATOS_SUPORTADOS:
            raise FormatoExportacaoInvalidoError(formato)
        if versao not in VERSOES_SUPORTADAS:
            raise VersaoExportacaoInvalidaError(versao)

        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        # "editada" usa os dados que o usuário revisou/ajustou na tela de edição (já
        # incorporando as sugestões da análise), sem nova chamada à IA. Se ainda não existir
        # edição salva, caímos graciosamente para o comportamento padrão ("original").
        if versao == "editada" and curriculo.dados_editados:
            dados = normalizar_dados_editados(curriculo.dados_editados, curriculo.texto_extraido or "")
        else:
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
        return extrair_dados_estruturados_curriculo(self.ai_service_adapter, texto_extraido)
