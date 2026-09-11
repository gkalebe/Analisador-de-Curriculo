import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.persistencia.models import Usuario
from app.core.service.auth_service import (
    AuthService,
    TokenRecuperacaoInvalidoError,
)


@pytest.fixture(autouse=True)
def _sem_envio_real_de_email():
    with patch("app.core.service.auth_service.enviar_email_recuperacao_senha") as mock_enviar:
        yield mock_enviar


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[uuid.UUID, Usuario]):
        self.usuarios = usuarios
        self.atualizados: list[Usuario] = []

    def buscar_por_email(self, email: str) -> Usuario | None:
        return next((usuario for usuario in self.usuarios.values() if usuario.email == email), None)

    def buscar_por_id(self, id_usuario: uuid.UUID) -> Usuario | None:
        return self.usuarios.get(id_usuario)

    def atualizar(self, usuario: Usuario) -> Usuario:
        self.atualizados.append(usuario)
        return usuario


def _criar_service_com_usuario() -> tuple[AuthService, Usuario]:
    usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash-antigo",
        perfil="candidato",
    )
    service = AuthService(db=None)
    service.usuario_repository = UsuarioRepositorioFalso({usuario.id_usuario: usuario})
    return service, usuario


def test_solicitar_recuperacao_senha_gera_token_para_usuario_existente():
    service, usuario = _criar_service_com_usuario()

    token = service.solicitar_recuperacao_senha(usuario.email)

    assert token is not None
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    assert payload["sub"] == str(usuario.id_usuario)
    assert payload["finalidade"] == "recuperacao_senha"


def test_solicitar_recuperacao_senha_retorna_none_para_email_inexistente():
    service, _ = _criar_service_com_usuario()

    assert service.solicitar_recuperacao_senha("nao-cadastrado@example.com") is None


def test_solicitar_recuperacao_senha_envia_email(_sem_envio_real_de_email):
    service, usuario = _criar_service_com_usuario()

    token = service.solicitar_recuperacao_senha(usuario.email)

    _sem_envio_real_de_email.assert_called_once_with(usuario.email, token, service.settings)


def test_solicitar_recuperacao_senha_nao_envia_email_para_email_inexistente(_sem_envio_real_de_email):
    service, _ = _criar_service_com_usuario()

    service.solicitar_recuperacao_senha("nao-cadastrado@example.com")

    _sem_envio_real_de_email.assert_not_called()


def test_redefinir_senha_atualiza_hash_com_token_valido():
    service, usuario = _criar_service_com_usuario()
    token = service.solicitar_recuperacao_senha(usuario.email)

    service.redefinir_senha(token, "nova-senha-123")

    assert usuario.senha_hash != "hash-antigo"


def test_redefinir_senha_recusa_token_invalido():
    service, _ = _criar_service_com_usuario()

    with pytest.raises(TokenRecuperacaoInvalidoError):
        service.redefinir_senha("token-invalido", "nova-senha-123")


def test_redefinir_senha_recusa_token_com_finalidade_errada():
    service, usuario = _criar_service_com_usuario()
    settings = get_settings()
    payload = {
        "sub": str(usuario.id_usuario),
        "finalidade": "outra-coisa",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    with pytest.raises(TokenRecuperacaoInvalidoError):
        service.redefinir_senha(token, "nova-senha-123")


def test_redefinir_senha_recusa_token_expirado():
    service, usuario = _criar_service_com_usuario()
    settings = get_settings()
    payload = {
        "sub": str(usuario.id_usuario),
        "finalidade": "recuperacao_senha",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

    with pytest.raises(TokenRecuperacaoInvalidoError):
        service.redefinir_senha(token, "nova-senha-123")
