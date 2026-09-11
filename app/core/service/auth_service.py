import uuid
from datetime import date, datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.persistencia.models import Usuario
from app.core.persistencia.usuario_repository import UsuarioRepository

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

    def cadastrar_usuario(self, nome: str, data_nascimento: date, email: str, senha: str) -> Usuario:
        email_normalizado = email.strip().lower()
        if self.usuario_repository.buscar_por_email(email_normalizado) is not None:
            raise EmailJaCadastradoError
        self._validar_senha(senha)
        usuario = Usuario(
            nome=nome.strip(),
            data_nascimento=data_nascimento,
            email=email_normalizado,
            senha_hash=pwd_context.hash(senha),
            perfil="candidato",
        )
        return self.usuario_repository.criar(usuario)

    def solicitar_exclusao(self, id_usuario: uuid.UUID) -> str:
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError
        usuario.exclusao_solicitada_em = datetime.now(timezone.utc)
        self.usuario_repository.atualizar(usuario)
        expira_em = datetime.now(timezone.utc) + timedelta(hours=PRAZO_EXCLUSAO_HORAS)
        payload = {"sub": str(id_usuario), "finalidade": FINALIDADE_EXCLUSAO_CONTA, "exp": expira_em}
        return jwt.encode(payload, self.settings.secret_key, algorithm="HS256")

    def confirmar_exclusao(self, id_usuario: uuid.UUID, token: str) -> None:
        try:
            payload = jwt.decode(token, self.settings.secret_key, algorithms=["HS256"])
            if payload.get("finalidade") != FINALIDADE_EXCLUSAO_CONTA:
                raise TokenExclusaoInvalidoError
            id_token = uuid.UUID(payload["sub"])
        except (JWTError, KeyError, ValueError) as erro:
            raise TokenExclusaoInvalidoError from erro
        if id_token != id_usuario:
            raise TokenExclusaoInvalidoError
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None or usuario.exclusao_solicitada_em is None:
            raise TokenExclusaoInvalidoError
        self.usuario_repository.excluir(usuario)

    def cancelar_exclusao(self, id_usuario: uuid.UUID) -> None:
        usuario = self.usuario_repository.buscar_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNaoEncontradoError
        usuario.exclusao_solicitada_em = None
        self.usuario_repository.atualizar(usuario)

    @staticmethod
    def _validar_senha(senha: str) -> None:
        regras = (
            (len(senha) >= 8, "A senha deve ter pelo menos 8 caracteres."),
            (any(caractere.isupper() for caractere in senha), "A senha deve conter uma letra maiúscula."),
            (any(caractere.islower() for caractere in senha), "A senha deve conter uma letra minúscula."),
            (any(caractere.isdigit() for caractere in senha), "A senha deve conter um número."),
        )
        for regra_atendida, mensagem in regras:
            if not regra_atendida:
                raise SenhaInvalidaError(mensagem)

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
        return jwt.encode(payload, self.settings.secret_key, algorithm="HS256")

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
