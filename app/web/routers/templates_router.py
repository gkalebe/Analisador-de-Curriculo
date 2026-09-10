from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["Templates ATS"])


def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    return TemplateService(db)
