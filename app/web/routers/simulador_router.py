import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import (
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
    IARespostaInvalidaError,
)
from app.core.database import get_db
from app.core.service.simulador_service import (
    RespostasInvalidasError,
    SimulacaoJaAvaliadaError,
    SimulacaoNaoEncontradaError,
    SimuladorService,
    VagaNaoEncontradaError,
)
from app.web.dependencies import get_usuario_atual
from app.web.paginacao import ParametrosPaginacao, get_paginacao, montar_meta
from app.web.schemas_simulador import (
    AvaliacaoSimulacaoRequest,
    SimulacaoIniciarRequest,
    SimulacaoItemResponse,
    SimulacaoListResponse,
    SimulacaoResponse,
)

router = APIRouter(prefix="/simulador", tags=["Simulador de Entrevistas"])


def get_simulador_service(db: Session = Depends(get_db)) -> SimuladorService:
    return SimuladorService(db)


@router.post("/iniciar", response_model=SimulacaoResponse, status_code=status.HTTP_201_CREATED)
def iniciar_simulacao(
    payload: SimulacaoIniciarRequest,
    usuario=Depends(get_usuario_atual),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
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
    except IARespostaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(erro)) from erro

    return SimulacaoResponse.model_validate(simulacao)


@router.get("", response_model=SimulacaoListResponse)
def listar_simulacoes(
    usuario=Depends(get_usuario_atual),
    email: str | None = None,
    paginacao: ParametrosPaginacao = Depends(get_paginacao),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoListResponse:
    simulacoes = simulador_service.listar_simulacoes_usuario(
        usuario.id_usuario, limit=paginacao.limit, offset=paginacao.offset
    )
    return SimulacaoListResponse(
        simulacoes=[SimulacaoItemResponse.model_validate(s) for s in simulacoes],
        paginacao=montar_meta(
            len(simulacoes), paginacao, lambda: simulador_service.contar_simulacoes_usuario(usuario.id_usuario)
        ),
    )


@router.get("/{id_simulacao}", response_model=SimulacaoResponse)
def obter_simulacao(
    id_simulacao: uuid.UUID,
    usuario=Depends(get_usuario_atual),
    email: str | None = None,
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    try:
        simulacao = simulador_service.obter_simulacao(usuario.id_usuario, id_simulacao)
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro

    return SimulacaoResponse.model_validate(simulacao)


@router.delete("/{id_simulacao}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_simulacao(
    id_simulacao: uuid.UUID,
    usuario=Depends(get_usuario_atual),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> Response:
    try:
        simulador_service.excluir_simulacao(usuario.id_usuario, id_simulacao)
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id_simulacao}/repetir", response_model=SimulacaoResponse, status_code=status.HTTP_201_CREATED)
def repetir_simulacao(
    id_simulacao: uuid.UUID,
    usuario=Depends(get_usuario_atual),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    """Nova simulação (novas perguntas) para a mesma vaga; consome 1 entrevista da cota e não
    altera a simulação original."""
    try:
        simulacao = simulador_service.repetir_simulacao(usuario.id_usuario, id_simulacao)
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro
    except VagaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A vaga desta simulação não está mais disponível.",
        ) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IARespostaInvalidaError as erro:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(erro)) from erro

    return SimulacaoResponse.model_validate(simulacao)


@router.post("/{id_simulacao}/avaliar", response_model=SimulacaoResponse)
def avaliar_simulacao(
    id_simulacao: uuid.UUID,
    payload: AvaliacaoSimulacaoRequest,
    usuario=Depends(get_usuario_atual),
    simulador_service: SimuladorService = Depends(get_simulador_service),
) -> SimulacaoResponse:
    """Avalia todas as respostas de uma vez (uma chamada de IA, uma reserva de cota)."""
    respostas = {str(item.id_pergunta): item.resposta for item in payload.respostas}
    try:
        simulacao = simulador_service.avaliar_simulacao(
            id_usuario=usuario.id_usuario,
            id_simulacao=id_simulacao,
            respostas=respostas,
        )
    except SimulacaoNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulação de entrevista não encontrada para este usuário.",
        ) from erro
    except SimulacaoJaAvaliadaError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta simulação já foi avaliada. Use \"Repetir entrevista\" para treinar de novo.",
        ) from erro
    except RespostasInvalidasError as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IARespostaInvalidaError as erro:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{erro} Sua cota não foi consumida; envie as respostas novamente.",
        ) from erro

    return SimulacaoResponse.model_validate(simulacao)
