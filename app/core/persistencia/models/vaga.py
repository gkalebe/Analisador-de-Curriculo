import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .analise import Analise
    from .mensagem_chat import MensagemChat
    from .usuario import Usuario


class Vaga(Base):
    __tablename__ = "vaga"

    id_vaga: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    requisitos: Mapped[str] = mapped_column(Text, nullable=True)
    area: Mapped[str] = mapped_column(String(100), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="vagas")
    analises: Mapped[list["Analise"]] = relationship(back_populates="vaga", cascade="all, delete-orphan")
    mensagens_chat: Mapped[list["MensagemChat"]] = relationship(
        back_populates="vaga", cascade="all, delete-orphan"
    )