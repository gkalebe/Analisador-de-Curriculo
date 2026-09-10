from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.adapters.curriculo_parser.curriculo_parser import CurriculoParser
from app.core.persistencia.analise_repository import AnaliseRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.vaga_repository import VagaRepository


class AnalisadorService:
    def __init__(self, db: Session):
        self.curriculo_repository = CurriculoRepository(db)
        self.vaga_repository = VagaRepository(db)
        self.analise_repository = AnaliseRepository(db)
        self.curriculo_parser = CurriculoParser()
        self.ai_service_adapter = AIServiceAdapter()

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
            "texto_extraido_tamanho": len(texto_extraido)
        }
