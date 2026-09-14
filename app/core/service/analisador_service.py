import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_parser.curriculo_parser import CurriculoParser
from app.core.config import get_settings
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models import Vaga
from app.core.persistencia.vaga_repository import VagaRepository


class DescricaoVagaObrigatoriaError(Exception):
    pass


class DescricaoVagaMuitoLongaError(Exception):
    pass


class AnalisadorService:
    def __init__(self, db: Session):
        self.curriculo_repository = CurriculoRepository(db)
        self.vaga_repository = VagaRepository(db)
        self.analise_repository = AnaliseRepository(db)
        self.curriculo_parser = CurriculoParser()
        self.ai_service_adapter = AIServiceAdapter()
        self.settings = get_settings()

    def processar_upload_curriculo(self, conteudo: bytes, nome_arquivo: str, extensao: str, id_usuario) -> dict:
        # Extrai o texto
        texto_extraido = self.curriculo_parser.extrair_texto(conteudo, extensao)

        # Cria registro de curriculo
        from app.core.persistencia.models import Curriculo
        novo_curriculo = Curriculo(
            nome_arquivo=nome_arquivo,
            id_usuario=id_usuario,
            status_processamento="processando"
        )
        self.curriculo_repository.criar(novo_curriculo)

        return {
            "id_curriculo": str(novo_curriculo.id_curriculo),
            "nome_arquivo": nome_arquivo,
            "tamanho_texto_extraido": len(texto_extraido),
        }

    def cadastrar_vaga(
        self,
        id_usuario: uuid.UUID,
        descricao: str,
        titulo: str | None = None,
        requisitos: str | None = None,
        area: str | None = None,
    ) -> Vaga:
        descricao_normalizada = (descricao or "").strip()
        if not descricao_normalizada:
            raise DescricaoVagaObrigatoriaError
        if len(descricao_normalizada) > self.settings.max_vaga_description_chars:
            raise DescricaoVagaMuitoLongaError

        vaga = Vaga(
            titulo=(titulo or "").strip() or None,
            descricao=descricao_normalizada,
            requisitos=(requisitos or "").strip() or None,
            area=(area or "").strip() or None,
            id_usuario=id_usuario,
        )
        return self.vaga_repository.criar(vaga)

    def listar_vagas_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        return self.vaga_repository.listar_por_usuario(id_usuario)
