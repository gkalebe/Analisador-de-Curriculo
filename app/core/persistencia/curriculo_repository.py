import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.persistencia.models.candidato import Candidato
from app.core.persistencia.models.curriculo import Curriculo


class CurriculoRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, curriculo: Curriculo) -> Curriculo:
        self.db.add(curriculo)
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def buscar_por_id(self, id_curriculo: uuid.UUID) -> Curriculo | None:
        return self.db.get(Curriculo, id_curriculo)

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Curriculo]:
        stmt = select(Curriculo).where(Curriculo.id_usuario == id_usuario).order_by(Curriculo.data_upload.desc())
        return list(self.db.execute(stmt).scalars().all())

    def buscar_candidato(self, id_curriculo: uuid.UUID) -> Candidato | None:
        return self.db.query(Candidato).filter(Candidato.id_curriculo == id_curriculo).one_or_none()

    def salvar_candidato(self, id_curriculo: uuid.UUID, dados: dict) -> Candidato:
        candidato = self.buscar_candidato(id_curriculo)
        if candidato is None:
            candidato = Candidato(id_curriculo=id_curriculo)

        for campo in (
            "nome",
            "email",
            "telefone",
            "resumo",
            "formacao",
            "experiencia_profissional",
            "habilidades",
        ):
            valor = dados.get(campo)
            if valor is not None:
                setattr(candidato, campo, valor)

        self.db.add(candidato)
        self.db.commit()
        self.db.refresh(candidato)
        return candidato

    def atualizar_status(self, curriculo: Curriculo, status: str) -> Curriculo:
        curriculo.status_processamento = status
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def excluir(self, curriculo: Curriculo) -> None:
        self.db.delete(curriculo)
        self.db.commit()
