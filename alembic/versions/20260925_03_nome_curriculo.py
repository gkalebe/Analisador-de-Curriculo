"""add optional curriculum title

Revision ID: 20260925_03
Revises: 20260925_02
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_03"
down_revision = "20260925_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("curriculo", sa.Column("nome_curriculo", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("curriculo", "nome_curriculo")
