import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.persistencia.models import Usuario
from app.core.service.auth_service import (
    AuthService,
    EmailJaCadastradoError,
    SenhaInvalidaError,
    TokenExclusaoInvalidoError,
    TokenRecuperacaoInvalidoError,
)


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[uuid.UUID, Usuario]):
        self.usuarios = usuarios
        self.atualizados: list[Usuario] = []
        self.criados: list[Usuario] = []
        self.excluidos: list[Usuario] = []

    def buscar_por_email(self, email: str) -> Usuario | None:
        return next((usuario for usuario in self.usuarios.values() if usuario.email == email), None)

    def buscar_por_id(self, id_usuario: uuid.UUID) -> Usuario | None:
        return self.usuarios.get(id_usuario)

    def atualizar(self, usuario: Usuario) -> Usuario:
        self.atualizados.append(usuario)
        return usuario

    def criar(self, usuario: Usuario) -> Usuario:
        usuario.id_usuario = usuario.id_usuario or uuid.uuid4()
        self.usuarios[usuario.id_usuario] = usuario
        self.criados.append(usuario)
        return usuario

    def excluir(self, usuario: Usuario) -> None:
        self.excluidos.append(usuario)
        self.usuarios.pop(usuario.id_usuario, None)


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


def test_cadastrar_usuario_cria_hash_e_normaliza_email():
    service, _ = _criar_service_com_usuario()
    service.usuario_repository.usuarios.pop(next(iter(service.usuario_repository.usuarios)))

    usuario = service.cadastrar_usuario("Novo Usuário", date(1990, 1, 1), " NOVO@EXAMPLE.COM ", "Senha-forte1")

    assert usuario.email == "novo@example.com"
    assert usuario.senha_hash != "Senha-forte1"
    assert service.usuario_repository.criados == [usuario]


def test_cadastrar_usuario_recusa_email_duplicado():
    service, usuario = _criar_service_com_usuario()

    with pytest.raises(EmailJaCadastradoError):
        service.cadastrar_usuario("Outro", date(1990, 1, 1), usuario.email, "Senha-forte1")


def test_cadastrar_usuario_informa_regra_de_senha_violada():
    service, _ = _criar_service_com_usuario()

    with pytest.raises(SenhaInvalidaError, match="maiúscula"):
        service.cadastrar_usuario("Novo", date(1990, 1, 1), "novo@example.com", "senha-fraca1")


def test_exclusao_em_duas_etapas_solicita_e_depois_remove_usuario():
    service, usuario = _criar_service_com_usuario()

    token = service.solicitar_exclusao(usuario.id_usuario)
    assert usuario.exclusao_solicitada_em is not None
    assert service.usuario_repository.excluidos == []

    service.confirmar_exclusao(usuario.id_usuario, token)

    assert service.usuario_repository.excluidos == [usuario]
    assert service.usuario_repository.buscar_por_id(usuario.id_usuario) is None


def test_exclusao_recusa_token_de_outra_finalidade():
    service, usuario = _criar_service_com_usuario()
    token = service.solicitar_recuperacao_senha(usuario.email)

    with pytest.raises(TokenExclusaoInvalidoError):
        service.confirmar_exclusao(usuario.id_usuario, token)


def test_cancelar_exclusao_mantem_conta_ativa():
    service, usuario = _criar_service_com_usuario()
    service.solicitar_exclusao(usuario.id_usuario)

    service.cancelar_exclusao(usuario.id_usuario)

    assert service.usuario_repository.buscar_por_id(usuario.id_usuario) is usuario
    assert usuario.exclusao_solicitada_em is None
