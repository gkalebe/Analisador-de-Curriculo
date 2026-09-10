import uuid

from sqlalchemy.orm import Session

from app.core.persistencia.models import Usuario


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, usuario: Usuario) -> Usuario:
        raise NotImplementedError

    def buscar_por_id(self, id_usuario: uuid.UUID) -> Usuario | None:
        raise NotImplementedError

    def buscar_por_email(self, email: str) -> Usuario | None:
        raise NotImplementedError

    def atualizar(self, usuario: Usuario) -> Usuario:
        raise NotImplementedError

    def excluir(self, usuario: Usuario) -> None:
        raise NotImplementedError
