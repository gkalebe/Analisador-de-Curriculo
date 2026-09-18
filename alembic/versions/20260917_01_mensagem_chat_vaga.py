"""create mensagem_chat table

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
    op.create_table(
        "mensagem_chat",
        sa.Column("id_mensagem", sa.UUID(), nullable=False),
        sa.Column("id_usuario", sa.UUID(), nullable=False),
        sa.Column("id_curriculo", sa.UUID(), nullable=True),
        sa.Column("id_vaga", sa.UUID(), nullable=True),
        sa.Column("autor", sa.String(length=20), nullable=False),
        sa.Column("conteudo", sa.Text(), nullable=False),
        sa.Column("data_envio", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_curriculo"], ["curriculo.id_curriculo"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["id_vaga"], ["vaga.id_vaga"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_mensagem"),
    )


def downgrade() -> None:
    op.drop_table("mensagem_chat")
