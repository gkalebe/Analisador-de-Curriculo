import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.email_service import enviar_email_recuperacao_senha

FINALIDADE_RECUPERACAO_SENHA = "recuperacao_senha"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenRecuperacaoInvalidoError(Exception):
    pass


class UsuarioNaoEncontradoError(Exception):
    pass

FINALIDADE_RECUPERACAO_SENHA = "recuperacao_senha"
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


class AuthService:
    def __init__(self, db: Session):
        self.usuario_repository = UsuarioRepository(db)
        self.settings = get_settings()

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
        enviar_email_recuperacao_senha(usuario.email, token, self.settings)
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
