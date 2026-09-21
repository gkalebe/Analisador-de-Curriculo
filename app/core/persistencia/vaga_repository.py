import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.persistencia.models.vaga import Vaga


class VagaRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, vaga: Vaga) -> Vaga:
        self.db.add(vaga)
        self.db.commit()
        self.db.refresh(vaga)
        return vaga

    def buscar_por_id(self, id_vaga: uuid.UUID) -> Vaga | None:
        return self.db.get(Vaga, id_vaga)

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        stmt = select(Vaga).where(Vaga.id_usuario == id_usuario).order_by(Vaga.data_criacao.desc())
        return list(self.db.execute(stmt).scalars().all())
