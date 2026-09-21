import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PerguntaAnonimizada(Base):
    """
    Pergunta extraída de uma conversa do ChatBOT ao ser encerrada, sem nenhum vínculo com o
    usuário ou com a resposta dada — alimenta a "árvore de dados" de dúvidas recorrentes do
    sistema. Nunca grava id_usuario, id_curriculo, id_vaga ou a resposta da IA.
    """

    __tablename__ = "pergunta_anonimizada"

    id_pergunta: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pergunta: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
