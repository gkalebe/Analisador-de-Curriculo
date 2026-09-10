from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.auth_service import (
    AuthService,
    TokenRecuperacaoInvalidoError,
    UsuarioNaoEncontradoError,
)
from app.web.schemas import MensagemResponse, RedefinirSenhaRequest, SolicitarRecuperacaoSenhaRequest

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


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
