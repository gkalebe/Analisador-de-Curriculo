import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.persistencia.models.mensagem_chat import MensagemChat


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, mensagem: MensagemChat) -> MensagemChat:
        self.db.add(mensagem)
        self.db.commit()
        self.db.refresh(mensagem)
        return mensagem

    def listar(
        self,
        id_usuario: uuid.UUID,
        id_curriculo: uuid.UUID | None = None,
        id_vaga: uuid.UUID | None = None,
    ) -> list[MensagemChat]:
        condicoes = [MensagemChat.id_usuario == id_usuario]
        if id_curriculo is not None and id_vaga is not None:
            condicoes.append(MensagemChat.id_curriculo == id_curriculo)
            condicoes.append(MensagemChat.id_vaga == id_vaga)
        elif id_curriculo is not None:
            condicoes.append(MensagemChat.id_curriculo == id_curriculo)
            condicoes.append(MensagemChat.id_vaga.is_(None))
        elif id_vaga is not None:
            condicoes.append(MensagemChat.id_vaga == id_vaga)
            condicoes.append(MensagemChat.id_curriculo.is_(None))

        stmt = select(MensagemChat).where(*condicoes).order_by(MensagemChat.data_envio.asc())
        return list(self.db.execute(stmt).scalars().all())

    def listar_por_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> list[MensagemChat]:
        return self.listar(id_usuario, id_curriculo=id_curriculo, id_vaga=None)

    def listar_por_vaga(self, id_usuario: uuid.UUID, id_vaga: uuid.UUID) -> list[MensagemChat]:
        return self.listar(id_usuario, id_curriculo=None, id_vaga=id_vaga)
