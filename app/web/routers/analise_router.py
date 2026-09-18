import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.adapters.curriculo_parser.curriculo_parser import CurriculoParser, FormatoNaoSuportadoError
from app.core.database import get_db
from app.core.persistencia.usuario_repository import UsuarioRepository
from app.core.service.analisador_service import (
    AnalisadorService,
    CurriculoArquivoNaoEncontradoError,
    CurriculoNaoEncontradoError,
    VagaNaoEncontradaError,
)
from app.web.schemas_analise import AnaliseListResponse, AnaliseResponse
from app.web.schemas_curriculo import (
    CurriculoDetalhesResponse,
    CurriculoEdicaoEstruturadaRequest,
    CurriculoEdicaoResponse,
    CurriculoEdicaoTextoLivreRequest,
    CurriculoItemResponse,
    CurriculoListResponse,
    CurriculoResponse,
)

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
    extensao = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""
    if extensao not in CurriculoParser.FORMATOS_SUPORTADOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Envie um arquivo PDF ou DOCX.",
        )
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


@router.post("", response_model=AnaliseResponse, status_code=status.HTTP_201_CREATED)
async def criar_analise(
    email: str = Form(...),
    id_vaga: uuid.UUID = Form(...),
    id_curriculo: uuid.UUID | None = Form(None),
    file: UploadFile | None = File(None),
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> AnaliseResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    if id_curriculo is not None:
        try:
            analise = analisador_service.analisar_curriculo_salvo_para_vaga(
                id_usuario=usuario.id_usuario,
                id_vaga=id_vaga,
                id_curriculo=id_curriculo,
            )
        except VagaNaoEncontradaError as erro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vaga não encontrada para este usuário.",
            ) from erro
        except CurriculoNaoEncontradoError as erro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Currículo não encontrado para este usuário.",
            ) from erro
        except CurriculoArquivoNaoEncontradoError as erro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo físico ou texto do currículo não encontrado.",
            ) from erro
        except IAConfiguracaoAusenteError as erro:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(erro),
            ) from erro
        except IAIndisponivelError as erro:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(erro),
            ) from erro
        except NotImplementedError as erro:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Essa funcionalidade ainda não foi implementada pelo time.",
            ) from erro

        return AnaliseResponse.model_validate(analise)

    if file is None or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo de currículo ou selecione um currículo já cadastrado.",
        )

    nome_arquivo = file.filename or ""
    extensao = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""
    if extensao not in CurriculoParser.FORMATOS_SUPORTADOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Envie um arquivo PDF ou DOCX.",
        )
    conteudo = await file.read()

    limite_mb = analisador_service.settings.max_upload_size_mb
    if len(conteudo) > limite_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"O arquivo excede o limite de {limite_mb}MB.",
        )

    try:
        analise = analisador_service.analisar_curriculo_para_vaga(
            id_usuario=usuario.id_usuario,
            id_vaga=id_vaga,
            conteudo=conteudo,
            nome_arquivo=nome_arquivo,
            extensao=extensao,
        )
    except VagaNaoEncontradaError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada para este usuário.",
        ) from erro
    except FormatoNaoSuportadoError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato não suportado. Envie um arquivo PDF ou DOCX.",
        ) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(erro),
        ) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(erro),
        ) from erro
    except NotImplementedError as erro:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Essa funcionalidade ainda não foi implementada pelo time.",
        ) from erro

    return AnaliseResponse.model_validate(analise)


@router.get("", response_model=AnaliseListResponse)
def listar_analises(
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> AnaliseListResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        analises = analisador_service.listar_analises_usuario(usuario.id_usuario)
    except NotImplementedError as erro:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Essa funcionalidade ainda não foi implementada pelo time.",
        ) from erro

    return AnaliseListResponse(analises=[AnaliseResponse.model_validate(a) for a in analises])


@router.get("/curriculos", response_model=CurriculoListResponse)
def listar_curriculos(
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoListResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    curriculos = analisador_service.listar_curriculos_usuario(usuario.id_usuario)
    return CurriculoListResponse(curriculos=[CurriculoItemResponse.model_validate(c) for c in curriculos])


@router.get("/curriculos/{id_curriculo}", response_model=CurriculoDetalhesResponse)
def obter_detalhes_curriculo(
    id_curriculo: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoDetalhesResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        detalhes = analisador_service.obter_detalhes_curriculo(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro

    return CurriculoDetalhesResponse.model_validate(detalhes)


@router.get("/curriculos/{id_curriculo}/download")
def baixar_arquivo_curriculo(
    id_curriculo: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
):
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        conteudo_arquivo, nome_arquivo = analisador_service.obter_arquivo_curriculo(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except CurriculoArquivoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo físico do currículo não encontrado.",
        ) from erro

    eh_pdf = nome_arquivo.lower().endswith(".pdf")
    media_type = "application/pdf" if eh_pdf else "application/octet-stream"
    disposicao = "inline" if eh_pdf else "attachment"
    return Response(
        content=conteudo_arquivo,
        media_type=media_type,
        headers={"Content-Disposition": f'{disposicao}; filename="{nome_arquivo}"'},
    )


@router.get("/curriculos/{id_curriculo}/edicao", response_model=CurriculoEdicaoResponse)
def obter_edicao_curriculo(
    id_curriculo: uuid.UUID,
    email: str,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoEdicaoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        dados_edicao = analisador_service.obter_dados_edicao_curriculo(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro

    return CurriculoEdicaoResponse.model_validate(dados_edicao)


@router.put("/curriculos/{id_curriculo}/edicao", response_model=CurriculoEdicaoResponse)
def salvar_edicao_estruturada_curriculo(
    id_curriculo: uuid.UUID,
    email: str,
    payload: CurriculoEdicaoEstruturadaRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoEdicaoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        analisador_service.salvar_edicao_estruturada_curriculo(
            usuario.id_usuario, id_curriculo, payload.model_dump()
        )
        dados_edicao = analisador_service.obter_dados_edicao_curriculo(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro

    return CurriculoEdicaoResponse.model_validate(dados_edicao)


@router.post("/curriculos/{id_curriculo}/edicao/texto-livre", response_model=CurriculoEdicaoResponse)
def salvar_edicao_texto_livre_curriculo(
    id_curriculo: uuid.UUID,
    email: str,
    payload: CurriculoEdicaoTextoLivreRequest,
    usuario_repository: UsuarioRepository = Depends(get_usuario_repository),
    analisador_service: AnalisadorService = Depends(get_analisador_service),
) -> CurriculoEdicaoResponse:
    usuario = usuario_repository.buscar_por_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não encontramos um usuário cadastrado com esse e-mail.",
        )

    try:
        analisador_service.salvar_edicao_texto_livre_curriculo(usuario.id_usuario, id_curriculo, payload.texto)
        dados_edicao = analisador_service.obter_dados_edicao_curriculo(usuario.id_usuario, id_curriculo)
    except CurriculoNaoEncontradoError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este usuário.",
        ) from erro
    except IAConfiguracaoAusenteError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro
    except IAIndisponivelError as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro)) from erro

    return CurriculoEdicaoResponse.model_validate(dados_edicao)
