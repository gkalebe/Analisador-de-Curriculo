import uuid

from sqlalchemy.orm import Session

from app.core.persistencia.models import Vaga


class VagaRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, vaga: Vaga) -> Vaga:
        raise NotImplementedError

    def buscar_por_id(self, id_vaga: uuid.UUID) -> Vaga | None:
        raise NotImplementedError

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        raise NotImplementedError
