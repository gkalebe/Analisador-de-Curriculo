import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models import Curriculo, Usuario


@pytest.fixture(scope="module")
def engine():
    engine = create_engine(get_settings().database_url)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(engine) -> Session:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def usuario(db: Session) -> Usuario:
    usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        data_nascimento=date(1995, 5, 20),
        email=f"{uuid.uuid4()}@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


def test_criar_persiste_curriculo_com_texto_extraido(db: Session, usuario: Usuario):
    repositorio = CurriculoRepository(db)
    curriculo = Curriculo(
        nome_arquivo="curriculo.pdf",
        id_usuario=usuario.id_usuario,
        status_processamento="processando",
        texto_extraido="texto extraído do currículo",
    )

    curriculo_criado = repositorio.criar(curriculo)

    assert curriculo_criado.id_curriculo is not None
    encontrado = repositorio.buscar_por_id(curriculo_criado.id_curriculo)
    assert encontrado is not None
    assert encontrado.texto_extraido == "texto extraído do currículo"


def test_buscar_por_id_retorna_none_quando_nao_existe(db: Session):
    repositorio = CurriculoRepository(db)

    assert repositorio.buscar_por_id(uuid.uuid4()) is None


def test_listar_por_usuario_retorna_apenas_curriculos_do_usuario(db: Session, usuario: Usuario):
    repositorio = CurriculoRepository(db)
    repositorio.criar(
        Curriculo(nome_arquivo="a.pdf", id_usuario=usuario.id_usuario, status_processamento="processando")
    )
    repositorio.criar(
        Curriculo(nome_arquivo="b.pdf", id_usuario=usuario.id_usuario, status_processamento="processando")
    )

    outro_usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Outro Usuário",
        data_nascimento=date(1990, 1, 15),
        email=f"{uuid.uuid4()}@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    db.add(outro_usuario)
    db.commit()
    repositorio.criar(
        Curriculo(nome_arquivo="c.pdf", id_usuario=outro_usuario.id_usuario, status_processamento="processando")
    )

    curriculos_do_usuario = repositorio.listar_por_usuario(usuario.id_usuario)

    assert len(curriculos_do_usuario) == 2
    assert all(c.id_usuario == usuario.id_usuario for c in curriculos_do_usuario)
