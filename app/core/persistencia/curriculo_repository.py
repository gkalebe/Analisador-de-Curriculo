import uuid

from sqlalchemy.orm import Session

from app.core.persistencia.models import Curriculo


class CurriculoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, curriculo: Curriculo) -> Curriculo:
        self.db.add(curriculo)
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def buscar_por_id(self, id_curriculo: uuid.UUID) -> Curriculo | None:
        raise NotImplementedError

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Curriculo]:
        raise NotImplementedError

    def atualizar_status(self, curriculo: Curriculo, status: str) -> Curriculo:
        curriculo.status_processamento = status
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def excluir(self, curriculo: Curriculo) -> None:
        raise NotImplementedError
