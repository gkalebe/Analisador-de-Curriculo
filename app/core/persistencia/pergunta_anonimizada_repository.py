from sqlalchemy.orm import Session

from app.core.persistencia.models.pergunta_anonimizada import PerguntaAnonimizada


class PerguntaAnonimizadaRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar_lote(self, perguntas: list[str]) -> list[PerguntaAnonimizada]:
        objetos = [PerguntaAnonimizada(pergunta=p.strip()) for p in perguntas if p and p.strip()]
        if not objetos:
            return []
        self.db.add_all(objetos)
        self.db.commit()
        return objetos
