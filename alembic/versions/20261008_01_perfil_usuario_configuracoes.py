"""persist user email notification preference

Revision ID: 20261008_01
Revises: 20260925_03
"""

import sqlalchemy as sa

from alembic import op

revision = "20261008_01"
down_revision = "20260925_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuario",
        sa.Column("notificacoes_por_email", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.alter_column("usuario", "notificacoes_por_email", server_default=None)


def downgrade() -> None:
    op.drop_column("usuario", "notificacoes_por_email")
