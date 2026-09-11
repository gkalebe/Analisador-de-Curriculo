import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.auth_service import (
    AuthService,
    EmailJaCadastradoError,
    SenhaInvalidaError,
    TokenExclusaoInvalidoError,
    TokenRecuperacaoInvalidoError,
    UsuarioNaoEncontradoError,
)
from app.web.schemas import (
    CadastrarUsuarioRequest,
    ConfirmarExclusaoRequest,
    MensagemResponse,
    RedefinirSenhaRequest,
    SolicitarExclusaoResponse,
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
        usuario = auth_service.cadastrar_usuario(payload.nome, payload.data_nascimento, payload.email, payload.senha)
    except EmailJaCadastradoError as erro:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.") from erro
    except SenhaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro
    return UsuarioResponse(id_usuario=str(usuario.id_usuario), mensagem="Conta criada. Confirme seu e-mail antes de entrar.")


@router.post("/{id_usuario}/solicitar-exclusao", response_model=SolicitarExclusaoResponse)
def solicitar_exclusao(
    id_usuario: uuid.UUID,
    auth_service: AuthService = Depends(get_auth_service),
) -> SolicitarExclusaoResponse:
    try:
        token = auth_service.solicitar_exclusao(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return SolicitarExclusaoResponse(
        token_confirmacao=token,
        mensagem="Solicitação registrada. Confirme a exclusão em até 48 horas.",
    )


@router.post("/{id_usuario}/confirmar-exclusao", response_model=MensagemResponse)
def confirmar_exclusao(
    id_usuario: uuid.UUID,
    payload: ConfirmarExclusaoRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.confirmar_exclusao(id_usuario, payload.token)
    except TokenExclusaoInvalidoError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de exclusão inválido ou expirado.") from erro
    return MensagemResponse(mensagem="Conta e dados excluídos permanentemente.")


@router.post("/{id_usuario}/cancelar-exclusao", response_model=MensagemResponse)
def cancelar_exclusao(
    id_usuario: uuid.UUID,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    try:
        auth_service.cancelar_exclusao(id_usuario)
    except UsuarioNaoEncontradoError as erro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.") from erro
    return MensagemResponse(mensagem="Solicitação de exclusão cancelada. A conta permanece ativa.")


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
