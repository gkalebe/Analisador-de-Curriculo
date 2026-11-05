import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UsoIA(Base):
    __tablename__ = "uso_ia"
    __table_args__ = (
        Index("ix_uso_ia_usuario_janela_estado", "id_usuario", "inicio_janela", "fim_janela", "estado"),
    )

    id_uso: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id_usuario", ondelete="CASCADE"), nullable=False
    )
    tipo_operacao: Mapped[str] = mapped_column(String(40), nullable=False)
    categoria_orcamento: Mapped[str] = mapped_column(String(20), nullable=False)
    creditos: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    inicio_janela: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_janela: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
