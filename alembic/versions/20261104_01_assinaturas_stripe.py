"""persist Stripe subscriptions and webhook idempotency

Revision ID: 20261104_01
Revises: 20261103_01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261104_01"
down_revision = "20261103_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assinatura",
        sa.Column("id_assinatura", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "id_usuario",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_schedule_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("plano_codigo", sa.String(length=20), nullable=False, server_default="free"),
        sa.Column("plano_pendente_codigo", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="free"),
        sa.Column("cancelamento_agendado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("periodo_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("periodo_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inicio_cota", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_cota", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("stripe_customer_id", name="uq_assinatura_stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id", name="uq_assinatura_stripe_subscription_id"),
    )
    op.create_table(
        "evento_stripe",
        sa.Column("id_evento", sa.String(length=255), primary_key=True, nullable=False),
        sa.Column("tipo_evento", sa.String(length=120), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("recebido_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("evento_stripe")
    op.drop_table("assinatura")
