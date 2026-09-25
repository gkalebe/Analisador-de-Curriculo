import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .usuario import Usuario
    from .vaga import Vaga


class SimulacaoEntrevista(Base):
    __tablename__ = "simulacao_entrevista"

    id_simulacao: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)
    id_vaga: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vaga.id_vaga", ondelete="CASCADE"), nullable=False
    )
    # Cada item: {id_pergunta, tipo (comportamental/tecnica/situacional), texto, resposta,
    # feedback: {clareza, objetividade, coerencia, alinhamento, geral} ou None, respondida_em}.
    # Guardado como JSON (mesmo padrão de curriculo.dados_editados) por ser um agregado que só
    # faz sentido lido/gravado por inteiro junto da simulação — não precisa de tabela própria.
    perguntas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="simulacoes_entrevista")
    vaga: Mapped["Vaga"] = relationship(back_populates="simulacoes_entrevista")
