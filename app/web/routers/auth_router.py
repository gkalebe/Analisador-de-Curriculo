from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.auth_service import (
    AuthService,
    TokenRecuperacaoInvalidoError,
    UsuarioNaoEncontradoError,
)
from app.web.schemas import MensagemResponse, RedefinirSenhaRequest, SolicitarRecuperacaoSenhaRequest

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])
templates = Jinja2Templates(directory="app/web/templates")

MENSAGEM_RECUPERACAO_SENHA = (
    "Se o e-mail informado estiver cadastrado, enviaremos instruções de recuperação de senha."
)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/recuperar-senha", response_model=MensagemResponse, status_code=status.HTTP_202_ACCEPTED)
def solicitar_recuperacao_senha(
    payload: SolicitarRecuperacaoSenhaRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> MensagemResponse:
    auth_service.solicitar_recuperacao_senha(payload.email)
    return MensagemResponse(mensagem=MENSAGEM_RECUPERACAO_SENHA)


@router.get("/recuperar-senha")
def formulario_recuperar_senha(request: Request, email: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="recuperar_senha.html",
        context={"email": email, "enviado": False, "mensagem": MENSAGEM_RECUPERACAO_SENHA},
    )


@router.post("/recuperar-senha/formulario")
def solicitar_recuperacao_senha_formulario(
    request: Request,
    email: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    auth_service.solicitar_recuperacao_senha(email)
    return templates.TemplateResponse(
        request=request,
        name="recuperar_senha.html",
        context={"email": email, "enviado": True, "mensagem": MENSAGEM_RECUPERACAO_SENHA},
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
