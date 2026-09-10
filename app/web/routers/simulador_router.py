from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.simulador_service import SimuladorService

router = APIRouter(prefix="/simulador", tags=["Simulador de Entrevistas"])


def get_simulador_service(db: Session = Depends(get_db)) -> SimuladorService:
    return SimuladorService(db)
