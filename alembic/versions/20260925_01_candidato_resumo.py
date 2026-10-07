"""add resumo to candidato

Revision ID: 20260925_01
Revises: 20260921_01
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_01"
down_revision = "20260921_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidato", sa.Column("resumo", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("candidato", "resumo")
