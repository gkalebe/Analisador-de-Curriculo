import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .analise import Analise
    from .candidato import Candidato
    from .usuario import Usuario


class Curriculo(Base):
    __tablename__ = "curriculo"

    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    data_upload: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_processamento: Mapped[str] = mapped_column(String(50), nullable=False, default="pendente")
    texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    conteudo_arquivo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="curriculos")
    candidato: Mapped["Candidato | None"] = relationship(
        back_populates="curriculo", uselist=False, cascade="all, delete-orphan"
    )
    analises: Mapped[list["Analise"]] = relationship(back_populates="curriculo", cascade="all, delete-orphan")