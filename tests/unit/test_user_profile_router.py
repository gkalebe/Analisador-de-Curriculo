import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.web.routers.auth_router import get_auth_service, get_usuario_autenticado

client = TestClient(app)


class AuthServiceFalso:
    def __init__(self):
        self.usuario = type(
            "UsuarioFalso",
            (),
            {
                "id_usuario": uuid.uuid4(),
                "nome": "Nome atual",
                "email": "pessoa@example.com",
                "notificacoes_por_email": True,
            },
        )()

    def obter_perfil(self, id_usuario):
        assert id_usuario == self.usuario.id_usuario
        return self.usuario

    def atualizar_perfil(self, id_usuario, nome, notificacoes_por_email):
        assert id_usuario == self.usuario.id_usuario
        self.usuario.nome = nome
        self.usuario.notificacoes_por_email = notificacoes_por_email
        return self.usuario


@pytest.fixture
def perfil_autenticado():
    auth_service = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_usuario_autenticado] = lambda: auth_service.usuario.id_usuario
    yield auth_service
    app.dependency_overrides.clear()


def test_obter_perfil_retorna_dados_persistidos(perfil_autenticado):
    response = client.get("/usuarios/me")

    assert response.status_code == 200
    assert response.json() == {
        "id_usuario": str(perfil_autenticado.usuario.id_usuario),
        "nome": "Nome atual",
        "email": "pessoa@example.com",
        "notificacoes_por_email": True,
    }


def test_atualizar_perfil_altera_nome_e_preferencia(perfil_autenticado):
    response = client.patch(
        "/usuarios/me",
        json={"nome": "Nome atualizado", "notificacoes_por_email": False},
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Nome atualizado"
    assert response.json()["notificacoes_por_email"] is False
    assert perfil_autenticado.usuario.nome == "Nome atualizado"
    assert perfil_autenticado.usuario.notificacoes_por_email is False


def test_atualizar_perfil_rejeita_nome_em_branco(perfil_autenticado):
    response = client.patch(
        "/usuarios/me",
        json={"nome": "   ", "notificacoes_por_email": True},
    )

    assert response.status_code == 422


def test_obter_perfil_exige_autenticacao():
    response = client.get("/usuarios/me")

    assert response.status_code == 401
