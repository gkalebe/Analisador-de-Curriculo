from sqlalchemy.orm import Session

from app.core.persistencia.analise_repository import AnaliseRepository


class PlanoService:
    def __init__(self, db: Session):
        self.analise_repository = AnaliseRepository(db)
