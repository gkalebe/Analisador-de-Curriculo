import uuid
from datetime import date

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.persistencia.models.usuario import Usuario
from app.core.persistencia.models.vaga import Vaga
from app.core.persistencia.vaga_repository import VagaRepository


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


def test_criar_persiste_vaga_e_gera_id(db: Session, usuario: Usuario):
    repositorio = VagaRepository(db)
    vaga = Vaga(
        titulo="Desenvolvedor Backend",
        descricao="Vaga para atuar com Python e FastAPI.",
        requisitos="Python, SQL",
        area="Tecnologia",
        id_usuario=usuario.id_usuario,
    )

    vaga_criada = repositorio.criar(vaga)

    assert vaga_criada.id_vaga is not None
    assert repositorio.buscar_por_id(vaga_criada.id_vaga) is not None


def test_buscar_por_id_retorna_none_quando_nao_existe(db: Session):
    repositorio = VagaRepository(db)

    assert repositorio.buscar_por_id(uuid.uuid4()) is None


def test_listar_por_usuario_retorna_apenas_vagas_do_usuario(db: Session, usuario: Usuario):
    repositorio = VagaRepository(db)
    repositorio.criar(
        Vaga(descricao="Vaga 1 do usuário", id_usuario=usuario.id_usuario)
    )
    repositorio.criar(
        Vaga(descricao="Vaga 2 do usuário", id_usuario=usuario.id_usuario)
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
    repositorio.criar(Vaga(descricao="Vaga de outro usuário", id_usuario=outro_usuario.id_usuario))

    vagas_do_usuario = repositorio.listar_por_usuario(usuario.id_usuario)

    assert len(vagas_do_usuario) == 2
    assert all(vaga.id_usuario == usuario.id_usuario for vaga in vagas_do_usuario)


def test_listar_por_usuario_pagina_com_limit_offset_e_conta_total(db: Session, usuario: Usuario):
    repositorio = VagaRepository(db)
    for i in range(5):
        repositorio.criar(Vaga(descricao=f"Vaga {i}", id_usuario=usuario.id_usuario))

    todas = repositorio.listar_por_usuario(usuario.id_usuario)
    primeira_pagina = repositorio.listar_por_usuario(usuario.id_usuario, limit=2, offset=0)
    segunda_pagina = repositorio.listar_por_usuario(usuario.id_usuario, limit=2, offset=2)
    alem_do_fim = repositorio.listar_por_usuario(usuario.id_usuario, limit=2, offset=10)

    assert len(todas) == 5
    assert [v.id_vaga for v in primeira_pagina + segunda_pagina] == [v.id_vaga for v in todas[:4]]
    assert alem_do_fim == []
    assert repositorio.contar_por_usuario(usuario.id_usuario) == 5
