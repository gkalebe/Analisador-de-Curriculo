from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.adapters.curriculo_parser.curriculo_parser import FormatoNaoSuportadoError
from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.analisador_service import AnalisadorService
from app.web.schemas_curriculo import CurriculoResponse

router = APIRouter(prefix="/analises", tags=["Análise de Currículo"])


def get_analisador_service(db: Session = Depends(get_db)) -> AnalisadorService:
    return AnalisadorService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


@router.post("/upload", response_model=CurriculoResponse, status_code=status.HTTP_201_CREATED)
async def upload_curriculo(
    email: str = Form(...),
    file: UploadFile = File(...),
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    nome_arquivo = file.filename or ""
    extensao = nome_arquivo.rsplit(".", 1)[-1] if "." in nome_arquivo else ""
    conteudo = await file.read()

    limite_mb = analisador_service.settings.max_upload_size_mb
    if len(conteudo) > limite_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O arquivo excede o limite de {limite_mb}MB.",
        )

    try:
        resultado = analisador_service.processar_upload_curriculo(
            conteudo, nome_arquivo, extensao, usuario.id_usuario
        )
    except FormatoNaoSuportadoError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Envie um arquivo PDF ou DOCX.",
        ) from erro

    return CurriculoResponse.model_validate(resultado)
