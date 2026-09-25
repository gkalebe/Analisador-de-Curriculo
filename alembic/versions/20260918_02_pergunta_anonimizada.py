"""create pergunta_anonimizada table

Revision ID: 20260918_02
Revises: 20260918_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260918_02"
down_revision = "20260918_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pergunta_anonimizada",
        sa.Column("id_pergunta", sa.UUID(), nullable=False),
        sa.Column("pergunta", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id_pergunta"),
    )


def downgrade() -> None:
    op.drop_table("pergunta_anonimizada")
