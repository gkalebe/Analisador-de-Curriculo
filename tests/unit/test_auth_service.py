import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.persistencia.models.usuario import Usuario
from app.core.service.auth_service import (
    AuthService,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    TokenRecuperacaoInvalidoError,
    TokenExclusaoInvalidoError,
    pwd_context,
)


@pytest.fixture(autouse=True)
def _sem_envio_real_de_email():
    with patch("app.core.service.auth_service.enviar_email_recuperacao_senha") as mock_enviar:
        yield mock_enviar


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


class EmailAdapterFalso:
    def __init__(self):
        self.confirmacoes_enviadas: list[tuple[str, str]] = []

    def enviar_confirmacao_cadastro(self, destinatario: str, nome: str) -> None:
        self.confirmacoes_enviadas.append((destinatario, nome))


def _criar_service_com_usuario() -> tuple[AuthService, Usuario]:
    usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        data_nascimento=date(1995, 5, 20),
        email="gabriel@example.com",
        senha_hash="hash-antigo",
        perfil="candidato",
    )
    service = AuthService(db=None, email_adapter=EmailAdapterFalso())
    service.usuario_repository = UsuarioRepositorioFalso({usuario.id_usuario: usuario})
    return service, usuario


def _criar_service_com_usuario_autenticavel(senha: str = "SenhaCorreta123") -> tuple[AuthService, Usuario]:
    usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        data_nascimento=date(1995, 5, 20),
        email="gabriel@example.com",
        senha_hash=pwd_context.hash(senha),
        perfil="candidato",
    )
    service = AuthService(db=None, email_adapter=EmailAdapterFalso())
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


def test_solicitar_recuperacao_senha_retorna_token_mesmo_com_falha_no_envio(_sem_envio_real_de_email):
    _sem_envio_real_de_email.side_effect = OSError("smtp indisponivel")
    service, usuario = _criar_service_com_usuario()

    token = service.solicitar_recuperacao_senha(usuario.email)

    assert token is not None


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


def test_autenticar_retorna_usuario_e_token_com_credenciais_validas():
    service, usuario = _criar_service_com_usuario_autenticavel("SenhaCorreta123")

    usuario_autenticado, token = service.autenticar(usuario.email, "SenhaCorreta123")

    assert usuario_autenticado.id_usuario == usuario.id_usuario
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    assert payload["sub"] == str(usuario.id_usuario)
    assert payload["finalidade"] == "acesso"


def test_autenticar_recusa_senha_incorreta_com_erro_generico():
    service, usuario = _criar_service_com_usuario_autenticavel("SenhaCorreta123")

    with pytest.raises(CredenciaisInvalidasError):
        service.autenticar(usuario.email, "senha-errada")


def test_autenticar_recusa_email_inexistente_com_mesmo_erro_generico():
    service, _ = _criar_service_com_usuario_autenticavel("SenhaCorreta123")

    with pytest.raises(CredenciaisInvalidasError):
        service.autenticar("nao-cadastrado@example.com", "qualquer-senha")


def test_cadastrar_usuario_persiste_com_senha_hasheada_e_envia_confirmacao():
    service, _ = _criar_service_com_usuario()

    usuario = service.cadastrar_usuario(
        nome="Kevin Iqbal",
        data_nascimento=date(1998, 3, 10),
        email="kevin@example.com",
        senha="SenhaForte123",
    )

    assert usuario.id_usuario is not None
    assert usuario.senha_hash != "SenhaForte123"
    assert pwd_context.verify("SenhaForte123", usuario.senha_hash)
    assert service.usuario_repository.criados == [usuario]
    assert service.email_adapter.confirmacoes_enviadas == [("kevin@example.com", "Kevin Iqbal")]


def test_cadastrar_usuario_recusa_email_ja_cadastrado():
    service, usuario_existente = _criar_service_com_usuario()

    with pytest.raises(EmailJaCadastradoError):
        service.cadastrar_usuario(
            nome="Outro Nome",
            data_nascimento=date(2000, 1, 1),
            email=usuario_existente.email,
            senha="SenhaForte123",
        )

    assert service.email_adapter.confirmacoes_enviadas == []


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


def test_solicitar_exclusao_registra_primeira_etapa_com_prazo():
    service, usuario = _criar_service_com_usuario()

    service.solicitar_exclusao_conta(usuario.id_usuario)

    assert usuario.exclusao_solicitada_em is not None
    assert service.usuario_repository.atualizados == [usuario]


def test_cancelar_exclusao_antes_da_segunda_etapa_mantem_conta_ativa():
    service, usuario = _criar_service_com_usuario()
    service.solicitar_exclusao_conta(usuario.id_usuario)

    service.cancelar_exclusao_conta(usuario.id_usuario)

    assert usuario.exclusao_solicitada_em is None
    assert service.usuario_repository.buscar_por_id(usuario.id_usuario) is usuario
    assert service.usuario_repository.excluidos == []


def test_confirmar_exclusao_remove_conta_na_segunda_etapa():
    service, usuario = _criar_service_com_usuario()
    service.solicitar_exclusao_conta(usuario.id_usuario)

    service.confirmar_exclusao_conta(usuario.id_usuario)

    assert service.usuario_repository.excluidos == [usuario]
    assert service.usuario_repository.buscar_por_id(usuario.id_usuario) is None


def test_confirmar_exclusao_recusa_solicitacao_expirada():
    service, usuario = _criar_service_com_usuario()
    usuario.exclusao_solicitada_em = datetime.now(timezone.utc) - timedelta(hours=49)

    with pytest.raises(TokenExclusaoInvalidoError):
        service.confirmar_exclusao_conta(usuario.id_usuario)

    assert usuario.exclusao_solicitada_em is None
    assert service.usuario_repository.excluidos == []
