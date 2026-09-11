"""add account registration and deletion fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuario", sa.Column("data_nascimento", sa.Date(), nullable=True))
    op.add_column("usuario", sa.Column("exclusao_solicitada_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("usuario", "exclusao_solicitada_em")
    op.drop_column("usuario", "data_nascimento")