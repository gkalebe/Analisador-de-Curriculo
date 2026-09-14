import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.persistencia.models import Usuario, Vaga
from app.core.service.analisador_service import (
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
)
from app.main import app
from app.web.routers.vagas_router import get_analisador_service, get_usuario_repository

client = TestClient(app)


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[str, Usuario]):
        self.usuarios = usuarios

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)


class AnalisadorServiceFalso:
    def __init__(self):
        self.settings = type("Settings", (), {"max_vaga_description_chars": 5000})()
        self.vagas_criadas: list[Vaga] = []
        self.deve_recusar_vazia = False
        self.deve_recusar_longa = False

    def cadastrar_vaga(self, id_usuario, descricao, titulo="", requisitos="", area=""):
        if self.deve_recusar_vazia:
            raise DescricaoVagaObrigatoriaError
        if self.deve_recusar_longa:
            raise DescricaoVagaMuitoLongaError
        vaga = Vaga(
            id_vaga=uuid.uuid4(),
            titulo=titulo or None,
            descricao=descricao,
            requisitos=requisitos or None,
            area=area or None,
            id_usuario=id_usuario,
            data_criacao=datetime.now(),
        )
        self.vagas_criadas.append(vaga)
        return vaga

    def listar_vagas_usuario(self, id_usuario):
        return [vaga for vaga in self.vagas_criadas if vaga.id_usuario == id_usuario]


def _usuario() -> Usuario:
    return Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_listar_vagas_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.get("/api/vagas", params={"email": "nao-cadastrado@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_listar_vagas_com_email_conhecido_retorna_lista():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.cadastrar_vaga(usuario.id_usuario, "Vaga para dev Python pleno.")
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.get("/api/vagas", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    corpo = response.json()
    assert len(corpo["vagas"]) == 1
    assert corpo["vagas"][0]["descricao"] == "Vaga para dev Python pleno."


def test_criar_vaga_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/api/vagas",
        json={
            "email": usuario.email,
            "titulo": "Dev Python",
            "descricao": "Vaga para desenvolvedor Python pleno.",
            "requisitos": "Python, SQL",
            "area": "Tecnologia",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    corpo = response.json()
    assert corpo["titulo"] == "Dev Python"
    assert corpo["descricao"] == "Vaga para desenvolvedor Python pleno."


def test_criar_vaga_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/api/vagas",
        json={"email": "nao-cadastrado@example.com", "descricao": "Vaga qualquer."},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_criar_vaga_com_descricao_vazia_retorna_422():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/api/vagas",
        json={"email": usuario.email, "descricao": "   "},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 422


def test_criar_vaga_com_descricao_longa_retorna_400():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_longa = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/api/vagas",
        json={"email": usuario.email, "descricao": "a" * 6000},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "no máximo" in response.json()["detail"]
