import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models import Curriculo, Usuario


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_criar_e_buscar_curriculo_por_id(db_session):
    repo = CurriculoRepository(db_session)
    id_usuario = uuid.uuid4()
    usuario = Usuario(
        id_usuario=id_usuario,
        nome="Teste",
        email="teste@example.com",
        senha_hash="hash123",
        perfil="candidato",
    )
    db_session.add(usuario)
    db_session.commit()

    curriculo = Curriculo(
        nome_arquivo="curriculo.pdf",
        status_processamento="concluido",
        id_usuario=id_usuario,
    )
    salvo = repo.criar(curriculo)

    assert salvo.id_curriculo is not None
    assert salvo.nome_arquivo == "curriculo.pdf"

    buscado = repo.buscar_por_id(salvo.id_curriculo)
    assert buscado is not None
    assert buscado.id_curriculo == salvo.id_curriculo
    assert buscado.nome_arquivo == "curriculo.pdf"


def test_listar_curriculos_por_usuario(db_session):
    repo = CurriculoRepository(db_session)
    id_usuario = uuid.uuid4()
    usuario = Usuario(
        id_usuario=id_usuario,
        nome="Teste 2",
        email="teste2@example.com",
        senha_hash="hash123",
        perfil="candidato",
    )
    db_session.add(usuario)
    db_session.commit()

    c1 = Curriculo(
        nome_arquivo="curriculo1.pdf",
        status_processamento="concluido",
        id_usuario=id_usuario,
        data_upload=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    c2 = Curriculo(
        nome_arquivo="curriculo2.docx",
        status_processamento="concluido",
        id_usuario=id_usuario,
        data_upload=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    repo.criar(c1)
    repo.criar(c2)

    lista = repo.listar_por_usuario(id_usuario)
    assert len(lista) == 2
    assert lista[0].nome_arquivo == "curriculo2.docx"
    assert lista[1].nome_arquivo == "curriculo1.pdf"
