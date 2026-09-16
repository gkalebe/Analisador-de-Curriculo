import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.service.auth_service import (
    AuthService,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    TokenRecuperacaoInvalidoError,
    TokenExclusaoInvalidoError,
    UsuarioNaoEncontradoError,
    FINALIDADE_ACESSO,
    PRAZO_EXCLUSAO_HORAS,
)
from app.web.schemas_auth import (
    CadastrarUsuarioRequest,
    LoginRequest,
    LoginResponse,
    MensagemResponse,
    RedefinirSenhaRequest,
    SolicitarRecuperacaoSenhaRequest,
    StatusExclusaoResponse,
    UsuarioResponse,
)

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])

MENSAGEM_RECUPERACAO_SENHA = (
    "Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação de senha."
)
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_usuario_autenticado(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> uuid.UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")

    try:
        payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])
        if payload.get("finalidade") != FINALIDADE_ACESSO:
            raise JWTError
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.") from erro


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(
    payload: CadastrarUsuarioRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
) -> UsuarioResponse:
    try:
        usuario = auth_service.cadastrar_usuario(
            nome=payload.nome,
            data_nascimento=payload.data_nascimento,
            email=payload.email,
            senha=payload.senha,
            enviar_email=False,
        )
    except EmailJaCadastradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        ) from erro
    background_tasks.add_task(
        auth_service.email_adapter.enviar_confirmacao_cadastro,
        usuario.email,
        usuario.nome,
    )
    return UsuarioResponse.model_validate(usuario)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    try:
        usuario, token = auth_service.autenticar(payload.email, payload.senha)
    except CredenciaisInvalidasError as erro:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos.",
        ) from erro
    return LoginResponse(access_token=token, usuario=UsuarioResponse.model_validate(usuario))


@router.get("/exclusao", response_model=StatusExclusaoResponse)
def status_exclusao_conta(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> StatusExclusaoResponse:
    usuario = auth_service.usuario_repository.buscar_por_id(id_usuario)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    solicitada_em = usuario.exclusao_solicitada_em
    if solicitada_em is None:
        return StatusExclusaoResponse(solicitada=False)
    if solicitada_em.tzinfo is None:
        solicitada_em = solicitada_em.replace(tzinfo=timezone.utc)
    if solicitada_em + timedelta(hours=PRAZO_EXCLUSAO_HORAS) < datetime.now(timezone.utc):
        auth_service.cancelar_exclusao_conta(id_usuario)
        return StatusExclusaoResponse(solicitada=False)
    return StatusExclusaoResponse(
        solicitada=True,
        expira_em=solicitada_em + timedelta(hours=PRAZO_EXCLUSAO_HORAS),
    )


@router.post("/exclusao", response_model=MensagemResponse, status_code=status.HTTP_202_ACCEPTED)
def solicitar_exclusao_conta(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.solicitar_exclusao_conta(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return MensagemResponse(mensagem="Solicitação registrada. Confirme a exclusão em até 48 horas.")


@router.post("/exclusao/cancelar", response_model=MensagemResponse)
def cancelar_exclusao_conta(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.cancelar_exclusao_conta(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return MensagemResponse(mensagem="Solicitação cancelada. Sua conta continua ativa.")


@router.post("/exclusao/confirmar", response_model=MensagemResponse)
def confirmar_exclusao_conta(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.confirmar_exclusao_conta(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    except TokenExclusaoInvalidoError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A solicitação de exclusão é inválida ou ultrapassou o prazo de 48 horas.",
        ) from erro
    return MensagemResponse(mensagem="Conta e dados excluídos permanentemente.")


@router.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_202_ACCEPTED)
def solicitar_recuperacao_senha(
    payload: SolicitarRecuperacaoSenhaRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    auth_service.solicitar_recuperacao_senha(payload.email)
    return MensagemResponse(mensagem=MENSAGEM_RECUPERACAO_SENHA)


@router.post("/redefinir-senha", response_model=MensagemResponse)
def redefinir_senha(
    payload: RedefinirSenhaRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.redefinir_senha(payload.token, payload.nova_senha)
    except (TokenRecuperacaoInvalidoError, UsuarioNaoEncontradoError) as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de recuperação inválido ou expirado.",
        ) from erro
    return MensagemResponse(mensagem="Senha redefinida com sucesso.")
