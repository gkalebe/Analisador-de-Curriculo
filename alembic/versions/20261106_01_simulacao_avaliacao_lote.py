"""store batch evaluation result on simulacao_entrevista

Revision ID: 20261106_01
Revises: 20261105_01

Colunas nulas: as simulações antigas (avaliadas pergunta a pergunta) continuam válidas e são
tratadas como "legadas" (somente leitura) pela aplicação. Nada em `uso_ia` precisa migrar:
`tipo_operacao` é texto livre sem constraint, e os registros antigos `entrevista_feedback`
seguem contando seus créditos na janela de cota vigente (só deixam de contar como operação).
"""

from alembic import op
import sqlalchemy as sa

revision = "20261106_01"
down_revision = "20261105_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("simulacao_entrevista", sa.Column("avaliada_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("simulacao_entrevista", sa.Column("nota_final", sa.Float(), nullable=True))
    op.add_column("simulacao_entrevista", sa.Column("feedback_geral", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulacao_entrevista", "feedback_geral")
    op.drop_column("simulacao_entrevista", "nota_final")
    op.drop_column("simulacao_entrevista", "avaliada_em")
