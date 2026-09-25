from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.analisador_service import (
    AnalisadorService,
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
    VagaDuplicadaError,
)
from app.core.service.importador_vaga_service import ImportacaoVagaError, importar_vaga
from app.web.schemas_vaga import VagaCreateRequest, VagaImportRequest, VagaListResponse, VagaResponse

router = APIRouter(prefix="/api/vagas", tags=["Vagas"])


def get_analisador_service(db: Session = Depends(get_db)) -> AnalisadorService:
    return AnalisadorService(db)


def get_usuario_repository(db: Session = Depends(get_db)) -> UsuarioRepository:
    return UsuarioRepository(db)


@router.get("", response_model=VagaListResponse)
def listar_vagas(
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> VagaListResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    vagas = analisador_service.listar_vagas_usuario(usuario.id_usuario)
    return VagaListResponse(vagas=[VagaResponse.model_validate(vaga) for vaga in vagas])


@router.post("", response_model=VagaResponse, status_code=status.HTTP_201_CREATED)
def criar_vaga(
    payload: VagaCreateRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> VagaResponse:
    usuario = usuario_repository.buscar_por_email(payload.email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        vaga = analisador_service.cadastrar_vaga(
            id_usuario=usuario.id_usuario,
            descricao=payload.descricao,
            titulo=payload.titulo,
            requisitos=payload.requisitos,
            area=payload.area,
        )
    except DescricaoVagaObrigatoriaError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A descrição da vaga é obrigatória.",
        ) from erro
    except DescricaoVagaMuitoLongaError as erro:
        limite = analisador_service.settings.max_vaga_description_chars
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A descrição da vaga deve ter no máximo {limite} caracteres.",
        ) from erro
    except VagaDuplicadaError as erro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já cadastrou uma vaga com essa mesma descrição.",
        ) from erro

    return VagaResponse.model_validate(vaga)


@router.post("/importar", response_model=VagaResponse, status_code=status.HTTP_201_CREATED)
def importar_vaga_por_url(
    payload: VagaImportRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> VagaResponse:
    usuario = usuario_repository.buscar_por_email(payload.email)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Não encontramos um usuário cadastrado com esse e-mail.")

    try:
        dados = importar_vaga(payload.url, analisador_service.settings.max_vaga_description_chars)
        vaga = analisador_service.cadastrar_vaga(id_usuario=usuario.id_usuario, **{chave: dados[chave] for chave in ("descricao", "titulo", "requisitos", "area")})
    except ImportacaoVagaError as erro:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(erro)) from erro
    except VagaDuplicadaError as erro:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Você já cadastrou uma vaga com essa mesma descrição.") from erro
    except DescricaoVagaMuitoLongaError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A descrição importada excede o limite permitido.") from erro

    return VagaResponse.model_validate(vaga)
