"""add texto_extraido to curriculo

Revision ID: 20260915_01
Revises: 20260911_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260915_01"
down_revision = "20260911_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("curriculo", sa.Column("texto_extraido", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("curriculo", "texto_extraido")
