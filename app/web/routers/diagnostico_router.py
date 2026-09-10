from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.diagnostico_service import DiagnosticoService

router = APIRouter(prefix="/diagnosticos", tags=["Diagnóstico Crítico"])


def get_diagnostico_service(db: Session = Depends(get_db)) -> DiagnosticoService:
    return DiagnosticoService(db)
