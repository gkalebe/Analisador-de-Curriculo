import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .curriculo import Curriculo


class Candidato(Base):
    __tablename__ = "candidato"

    id_candidato: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str] = mapped_column(String(30), nullable=True)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    formacao: Mapped[str] = mapped_column(Text, nullable=True)
    experiencia_profissional: Mapped[str] = mapped_column(Text, nullable=True)
    habilidades: Mapped[str] = mapped_column(Text, nullable=True)
    id_curriculo: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curriculo.id_curriculo"), nullable=False, unique=True
    )

    curriculo: Mapped["Curriculo"] = relationship(back_populates="candidato")