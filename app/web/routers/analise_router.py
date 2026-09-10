from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.analisador_service import AnalisadorService

router = APIRouter(prefix="/analises", tags=["Análise de Currículo"])


def get_analisador_service(db: Session = Depends(get_db)) -> AnalisadorService:
    return AnalisadorService(db)
