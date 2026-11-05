import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista


class SimulacaoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, simulacao: SimulacaoEntrevista) -> SimulacaoEntrevista:
        self.db.add(simulacao)
        self.db.commit()
        self.db.refresh(simulacao)
        return simulacao

    def buscar_por_id(self, id_simulacao: uuid.UUID) -> SimulacaoEntrevista | None:
        return self.db.get(SimulacaoEntrevista, id_simulacao)

    def listar_por_usuario(
        self, id_usuario: uuid.UUID, limit: int | None = None, offset: int = 0
    ) -> list[SimulacaoEntrevista]:
        stmt = (
            select(SimulacaoEntrevista)
            .where(SimulacaoEntrevista.id_usuario == id_usuario)
            .order_by(SimulacaoEntrevista.data_criacao.desc(), SimulacaoEntrevista.id_simulacao)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def contar_por_usuario(self, id_usuario: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(SimulacaoEntrevista)
            .where(SimulacaoEntrevista.id_usuario == id_usuario)
        )
        return self.db.execute(stmt).scalar_one()

    def salvar_perguntas(self, simulacao: SimulacaoEntrevista, perguntas: list[dict]) -> SimulacaoEntrevista:
        simulacao.perguntas = perguntas
        self.db.add(simulacao)
        self.db.commit()
        self.db.refresh(simulacao)
        return simulacao
