import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(50), nullable=False, default="candidato")
    data_cadastro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exclusao_solicitada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    curriculos: Mapped[list["Curriculo"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    vagas: Mapped[list["Vaga"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    analises: Mapped[list["Analise"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Curriculo(Base):
    __tablename__ = "curriculo"

    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_arquivo: Mapped[str] = mapped_column(String(255), nullable=False)
    data_upload: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status_processamento: Mapped[str] = mapped_column(String(50), nullable=False, default="pendente")
    texto_extraido: Mapped[str | None] = mapped_column(Text, nullable=True)
    conteudo_arquivo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="curriculos")
    candidato: Mapped["Candidato | None"] = relationship(back_populates="curriculo", uselist=False, cascade="all, delete-orphan")
    analises: Mapped[list["Analise"]] = relationship(back_populates="curriculo", cascade="all, delete-orphan")


class Candidato(Base):
    __tablename__ = "candidato"

    id_candidato: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str] = mapped_column(String(30), nullable=True)
    formacao: Mapped[str] = mapped_column(Text, nullable=True)
    experiencia_profissional: Mapped[str] = mapped_column(Text, nullable=True)
    habilidades: Mapped[str] = mapped_column(Text, nullable=True)
    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("curriculo.id_curriculo"), nullable=False, unique=True)

    curriculo: Mapped["Curriculo"] = relationship(back_populates="candidato")


class Vaga(Base):
    __tablename__ = "vaga"

    id_vaga: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    requisitos: Mapped[str] = mapped_column(Text, nullable=True)
    area: Mapped[str] = mapped_column(String(100), nullable=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="vagas")
    analises: Mapped[list["Analise"]] = relationship(back_populates="vaga", cascade="all, delete-orphan")


class Analise(Base):
    __tablename__ = "analise"

    id_analise: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_curriculo: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("curriculo.id_curriculo"), nullable=False)
    id_vaga: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vaga.id_vaga"), nullable=False)
    id_usuario: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuario.id_usuario"), nullable=False)
    pontuacao: Mapped[float] = mapped_column(Float, nullable=True)
    observacoes: Mapped[str] = mapped_column(Text, nullable=True)
    data_analise: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    curriculo: Mapped["Curriculo"] = relationship(back_populates="analises")
    vaga: Mapped["Vaga"] = relationship(back_populates="analises")
    usuario: Mapped["Usuario"] = relationship(back_populates="analises")
