import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_exporter.curriculo_exporter import CurriculoExporter
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.service.extracao_curriculo import (
    normalizar_dados_editados,
    obter_dados_curriculo_com_cache,
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
        "id_template": "generico",
        "nome": "Genérico / Multiuso",
        "descricao": "Layout neutro em azul-marinho, direto ao ponto — indicado para qualquer área quando não há um template mais específico.",
        "preview_ficticio": {
            "nome": "Ana Beatriz Souza",
            "email": "ana.souza@email.com",
            "telefone": "(61) 99999-0000",
            "resumo": "Profissional administrativa com 4 anos de experiência em rotinas de escritório, atendimento e organização de processos.",
            "experiencia_profissional": (
                "Assistente Administrativa — Empresa XPTO (2023-atual)\n"
                "Auxiliar Administrativo — Empresa ABC (2021-2023)"
            ),
            "formacao": "Bacharelado em Administração — Universidade Exemplo (2017-2021)",
            "habilidades": "Pacote Office, atendimento ao cliente, organização, rotinas administrativas",
        },
    },
    {
        "id_template": "tecnologia",
        "nome": "Tecnologia / TI",
        "descricao": "Layout em verde-azulado com seções bem demarcadas — indicado para desenvolvimento, dados e áreas técnicas.",
        "preview_ficticio": {
            "nome": "Carlos Eduardo Lima",
            "email": "carlos.lima@email.com",
            "telefone": "(61) 98888-0000",
            "resumo": "Desenvolvedor backend pleno com 4 anos de experiência em Python e sistemas distribuídos.",
            "experiencia_profissional": (
                "Desenvolvedor Backend Pleno — Empresa Delta (2020-atual)\n"
                "Desenvolvedor Backend Júnior — Empresa Gama (2018-2020)"
            ),
            "formacao": "Bacharelado em Ciência da Computação — Universidade Exemplo (2014-2018)",
            "habilidades": "Python, FastAPI, PostgreSQL, Docker, SQLAlchemy",
        },
    },
    {
        "id_template": "estagio",
        "nome": "Entrada / Estágio",
        "descricao": "Layout em laranja, acolhedor e objetivo — indicado para quem está começando (estágio, trainee, primeiro emprego).",
        "preview_ficticio": {
            "nome": "Fernanda Alves",
            "email": "fernanda.alves@email.com",
            "telefone": "(61) 97777-0000",
            "resumo": "Estudante de Design Gráfico, em busca da primeira oportunidade de estágio na área de branding.",
            "experiencia_profissional": (
                "Estagiária de Design — Agência Criativa (2023-atual)\n" "Monitora de laboratório — Universidade Exemplo (2022-2023)"
            ),
            "formacao": "Tecnólogo em Design Gráfico (cursando) — Universidade Exemplo (2020-atual)",
            "habilidades": "Adobe Illustrator, Photoshop, Figma, branding",
        },
    },
    {
        "id_template": "gestao",
        "nome": "Gestão / Coordenação",
        "descricao": "Layout sóbrio em tom terracota — indicado para cargos de liderança, coordenação e gestão de equipes.",
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
        "id_template": "setor_publico",
        "nome": "Setor Público",
        "descricao": "Layout formal em verde escuro — indicado para vagas em órgãos públicos, concursos e processos seletivos institucionais.",
        "preview_ficticio": {
            "nome": "Juliana Prado Martins",
            "email": "juliana.prado@email.com",
            "telefone": "(61) 95555-0000",
            "resumo": "Analista administrativa com experiência em órgão público, atuando em processos de atendimento e conformidade.",
            "experiencia_profissional": (
                "Analista Administrativa — Ministério Exemplo (2022-atual)\n"
                "Estagiária — Secretaria Municipal Exemplo (2020-2022)"
            ),
            "formacao": "Bacharelado em Administração Pública — Universidade Exemplo (2016-2020)",
            "habilidades": "Atendimento ao público, processos administrativos, Lei nº 8.112/1990, redação oficial",
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
        # edição salva, caímos graciosamente para o comportamento padrão ("original"), que por
        # sua vez reaproveita a extração já em cache (dados_extraidos) em vez de chamar a IA de
        # novo a cada exportação — ver obter_dados_curriculo_com_cache.
        if versao == "editada" and curriculo.dados_editados:
            dados = normalizar_dados_editados(curriculo.dados_editados, curriculo.texto_extraido or "")
        else:
            dados = obter_dados_curriculo_com_cache(curriculo, self.ai_service_adapter, self.curriculo_repository)

        if formato == "pdf":
            conteudo = self.curriculo_exporter.gerar_pdf(dados, id_template)
            media_type = "application/pdf"
        else:
            conteudo = self.curriculo_exporter.gerar_docx(dados, id_template)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        nome_base = (dados.get("nome") or curriculo.nome_arquivo.rsplit(".", 1)[0] or "curriculo").strip()
        nome_arquivo = f"{nome_base} - {TEMPLATES_POR_ID[id_template]['nome']}.{formato}"
        return conteudo, nome_arquivo, media_type
