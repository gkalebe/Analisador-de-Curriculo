"""repair curriculum edit and extraction columns

Revision ID: 20260925_02
Revises: 20260925_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260925_02"
down_revision = "20260925_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("curriculo")}

    if "dados_editados" not in colunas:
        op.add_column("curriculo", sa.Column("dados_editados", sa.JSON(), nullable=True))
    if "editado_em" not in colunas:
        op.add_column("curriculo", sa.Column("editado_em", sa.DateTime(timezone=True), nullable=True))
    if "dados_extraidos" not in colunas:
        op.add_column("curriculo", sa.Column("dados_extraidos", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas = {coluna["name"] for coluna in inspector.get_columns("curriculo")}

    if "dados_extraidos" in colunas:
        op.drop_column("curriculo", "dados_extraidos")
    if "editado_em" in colunas:
        op.drop_column("curriculo", "editado_em")
    if "dados_editados" in colunas:
        op.drop_column("curriculo", "dados_editados")
