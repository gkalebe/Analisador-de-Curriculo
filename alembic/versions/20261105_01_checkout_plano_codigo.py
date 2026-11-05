"""store the pending Checkout plan separately from scheduled downgrades

Revision ID: 20261105_01
Revises: 20261104_01
"""

from alembic import op
import sqlalchemy as sa

revision = "20261105_01"
down_revision = "20261104_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assinatura", sa.Column("checkout_plano_codigo", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("assinatura", "checkout_plano_codigo")
