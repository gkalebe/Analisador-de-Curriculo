"""add account deletion field

Revision ID: 20260911_01
Revises: 6cabc8c4e959
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_01"
down_revision = "6cabc8c4e959"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # data_nascimento ja existe desde a migracao 6cabc8c4e959 (schema inicial)
    op.alter_column("usuario", "data_nascimento", existing_type=sa.Date(), nullable=True)
    op.add_column("usuario", sa.Column("exclusao_solicitada_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("usuario", "exclusao_solicitada_em")
    op.alter_column("usuario", "data_nascimento", existing_type=sa.Date(), nullable=False)