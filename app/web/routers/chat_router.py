import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.chat_service import (
    ChatService,
    ContextoChatObrigatorioError,
    CurriculoNaoEncontradoError,
    CurriculoSemTextoError,
    PerguntaVaziaError,
    VagaNaoEncontradaError,
)
from app.web.schemas_chat import ChatEnviarResponse, ChatHistoricoResponse, ChatMensagemRequest, MensagemChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


@router.get("/mensagens", response_model=ChatHistoricoResponse)
def listar_mensagens_geral(
    email: str,
    id_curriculo: uuid.UUID | None = None,
    id_vaga: uuid.UUID | None = None,
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
        mensagens = chat_service.listar_historico(
            usuario.id_usuario, id_curriculo=id_curriculo, id_vaga=id_vaga
        )
    except ContextoChatObrigatorioError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except VagaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada para este usuário.",
        ) from erro

    return ChatHistoricoResponse(mensagens=[MensagemChatResponse.model_validate(m) for m in mensagens])


@router.post("/mensagens", response_model=ChatEnviarResponse, status_code=status.HTTP_201_CREATED)
def enviar_mensagem_geral(
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
            id_usuario=usuario.id_usuario,
            pergunta=payload.pergunta,
            id_curriculo=payload.id_curriculo,
            id_vaga=payload.id_vaga,
        )
    except PerguntaVaziaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Digite uma pergunta antes de enviar.",
        ) from erro
    except ContextoChatObrigatorioError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro),
        ) from erro
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except VagaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada para este usuário.",
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


# --- Rotas retrocompatíveis para currículo ---


@router.get("/curriculos/{id_curriculo}/mensagens", response_model=ChatHistoricoResponse)
def listar_mensagens(
    id_curriculo: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatHistoricoResponse:
    return listar_mensagens_geral(
        email=email,
        id_curriculo=id_curriculo,
        id_vaga=None,
        usuario_repository=usuario_repository,
        chat_service=chat_service,
    )


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
    payload_com_curriculo = ChatMensagemRequest(
        email=payload.email,
        pergunta=payload.pergunta,
        id_curriculo=id_curriculo,
        id_vaga=payload.id_vaga,
    )
    return enviar_mensagem_geral(
        payload=payload_com_curriculo,
        usuario_repository=usuario_repository,
        chat_service=chat_service,
    )


# --- Rotas específicas para vaga ---


@router.get("/vagas/{id_vaga}/mensagens", response_model=ChatHistoricoResponse)
def listar_mensagens_vaga(
    id_vaga: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatHistoricoResponse:
    return listar_mensagens_geral(
        email=email,
        id_curriculo=None,
        id_vaga=id_vaga,
        usuario_repository=usuario_repository,
        chat_service=chat_service,
    )


@router.post(
    "/vagas/{id_vaga}/mensagens",
    response_model=ChatEnviarResponse,
    status_code=status.HTTP_201_CREATED,
)
def enviar_mensagem_vaga(
    id_vaga: uuid.UUID,
    payload: ChatMensagemRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatEnviarResponse:
    payload_com_vaga = ChatMensagemRequest(
        email=payload.email,
        pergunta=payload.pergunta,
        id_curriculo=payload.id_curriculo,
        id_vaga=id_vaga,
    )
    return enviar_mensagem_geral(
        payload=payload_com_vaga,
        usuario_repository=usuario_repository,
        chat_service=chat_service,
    )
