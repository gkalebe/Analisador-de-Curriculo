import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.adapters.email.email_adapter import EmailAdapter
from app.core.config import get_settings
from app.core.persistencia.models.usuario import Usuario
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.email_service import enviar_email_recuperacao_senha

logger = logging.getLogger(__name__)

FINALIDADE_RECUPERACAO_SENHA = "recuperacao_senha"
FINALIDADE_ACESSO = "acesso"
FINALIDADE_EXCLUSAO_CONTA = "exclusao_conta"
PRAZO_EXCLUSAO_HORAS = 48

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenRecuperacaoInvalidoError(Exception):
    pass


class UsuarioNaoEncontradoError(Exception):
    pass


class EmailJaCadastradoError(Exception):
    pass


class SenhaInvalidaError(Exception):
    pass


class TokenExclusaoInvalidoError(Exception):
    pass


class CredenciaisInvalidasError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session, email_adapter: EmailAdapter | None = None):
        self.usuario_repository = UsuarioRepository(db)
        self.settings = get_settings()
        self.email_adapter = email_adapter or EmailAdapter()

    def cadastrar_usuario(
        self, nome: str, data_nascimento: date, email: str, senha: str, enviar_email: bool = True
    ) -> Usuario:
        if self.usuario_repository.buscar_por_email(email) is not None:
            raise EmailJaCadastradoError

        usuario = Usuario(
            nome=nome,
            data_nascimento=data_nascimento,
            email=email,
            senha_hash=pwd_context.hash(senha),
        )
        usuario = self.usuario_repository.criar(usuario)
        if enviar_email:
            self.email_adapter.enviar_confirmacao_cadastro(usuario.email, usuario.nome)
        return usuario

    def autenticar(self, email: str, senha: str) -> tuple[Usuario, str]:
        usuario = self.usuario_repository.buscar_por_email(email)
        if usuario is None or not pwd_context.verify(senha, usuario.senha_hash):
            raise CredenciaisInvalidasError

        expira_em = datetime.now(timezone.utc) + timedelta(minutes=self.settings.access_token_expire_minutes)
        payload = {
            "sub": str(usuario.id_usuario),
            "finalidade": FINALIDADE_ACESSO,
            "exp": expira_em,
        }
        token = jwt.encode(payload, self.settings.secret_key, algorithm="HS256")
        return usuario, token

    def solicitar_exclusao_conta(self, id_usuario: uuid.UUID) -> Usuario:
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError

        if usuario.exclusao_solicitada_em is None:
            usuario.exclusao_solicitada_em = datetime.now(timezone.utc)
            self.usuario_repository.atualizar(usuario)
        return usuario

    def cancelar_exclusao_conta(self, id_usuario: uuid.UUID) -> Usuario:
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError

        usuario.exclusao_solicitada_em = None
        self.usuario_repository.atualizar(usuario)
        return usuario

    def confirmar_exclusao_conta(self, id_usuario: uuid.UUID) -> None:
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError
        if usuario.exclusao_solicitada_em is None:
            raise TokenExclusaoInvalidoError

        solicitada_em = usuario.exclusao_solicitada_em
        if solicitada_em.tzinfo is None:
            solicitada_em = solicitada_em.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - solicitada_em > timedelta(hours=PRAZO_EXCLUSAO_HORAS):
            usuario.exclusao_solicitada_em = None
            self.usuario_repository.atualizar(usuario)
            raise TokenExclusaoInvalidoError

        self.usuario_repository.excluir(usuario)

    def solicitar_recuperacao_senha(self, email: str) -> str | None:
        usuario = self.usuario_repository.buscar_por_email(email)
        if usuario is None:
            return None
        expira_em = datetime.now(timezone.utc) + timedelta(minutes=self.settings.password_reset_expire_minutes)
        payload = {
            "sub": str(usuario.id_usuario),
            "finalidade": FINALIDADE_RECUPERACAO_SENHA,
            "exp": expira_em,
        }
        token = jwt.encode(payload, self.settings.secret_key, algorithm="HS256")
        try:
            enviar_email_recuperacao_senha(usuario.email, token, self.settings)
        except OSError:
            logger.exception("Falha ao enviar e-mail de recuperacao de senha para %s", usuario.email)
        return token

    def redefinir_senha(self, token: str, nova_senha: str) -> None:
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=["HS256"])
        except JWTError as erro:
            raise TokenRecuperacaoInvalidoError from erro

        if payload.get("finalidade") != FINALIDADE_RECUPERACAO_SENHA:
            raise TokenRecuperacaoInvalidoError

        try:
            id_usuario = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as erro:
            raise TokenRecuperacaoInvalidoError from erro

        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError

        usuario.senha_hash = pwd_context.hash(nova_senha)
        self.usuario_repository.atualizar(usuario)
