import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.chat_service import (
    ChatService,
    CurriculoNaoEncontradoError,
    CurriculoSemTextoError,
    PerguntaVaziaError,
)
from app.web.schemas_chat import ChatEnviarResponse, ChatHistoricoResponse, ChatMensagemRequest, MensagemChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


@router.get("/curriculos/{id_curriculo}/mensagens", response_model=ChatHistoricoResponse)
def listar_mensagens(
    id_curriculo: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatHistoricoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        mensagens = chat_service.listar_historico(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro

    return ChatHistoricoResponse(mensagens=[MensagemChatResponse.model_validate(m) for m in mensagens])


@router.post(
    "/curriculos/{id_curriculo}/mensagens",
    response_model=ChatEnviarResponse,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensagem(
    id_curriculo: uuid.UUID,
    payload: ChatMensagemRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatEnviarResponse:
    usuario = usuario_repository.buscar_por_email(payload.email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        mensagem_usuario, mensagem_assistente = chat_service.enviar_mensagem(
            usuario.id_usuario, id_curriculo, payload.pergunta
        )
    except PerguntaVaziaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Digite uma pergunta antes de enviar.",
        ) from erro
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except CurriculoSemTextoError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse currículo ainda não tem texto extraído para conversar sobre ele.",
        ) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    return ChatEnviarResponse(
        mensagem_usuario=MensagemChatResponse.model_validate(mensagem_usuario),
        mensagem_assistente=MensagemChatResponse.model_validate(mensagem_assistente),
    )
