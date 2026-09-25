import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.simulador_service import (
    PerguntaNaoEncontradaError,
    RespostaVaziaError,
    SimulacaoNaoEncontradaError,
    SimuladorService,
    VagaNaoEncontradaError,
)
from app.web.schemas_simulador import (
    RespostaSimulacaoRequest,
    SimulacaoIniciarRequest,
    SimulacaoItemResponse,
    SimulacaoListResponse,
    SimulacaoResponse,
)

router = APIRouter(prefix="/simulador", tags=["Simulador de Entrevistas"])


def get_simulador_service(db: Session = Depends(get_db)) -> SimuladorService:
    return SimuladorService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def _buscar_usuario_ou_404(email: str, usuario_repository: UsuarioRepository):
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )
    return usuario


@router.post("/iniciar", response_model=SimulacaoResponse, status_code=status.HTTP_201_CREATED)
def iniciar_simulacao(
    payload: SimulacaoIniciarRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    usuario = _buscar_usuario_ou_404(payload.email, usuario_repository)

    try:
        simulacao = simulador_service.iniciar_simulacao(usuario.id_usuario, payload.id_vaga)
    except VagaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecione uma vaga válida para iniciar a simulação de entrevista.",
        ) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    return SimulacaoResponse.model_validate(simulacao)


@router.get("", response_model=SimulacaoListResponse)
def listar_simulacoes(
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoListResponse:
    usuario = _buscar_usuario_ou_404(email, usuario_repository)

    simulacoes = simulador_service.listar_simulacoes_usuario(usuario.id_usuario)
    return SimulacaoListResponse(
        simulacoes=[
            SimulacaoItemResponse(
                id_simulacao=s.id_simulacao,
                id_vaga=s.id_vaga,
                data_criacao=s.data_criacao,
                total_perguntas=len(s.perguntas or []),
                total_respondidas=len([p for p in (s.perguntas or []) if p.get("resposta")]),
            )
            for s in simulacoes
        ]
    )


@router.get("/{id_simulacao}", response_model=SimulacaoResponse)
def obter_simulacao(
    id_simulacao: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    usuario = _buscar_usuario_ou_404(email, usuario_repository)

    try:
        simulacao = simulador_service.obter_simulacao(usuario.id_usuario, id_simulacao)
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro

    return SimulacaoResponse.model_validate(simulacao)


@router.post("/{id_simulacao}/perguntas/{id_pergunta}/resposta", response_model=SimulacaoResponse)
def responder_pergunta(
    id_simulacao: uuid.UUID,
    id_pergunta: uuid.UUID,
    payload: RespostaSimulacaoRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    usuario = _buscar_usuario_ou_404(payload.email, usuario_repository)

    try:
        simulacao = simulador_service.responder_pergunta(
            id_usuario=usuario.id_usuario,
            id_simulacao=id_simulacao,
            id_pergunta=id_pergunta,
            resposta=payload.resposta,
        )
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro
    except PerguntaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pergunta não encontrada nesta simulação.",
        ) from erro
    except RespostaVaziaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    return SimulacaoResponse.model_validate(simulacao)
