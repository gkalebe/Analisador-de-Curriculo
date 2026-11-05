import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, false, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Assinatura(Base):
    __tablename__ = "assinatura"
    __table_args__ = (
        UniqueConstraint("stripe_customer_id", name="uq_assinatura_stripe_customer_id"),
        UniqueConstraint("stripe_subscription_id", name="uq_assinatura_stripe_subscription_id"),
    )

    id_assinatura: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id_usuario", ondelete="CASCADE"), nullable=False, unique=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_schedule_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkout_plano_codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plano_codigo: Mapped[str] = mapped_column(String(20), nullable=False, default="free", server_default="free")
    plano_pendente_codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="free", server_default="free")
    cancelamento_agendado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    periodo_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    periodo_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inicio_cota: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fim_cota: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EventoStripe(Base):
    __tablename__ = "evento_stripe"

    id_evento: Mapped[str] = mapped_column(String(255), primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="processing", server_default="processing"
    )
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
