import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

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

    def atualizar_status(self, curriculo: Curriculo, status: str) -> Curriculo:
        curriculo.status_processamento = status
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def excluir(self, curriculo: Curriculo) -> None:
        self.db.delete(curriculo)
        self.db.commit()

    def salvar_edicao(self, curriculo: Curriculo, dados_editados: dict) -> Curriculo:
        curriculo.dados_editados = dados_editados
        curriculo.editado_em = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo

    def salvar_dados_extraidos(self, curriculo: Curriculo, dados_extraidos: dict) -> Curriculo:
        curriculo.dados_extraidos = dados_extraidos
        self.db.commit()
        self.db.refresh(curriculo)
        return curriculo
