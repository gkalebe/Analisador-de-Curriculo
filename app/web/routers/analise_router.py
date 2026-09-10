from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.core.service.analisador_service import AnalisadorService

router = APIRouter(prefix="/analises", tags=["Análise de Currículo"])
templates = Jinja2Templates(directory="app/web/templates")


def get_analisador_service(db: Session = Depends(get_db)) -> AnalisadorService:
    return AnalisadorService(db)


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@router.post("/upload")
async def processar_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    service: AnalisadorService = Depends(get_analisador_service)
):
    conteudo = await file.read()
    extensao = file.filename.split(".")[-1]
    
    # Usuário mock provisório para desenvolvimento
    from app.core.persistencia.models import Usuario
    user = db.query(Usuario).first()
    if not user:
        user = Usuario(nome="Test User", email="test@test.com", senha_hash="fakehash")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    resultado = service.processar_upload_curriculo(conteudo, file.filename, extensao, user.id_usuario)
    return resultado
