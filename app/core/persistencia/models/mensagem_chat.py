import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .curriculo import Curriculo
    from .usuario import Usuario
    from .vaga import Vaga


class MensagemChat(Base):
    __tablename__ = "mensagem_chat"

    id_mensagem: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)
    id_curriculo: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculo.id_curriculo", ondelete="CASCADE"), nullable=True
    )
    id_vaga: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaga.id_vaga", ondelete="CASCADE"), nullable=True
    )
    autor: Mapped[str] = mapped_column(String(20), nullable=False)
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    data_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="mensagens_chat")
    curriculo: Mapped["Curriculo | None"] = relationship(back_populates="mensagens_chat")
    vaga: Mapped["Vaga | None"] = relationship(back_populates="mensagens_chat")
