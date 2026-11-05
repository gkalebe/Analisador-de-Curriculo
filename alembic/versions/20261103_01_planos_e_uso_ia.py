"""add plan code and metered AI usage reservations

Revision ID: 20261103_01
Revises: 20261016_01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261103_01"
down_revision = "20261016_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("plano_codigo", sa.String(length=20), server_default="free", nullable=False),
    )
    op.alter_column("usuario", "plano_codigo", server_default=None)
    op.create_table(
        "uso_ia",
        sa.Column("id_uso", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "id_usuario",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuario.id_usuario", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo_operacao", sa.String(length=40), nullable=False),
        sa.Column("categoria_orcamento", sa.String(length=20), nullable=False),
        sa.Column("creditos", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("inicio_janela", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_janela", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_uso_ia_usuario_janela_estado",
        "uso_ia",
        ["id_usuario", "inicio_janela", "fim_janela", "estado"],
    )


def downgrade() -> None:
    op.drop_index("ix_uso_ia_usuario_janela_estado", table_name="uso_ia")
    op.drop_table("uso_ia")
    op.drop_column("usuario", "plano_codigo")
