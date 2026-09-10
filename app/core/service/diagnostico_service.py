from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.core.persistencia.analise_repository import AnaliseRepository


class DiagnosticoService:
    def __init__(self, db: Session):
        self.analise_repository = AnaliseRepository(db)
        self.ai_service_adapter = AIServiceAdapter()
