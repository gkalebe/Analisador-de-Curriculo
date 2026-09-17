"""add id_vaga to mensagem_chat and make id_curriculo nullable

Revision ID: 20260917_01
Revises: 20260915_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260917_01"
down_revision = "20260915_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("mensagem_chat", "id_curriculo", existing_type=sa.UUID(), nullable=True)
    op.add_column(
        "mensagem_chat",
        sa.Column("id_vaga", sa.UUID(), sa.ForeignKey("vaga.id_vaga", ondelete="CASCADE"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mensagem_chat", "id_vaga")
    op.alter_column("mensagem_chat", "id_curriculo", existing_type=sa.UUID(), nullable=False)
