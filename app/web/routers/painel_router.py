from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.plano_service import PlanoService

router = APIRouter(prefix="/painel", tags=["Painel e Plano de Desenvolvimento"])


def get_plano_service(db: Session = Depends(get_db)) -> PlanoService:
    return PlanoService(db)
