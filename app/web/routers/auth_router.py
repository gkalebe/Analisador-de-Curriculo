from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.auth_service import AuthService

router = APIRouter(prefix="/usuarios", tags=["Autenticação"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)
