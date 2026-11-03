"""store optional job posting context and source url

Revision ID: 20261016_01
Revises: 20261008_01
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_01"
down_revision = "20261008_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vaga", sa.Column("empresa", sa.String(length=200), nullable=True))
    op.add_column("vaga", sa.Column("localizacao", sa.String(length=200), nullable=True))
    op.add_column("vaga", sa.Column("modalidade", sa.String(length=100), nullable=True))
    op.add_column("vaga", sa.Column("senioridade", sa.String(length=100), nullable=True))
    op.add_column("vaga", sa.Column("tipo_contratacao", sa.String(length=100), nullable=True))
    op.add_column("vaga", sa.Column("faixa_salarial", sa.String(length=200), nullable=True))
    op.add_column("vaga", sa.Column("responsabilidades", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("requisitos_obrigatorios", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("requisitos_desejaveis", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("competencias", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("idiomas", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("beneficios", sa.Text(), nullable=True))
    op.add_column("vaga", sa.Column("url_origem", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("vaga", "url_origem")
    op.drop_column("vaga", "beneficios")
    op.drop_column("vaga", "idiomas")
    op.drop_column("vaga", "competencias")
    op.drop_column("vaga", "requisitos_desejaveis")
    op.drop_column("vaga", "requisitos_obrigatorios")
    op.drop_column("vaga", "responsabilidades")
    op.drop_column("vaga", "faixa_salarial")
    op.drop_column("vaga", "tipo_contratacao")
    op.drop_column("vaga", "senioridade")
    op.drop_column("vaga", "modalidade")
    op.drop_column("vaga", "localizacao")
    op.drop_column("vaga", "empresa")
