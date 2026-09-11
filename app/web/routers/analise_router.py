from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.analisador_service import (
    AnalisadorService,
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
)

router = APIRouter(prefix="/analises", tags=["Análise de Currículo"])
templates = Jinja2Templates(directory="app/web/templates")


def get_analisador_service(db: Session = Depends(get_db)) -> AnalisadorService:
    return AnalisadorService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


def _renderizar_formulario(
    request: Request,
    usuario_repository: UsuarioRepository,
    analisador_service: AnalisadorService,
    email: str,
    erro: str | None,
    sucesso: str | None,
    status_code: int = status.HTTP_200_OK,
):
    vagas_salvas = []
    if email and erro is None:
        usuario = usuario_repository.buscar_por_email(email)
        if usuario is not None:
            vagas_salvas = analisador_service.listar_vagas_usuario(usuario.id_usuario)

    return templates.TemplateResponse(
        request=request,
        name="vagas_nova.html",
        context={
            "email": email,
            "erro": erro,
            "sucesso": sucesso,
            "vagas_salvas": vagas_salvas,
            "limite_descricao": analisador_service.settings.max_vaga_description_chars,
        },
        status_code=status_code,
    )


@router.get("/vagas/nova")
def formulario_nova_vaga(
    request: Request,
    email: str = "",
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
):
    erro = None
    if email and usuario_repository.buscar_por_email(email) is None:
        erro = "Não encontramos um usuário cadastrado com esse e-mail."

    return _renderizar_formulario(request, usuario_repository, analisador_service, email, erro, sucesso=None)


@router.post("/vagas")
def criar_vaga(
    request: Request,
    email: str = Form(...),
    titulo: str = Form(""),
    descricao: str = Form(...),
    requisitos: str = Form(""),
    area: str = Form(""),
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
):
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        return _renderizar_formulario(
            request,
            usuario_repository,
            analisador_service,
            email,
            erro="Não encontramos um usuário cadastrado com esse e-mail.",
            sucesso=None,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analisador_service.cadastrar_vaga(
            id_usuario=usuario.id_usuario,
            descricao=descricao,
            titulo=titulo,
            requisitos=requisitos,
            area=area,
        )
    except DescricaoVagaObrigatoriaError:
        return _renderizar_formulario(
            request,
            usuario_repository,
            analisador_service,
            email,
            erro="A descrição da vaga é obrigatória.",
            sucesso=None,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except DescricaoVagaMuitoLongaError:
        limite = analisador_service.settings.max_vaga_description_chars
        return _renderizar_formulario(
            request,
            usuario_repository,
            analisador_service,
            email,
            erro=f"A descrição da vaga deve ter no máximo {limite} caracteres.",
            sucesso=None,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return _renderizar_formulario(
        request,
        usuario_repository,
        analisador_service,
        email,
        erro=None,
        sucesso="Vaga salva com sucesso.",
    )
