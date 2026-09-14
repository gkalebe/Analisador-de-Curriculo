from fastapi.testclient import TestClient

from app.core.service.auth_service import TokenRecuperacaoInvalidoError
from app.main import app
from app.web.routers.auth_router import get_auth_service

client = TestClient(app)


class AuthServiceFalso:
    def __init__(self):
        self.chamadas_recuperacao: list[str] = []
        self.chamadas_redefinicao: list[tuple[str, str]] = []
        self.token_invalido = False

    def solicitar_recuperacao_senha(self, email: str) -> str | None:
        self.chamadas_recuperacao.append(email)
        return "token-fake"

    def redefinir_senha(self, token: str, nova_senha: str) -> None:
        self.chamadas_redefinicao.append((token, nova_senha))
        if self.token_invalido:
            raise TokenRecuperacaoInvalidoError


def test_solicitar_recuperacao_senha_retorna_202_e_mensagem_generica():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios/recuperar-senha", json={"email": "gabriel@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 202
    assert "instruções" in response.json()["mensagem"]
    assert auth_service_falso.chamadas_recuperacao == ["gabriel@example.com"]


def test_solicitar_recuperacao_senha_rejeita_email_invalido():
    response = client.post("/usuarios/recuperar-senha", json={"email": "nao-e-um-email"})

    assert response.status_code == 422


def test_redefinir_senha_retorna_200_com_token_valido():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post(
        "/usuarios/redefinir-senha",
        json={"token": "token-valido", "nova_senha": "senha-nova-123"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["mensagem"] == "Senha redefinida com sucesso."


def test_redefinir_senha_retorna_400_com_token_invalido():
    auth_service_falso = AuthServiceFalso()
    auth_service_falso.token_invalido = True
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post(
        "/usuarios/redefinir-senha",
        json={"token": "token-invalido", "nova_senha": "senha-nova-123"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_redefinir_senha_rejeita_senha_curta():
    response = client.post(
        "/usuarios/redefinir-senha",
        json={"token": "qualquer", "nova_senha": "123"},
    )

    assert response.status_code == 422


def test_formulario_recuperar_senha_renderiza_pagina():
    response = client.get("/usuarios/recuperar-senha")

    assert response.status_code == 200
    assert "Recuperar senha" in response.text
    assert "Enviar link de recuperação" in response.text


def test_solicitar_recuperacao_senha_formulario_mostra_mensagem_generica():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post(
        "/usuarios/recuperar-senha/formulario",
        data={"email": "gabriel@example.com"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "Se o e-mail informado estiver cadastrado" in response.text
    assert "Reenviar link" in response.text
    assert auth_service_falso.chamadas_recuperacao == ["gabriel@example.com"]


def test_solicitar_recuperacao_senha_formulario_nao_revela_email_inexistente():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post(
        "/usuarios/recuperar-senha/formulario",
        data={"email": "nao-cadastrado@example.com"},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "Se o e-mail informado estiver cadastrado" in response.text
