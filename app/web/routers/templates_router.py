import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.service.template_service import (
    CurriculoNaoEncontradoError,
    FormatoExportacaoInvalidoError,
    NenhumaAnaliseEncontradaError,
    TemplateNaoEncontradoError,
    TemplateService,
    VersaoExportacaoInvalidaError,
)
from app.web.dependencies import get_usuario_atual
from app.web.schemas_template import TemplateListResponse

router = APIRouter(prefix="/templates", tags=["Templates ATS"])


def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@router.get("", response_model=TemplateListResponse)
def listar_templates(
    usuario=Depends(get_usuario_atual),
    email: str | None = None,
    template_service: TemplateService = Depends(get_template_service),
) -> TemplateListResponse:
    try:
        templates = template_service.listar_templates(usuario.id_usuario)
    except NenhumaAnaliseEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conclua ao menos uma análise antes de escolher um template.",
        ) from erro

    return TemplateListResponse(templates=templates)


@router.get("/exportar")
def exportar_curriculo(
    id_curriculo: uuid.UUID,
    id_template: str,
    formato: str,
    usuario=Depends(get_usuario_atual),
    versao: str = "original",
    email: str | None = None,
    template_service: TemplateService = Depends(get_template_service),
) -> Response:
    try:
        conteudo, nome_arquivo, media_type = template_service.exportar_curriculo(
            id_usuario=usuario.id_usuario,
            id_curriculo=id_curriculo,
            id_template=id_template,
            formato=formato,
            versao=versao,
        )
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except TemplateNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template não encontrado.",
        ) from erro
    except FormatoExportacaoInvalidoError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de exportação inválido. Use 'pdf' ou 'docx'.",
        ) from erro
    except VersaoExportacaoInvalidaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Versão de exportação inválida. Use 'original' ou 'editada'.",
        ) from erro

    nome_arquivo_ascii = nome_arquivo.encode("ascii", "ignore").decode() or f"curriculo.{formato}"
    return Response(
        content=conteudo,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nome_arquivo_ascii}"; ' f"filename*=UTF-8''{quote(nome_arquivo)}"
            )
        },
    )
