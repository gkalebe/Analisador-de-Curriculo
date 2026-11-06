import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

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

    def buscar_por_id_para_atualizacao(self, id_simulacao: uuid.UUID) -> SimulacaoEntrevista | None:
        """SELECT ... FOR UPDATE: serializa avaliações concorrentes da mesma simulação. O lock
        dura até o próximo commit/rollback da sessão; `populate_existing` garante que o estado
        lido é o atual do banco, não o que já estava no identity map."""
        stmt = (
            select(SimulacaoEntrevista)
            .where(SimulacaoEntrevista.id_simulacao == id_simulacao)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def excluir(self, simulacao: SimulacaoEntrevista) -> None:
        self.db.delete(simulacao)
        self.db.commit()

    def listar_por_usuario(
        self, id_usuario: uuid.UUID, limit: int | None = None, offset: int = 0
    ) -> list[SimulacaoEntrevista]:
        stmt = (
            select(SimulacaoEntrevista)
            .options(joinedload(SimulacaoEntrevista.vaga))
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

    def salvar_avaliacao(
        self,
        simulacao: SimulacaoEntrevista,
        perguntas: list[dict],
        feedback_geral: str,
        nota_final: float | None,
        avaliada_em: datetime,
    ) -> SimulacaoEntrevista:
        simulacao.perguntas = perguntas
        simulacao.feedback_geral = feedback_geral
        simulacao.nota_final = nota_final
        simulacao.avaliada_em = avaliada_em
        self.db.add(simulacao)
        self.db.commit()
        self.db.refresh(simulacao)
        return simulacao
