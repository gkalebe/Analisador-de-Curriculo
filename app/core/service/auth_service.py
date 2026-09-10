from sqlalchemy.orm import Session

from app.core.persistencia.usuario_repository import UsuarioRepository


class AuthService:
    def __init__(self, db: Session):
        self.usuario_repository = UsuarioRepository(db)
