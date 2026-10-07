"""add dados_extraidos (cache de extracao por IA) ao curriculo

Revision ID: 20260918_03
Revises: 20260918_02
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_03"
down_revision = "20260918_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("curriculo", sa.Column("dados_extraidos", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("curriculo", "dados_extraidos")
