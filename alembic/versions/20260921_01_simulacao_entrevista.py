"""create simulacao_entrevista table

Revision ID: 20260921_01
Revises: 20260918_03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_01"
down_revision = "20260918_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulacao_entrevista",
        sa.Column("id_simulacao", sa.UUID(), nullable=False),
        sa.Column("id_usuario", sa.UUID(), nullable=False),
        sa.Column("id_vaga", sa.UUID(), nullable=False),
        sa.Column("perguntas", sa.JSON(), nullable=False),
        sa.Column("data_criacao", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario"], ["usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_vaga"], ["vaga.id_vaga"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id_simulacao"),
    )


def downgrade() -> None:
    op.drop_table("simulacao_entrevista")
