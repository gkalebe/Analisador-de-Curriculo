import uuid

from sqlalchemy.orm import Session

from app.core.persistencia.models import Analise


class AnaliseRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, analise: Analise) -> Analise:
        raise NotImplementedError

    def buscar_por_id(self, id_analise: uuid.UUID) -> Analise | None:
        raise NotImplementedError

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        raise NotImplementedError
