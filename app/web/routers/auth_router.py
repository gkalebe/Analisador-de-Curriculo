from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.auth_service import (
    AuthService,
    CredenciaisInvalidasError,
    EmailJaCadastradoError,
    TokenRecuperacaoInvalidoError,
    UsuarioNaoEncontradoError,
)
from app.web.schemas import (
    CadastrarUsuarioRequest,
    LoginRequest,
    LoginResponse,
    MensagemResponse,
    RedefinirSenhaRequest,
    SolicitarRecuperacaoSenhaRequest,
    UsuarioResponse,
)

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_usuario(
    payload: CadastrarUsuarioRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UsuarioResponse:
    try:
        usuario = auth_service.cadastrar_usuario(
            nome=payload.nome,
            data_nascimento=payload.data_nascimento,
            email=payload.email,
            senha=payload.senha,
        )
    except EmailJaCadastradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está cadastrado.",
        ) from erro
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


@router.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_202_ACCEPTED)
def solicitar_recuperacao_senha(
    payload: SolicitarRecuperacaoSenhaRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    auth_service.solicitar_recuperacao_senha(payload.email)
    return MensagemResponse(
        mensagem="Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação de senha."
    )


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
