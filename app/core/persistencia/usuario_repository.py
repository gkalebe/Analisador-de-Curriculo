import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.persistencia.models import Usuario


class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def criar(self, usuario: Usuario) -> Usuario:
        self.db.add(usuario)
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def buscar_por_id(self, id_usuario: uuid.UUID) -> Usuario | None:
        return self.db.get(Usuario, id_usuario)

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()

    def atualizar(self, usuario: Usuario) -> Usuario:
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def excluir(self, usuario: Usuario) -> None:
        self.db.delete(usuario)
        self.db.commit()
