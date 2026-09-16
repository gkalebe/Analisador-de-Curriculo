from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.plano_service import PlanoService
from app.web.schemas_painel import PainelHistoricoResponse

router = APIRouter(prefix="/painel", tags=["Painel e Plano de Desenvolvimento"])


def get_plano_service(db: Session = Depends(get_db)) -> PlanoService:
    return PlanoService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


@router.get("/historico", response_model=PainelHistoricoResponse)
def obter_historico(
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    plano_service: PlanoService = Depends(get_plano_service),
) -> PainelHistoricoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    dados = plano_service.obter_historico_e_lacunas(usuario.id_usuario)
    return PainelHistoricoResponse(**dados)
