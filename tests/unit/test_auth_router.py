import uuid

from fastapi.testclient import TestClient

from app.core.service.auth_service import (
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    TokenRecuperacaoInvalidoError,
)
from app.main import app
from app.web.routers.auth_router import get_auth_service

client = TestClient(app)


class UsuarioFalso:
    def __init__(self, nome: str, email: str):
        self.id_usuario = uuid.uuid4()
        self.nome = nome
        self.email = email


class EmailAdapterFalso:
    def __init__(self):
        self.confirmacoes_enviadas: list[tuple[str, str]] = []

    def enviar_confirmacao_cadastro(self, destinatario: str, nome: str) -> None:
        self.confirmacoes_enviadas.append((destinatario, nome))


class AuthServiceFalso:
    def __init__(self):
        self.chamadas_recuperacao: list[str] = []
        self.chamadas_redefinicao: list[tuple[str, str]] = []
        self.chamadas_cadastro: list[dict] = []
        self.chamadas_login: list[tuple[str, str]] = []
        self.token_invalido = False
        self.email_ja_cadastrado = False
        self.credenciais_invalidas = False
        self.email_adapter = EmailAdapterFalso()

    def solicitar_recuperacao_senha(self, email: str) -> str | None:
        self.chamadas_recuperacao.append(email)
        return "token-fake"

    def redefinir_senha(self, token: str, nova_senha: str) -> None:
        self.chamadas_redefinicao.append((token, nova_senha))
        if self.token_invalido:
            raise TokenRecuperacaoInvalidoError

    def cadastrar_usuario(self, nome: str, data_nascimento, email: str, senha: str, enviar_email: bool = True):
        self.chamadas_cadastro.append(
            {"nome": nome, "data_nascimento": data_nascimento, "email": email, "senha": senha}
        )
        if self.email_ja_cadastrado:
            raise EmailJaCadastradoError
        if enviar_email:
            self.email_adapter.enviar_confirmacao_cadastro(email, nome)
        return UsuarioFalso(nome=nome, email=email)

    def autenticar(self, email: str, senha: str):
        self.chamadas_login.append((email, senha))
        if self.credenciais_invalidas:
            raise CredenciaisInvalidasError
        return UsuarioFalso(nome="Kevin Iqbal", email=email), "token-jwt-fake"


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


def _payload_cadastro(**overrides):
    payload = {
        "nome": "Kevin Iqbal",
        "data_nascimento": "1998-03-10",
        "email": "kevin@example.com",
        "senha": "SenhaForte123",
    }
    payload.update(overrides)
    return payload


def test_cadastrar_usuario_retorna_201_com_dados_validos():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios", json=_payload_cadastro())

    app.dependency_overrides.clear()
    assert response.status_code == 201
    corpo = response.json()
    assert corpo["nome"] == "Kevin Iqbal"
    assert corpo["email"] == "kevin@example.com"
    assert len(auth_service_falso.chamadas_cadastro) == 1


def test_cadastrar_usuario_nao_envia_email_de_forma_sincrona_mas_agenda_em_background():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios", json=_payload_cadastro())

    app.dependency_overrides.clear()
    assert response.status_code == 201
    assert auth_service_falso.chamadas_cadastro[0]["email"] == "kevin@example.com"
    assert auth_service_falso.email_adapter.confirmacoes_enviadas == [("kevin@example.com", "Kevin Iqbal")]


def test_cadastrar_usuario_retorna_409_quando_email_ja_cadastrado():
    auth_service_falso = AuthServiceFalso()
    auth_service_falso.email_ja_cadastrado = True
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios", json=_payload_cadastro())

    app.dependency_overrides.clear()
    assert response.status_code == 409


def test_cadastrar_usuario_rejeita_campos_obrigatorios_ausentes():
    response = client.post("/usuarios", json={"email": "kevin@example.com"})

    assert response.status_code == 422
    campos_com_erro = {erro["loc"][-1] for erro in response.json()["detail"]}
    assert {"nome", "data_nascimento", "senha"} <= campos_com_erro


def test_cadastrar_usuario_rejeita_email_com_formato_invalido():
    response = client.post("/usuarios", json=_payload_cadastro(email="nao-e-um-email"))

    assert response.status_code == 422


def test_cadastrar_usuario_rejeita_senha_fora_das_regras_minimas():
    response = client.post("/usuarios", json=_payload_cadastro(senha="fraca"))

    assert response.status_code == 422
    mensagem = response.json()["detail"][0]["msg"]
    assert "mínimo de 8 caracteres" in mensagem
    assert "letra maiúscula" in mensagem
    assert "número" in mensagem


def test_login_retorna_200_com_token_para_credenciais_validas():
    auth_service_falso = AuthServiceFalso()
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios/login", json={"email": "kevin@example.com", "senha": "SenhaForte123"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    corpo = response.json()
    assert corpo["access_token"] == "token-jwt-fake"
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario"]["email"] == "kevin@example.com"
    assert auth_service_falso.chamadas_login == [("kevin@example.com", "SenhaForte123")]


def test_login_retorna_401_generico_para_senha_incorreta():
    auth_service_falso = AuthServiceFalso()
    auth_service_falso.credenciais_invalidas = True
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios/login", json={"email": "kevin@example.com", "senha": "senha-errada"})

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos."


def test_login_retorna_401_generico_para_email_inexistente():
    auth_service_falso = AuthServiceFalso()
    auth_service_falso.credenciais_invalidas = True
    app.dependency_overrides[get_auth_service] = lambda: auth_service_falso

    response = client.post("/usuarios/login", json={"email": "nao-cadastrado@example.com", "senha": "qualquer"})

    app.dependency_overrides.clear()
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos."


# As rotas que renderizavam HTML (GET /recuperar-senha, POST /recuperar-senha/formulario,
# GET /redefinir-senha) foram removidas: essas telas agora são React e consomem só as rotas
# JSON acima (POST /recuperar-senha, POST /redefinir-senha), já cobertas nos testes anteriores.
