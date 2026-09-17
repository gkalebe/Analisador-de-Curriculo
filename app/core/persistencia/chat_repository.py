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

    def listar_por_curriculo(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> list[MensagemChat]:
        stmt = (
            select(MensagemChat)
            .where(MensagemChat.id_usuario == id_usuario, MensagemChat.id_curriculo == id_curriculo)
            .order_by(MensagemChat.data_envio.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
