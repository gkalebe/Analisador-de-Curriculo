import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.persistencia.models import Analise


class AnaliseRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, analise: Analise) -> Analise:
        self.db.add(analise)
        self.db.commit()
        self.db.refresh(analise)
        return analise

    def buscar_por_id(self, id_analise: uuid.UUID) -> Analise | None:
        stmt = (
            select(Analise)
            .options(joinedload(Analise.vaga), joinedload(Analise.curriculo))
            .where(Analise.id_analise == id_analise)
        )
        return self.db.execute(stmt).scalars().first()

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Analise]:
        stmt = (
            select(Analise)
            .options(joinedload(Analise.vaga), joinedload(Analise.curriculo))
            .where(Analise.id_usuario == id_usuario)
            .order_by(Analise.data_analise.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
