import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.persistencia.models.usuario import Usuario
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.auth_service import FINALIDADE_ACESSO

bearer_scheme = HTTPBearer(auto_error=False)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def get_usuario_autenticado(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> uuid.UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária.")

    try:
        payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])
        if payload.get("finalidade") != FINALIDADE_ACESSO:
            raise JWTError
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise JWTError
        return uuid.UUID(subject)
    except (JWTError, KeyError, ValueError) as erro:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.") from erro


def get_usuario_atual(
    id_usuario: uuid.UUID = Depends(get_usuario_autenticado),
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
) -> Usuario:
    usuario = usuario_repository.buscar_por_id(id_usuario)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")
    return usuario
