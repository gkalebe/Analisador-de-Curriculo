from sqlalchemy.orm import Session

from app.core.persistencia.curriculo_repository import CurriculoRepository


class TemplateService:
    def __init__(self, db: Session):
        self.curriculo_repository = CurriculoRepository(db)
