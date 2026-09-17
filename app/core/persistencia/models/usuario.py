import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .analise import Analise
    from .curriculo import Curriculo
    from .vaga import Vaga


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(50), nullable=False, default="candidato")
    data_cadastro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exclusao_solicitada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    curriculos: Mapped[list["Curriculo"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    vagas: Mapped[list["Vaga"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    analises: Mapped[list["Analise"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")