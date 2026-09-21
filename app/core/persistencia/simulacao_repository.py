import uuid

from sqlalchemy import select
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

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[SimulacaoEntrevista]:
        stmt = (
            select(SimulacaoEntrevista)
            .where(SimulacaoEntrevista.id_usuario == id_usuario)
            .order_by(SimulacaoEntrevista.data_criacao.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def salvar_perguntas(self, simulacao: SimulacaoEntrevista, perguntas: list[dict]) -> SimulacaoEntrevista:
        simulacao.perguntas = perguntas
        self.db.add(simulacao)
        self.db.commit()
        self.db.refresh(simulacao)
        return simulacao
