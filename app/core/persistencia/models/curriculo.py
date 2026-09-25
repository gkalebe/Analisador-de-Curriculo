import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .analise import Analise
    from .candidato import Candidato
    from .mensagem_chat import MensagemChat
    from .usuario import Usuario


class Curriculo(Base):
    __tablename__ = "curriculo"

    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_curriculo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_upload: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_processamento: Mapped[str] = mapped_column(String(50), nullable=False, default="pendente")
    texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    conteudo_arquivo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    dados_editados: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    editado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Cache da extração por IA de `texto_extraido` (nome/resumo/formação/experiência/habilidades),
    # preenchido na primeira vez que a extração funciona. Sem isso, cada preview/exportação do
    # currículo original chamava a IA de novo — caro e frágil (quota/indisponibilidade quebrava a
    # exportação, que não deveria depender de IA). `dados_editados`, quando existir, sempre tem
    # prioridade sobre este campo (é uma edição intencional do usuário).
    dados_extraidos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="curriculos")
    candidato: Mapped["Candidato | None"] = relationship(
        back_populates="curriculo", uselist=False, cascade="all, delete-orphan"
    )
    analises: Mapped[list["Analise"]] = relationship(back_populates="curriculo", cascade="all, delete-orphan")
    mensagens_chat: Mapped[list["MensagemChat"]] = relationship(
        back_populates="curriculo", cascade="all, delete-orphan"
    )
