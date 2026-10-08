import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.service.auth_service import (
    PRAZO_EXCLUSAO_HORAS,
    AuthService,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    TokenExclusaoInvalidoError,
    TokenRecuperacaoInvalidoError,
    UsuarioNaoEncontradoError,
)
from app.web.dependencies import get_usuario_autenticado
from app.web.schemas_auth import (
    AtualizarPerfilUsuarioRequest,
    CadastrarUsuarioRequest,
    LoginRequest,
    LoginResponse,
    MensagemResponse,
    PerfilUsuarioResponse,
    RedefinirSenhaRequest,
    SolicitarRecuperacaoSenhaRequest,
    StatusExclusaoResponse,
    UsuarioResponse,
)

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])

MENSAGEM_RECUPERACAO_SENHA = (
    "Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação de senha."
)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def cadastrar_usuario(
    request: Request,
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
@limiter.limit("5/minute")
def login(
    request: Request,
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


@router.get("/me", response_model=PerfilUsuarioResponse)
def obter_perfil_usuario(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> PerfilUsuarioResponse:
    try:
        usuario = auth_service.obter_perfil(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return PerfilUsuarioResponse.model_validate(usuario)


@router.patch("/me", response_model=PerfilUsuarioResponse)
def atualizar_perfil_usuario(
    payload: AtualizarPerfilUsuarioRequest,
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    auth_service: AuthService = Depends(get_auth_service),
) -> PerfilUsuarioResponse:
    try:
        usuario = auth_service.atualizar_perfil(
            id_usuario,
            nome=payload.nome,
            notificacoes_por_email=payload.notificacoes_por_email,
        )
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return PerfilUsuarioResponse.model_validate(usuario)


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
@limiter.limit("5/hour")
def solicitar_recuperacao_senha(
    request: Request,
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
