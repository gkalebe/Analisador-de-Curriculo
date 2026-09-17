import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .curriculo import Curriculo
    from .usuario import Usuario
    from .vaga import Vaga


class Analise(Base):
    __tablename__ = "analise"

    id_analise: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("curriculo.id_curriculo"), nullable=False)
    id_vaga: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vaga.id_vaga"), nullable=False)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)
    pontuacao: Mapped[float] = mapped_column(Float, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, nullable=True)
    data_analise: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    curriculo: Mapped["Curriculo"] = relationship(back_populates="analises")
    vaga: Mapped["Vaga"] = relationship(back_populates="analises")
    usuario: Mapped["Usuario"] = relationship(back_populates="analises")

    @property
    def titulo_vaga(self) -> str | None:
        return self.vaga.titulo if self.vaga else None

    @property
    def nome_curriculo(self) -> str | None:
        return self.curriculo.nome_arquivo if self.curriculo else None