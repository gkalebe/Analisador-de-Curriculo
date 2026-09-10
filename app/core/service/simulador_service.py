from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.core.persistencia.vaga_repository import VagaRepository


class SimuladorService:
    def __init__(self, db: Session):
        self.vaga_repository = VagaRepository(db)
        self.ai_service_adapter = AIServiceAdapter()
