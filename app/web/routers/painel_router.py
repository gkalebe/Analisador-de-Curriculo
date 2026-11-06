from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.plano_service import PlanoService
from app.web.dependencies import get_usuario_atual
from app.web.paginacao import PaginacaoMeta, ParametrosPaginacao, get_paginacao
from app.web.schemas_painel import PainelHistoricoResponse, PlanoDesenvolvimentoResponse

router = APIRouter(prefix="/painel", tags=["Painel e Plano de Desenvolvimento"])


def get_plano_service(db: Session = Depends(get_db)) -> PlanoService:
    return PlanoService(db)


@router.get("/historico", response_model=PainelHistoricoResponse)
def obter_historico(
    usuario=Depends(get_usuario_atual),
    email: str | None = None,
    paginacao: ParametrosPaginacao = Depends(get_paginacao),
    plano_service: PlanoService = Depends(get_plano_service),
) -> PainelHistoricoResponse:
    # A paginação recorta só `historico`; `lacunas_recorrentes` segue agregando todas as análises.
    dados = plano_service.obter_historico_e_lacunas(
        usuario.id_usuario, limit=paginacao.limit, offset=paginacao.offset
    )
    return PainelHistoricoResponse(
        historico=dados["historico"],
        lacunas_recorrentes=dados["lacunas_recorrentes"],
        paginacao=PaginacaoMeta(total=dados["total_historico"], limit=paginacao.limit, offset=paginacao.offset),
    )


@router.get("/plano-desenvolvimento", response_model=PlanoDesenvolvimentoResponse)
def obter_plano_desenvolvimento(
    usuario=Depends(get_usuario_atual),
    plano_service: PlanoService = Depends(get_plano_service),
) -> PlanoDesenvolvimentoResponse:
    """US-015: trilhas e certificações para os requisitos não atendidos nas vagas analisadas."""
    return PlanoDesenvolvimentoResponse(**plano_service.obter_plano_desenvolvimento(usuario.id_usuario))
