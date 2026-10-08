from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.plano_service import PlanoService
from app.web.dependencies import get_usuario_atual
from app.web.schemas_painel import PainelHistoricoResponse

router = APIRouter(prefix="/painel", tags=["Painel e Plano de Desenvolvimento"])


def get_plano_service(db: Session = Depends(get_db)) -> PlanoService:
    return PlanoService(db)


@router.get("/historico", response_model=PainelHistoricoResponse)
def obter_historico(
    usuario=Depends(get_usuario_atual),
    email: str | None = None,
    plano_service: PlanoService = Depends(get_plano_service),
) -> PainelHistoricoResponse:
    dados = plano_service.obter_historico_e_lacunas(usuario.id_usuario)
    return PainelHistoricoResponse(**dados)
