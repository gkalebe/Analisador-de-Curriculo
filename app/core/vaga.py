"""
Router: Vaga (Controller - MVC)

Implementa a US-005 - Colar descrição textual de uma vaga.

Endpoints:
    POST /api/vagas         -> associa uma nova descrição de vaga à sessão de análise
    GET  /api/vagas         -> lista vagas salvas pelo usuário autenticado (reuso - US-019)
    GET  /api/vagas/{id}    -> recupera uma vaga específica do usuário autenticado

Dependência: US-002 (login) - todas as rotas exigem usuário autenticado.
Regras de negócio aplicadas:
    RN-002 - sigilo dos dados do usuário
    RN-003 - a comparação currículo x vaga só ocorre com os dois documentos
    RN-015 - isolamento total entre usuários
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_usuario_atual
from app.models.usuario import Usuario
from app.models.vaga import Vaga
from app.schemas.vaga import VagaCreate, VagaResponse

router = APIRouter(prefix="/api/vagas", tags=["Vagas"])


def _para_response(vaga: Vaga) -> VagaResponse:
    """Converte a entidade Vaga (Model) para o schema de resposta (VagaResponse)."""
    return VagaResponse(
        id=vaga.id,
        titulo=vaga.titulo,
        empresa=vaga.empresa,
        descricao=vaga.descricao,
        criado_em=vaga.criado_em,
        caracteres_utilizados=len(vaga.descricao),
    )


@router.post(
    "",
    response_model=VagaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Colar descrição textual de uma vaga (US-005)",
)
def criar_vaga(
    payload: VagaCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
) -> VagaResponse:
    """
    Critério 1 (US-005): aceita descrição de até 5.000 caracteres e a
    associa à sessão de análise do usuário autenticado.

    Critério 2 (US-005): se o texto exceder 5.000 caracteres, o schema
    VagaCreate já rejeita o payload antes de chegar aqui, retornando
    automaticamente 422 Unprocessable Entity com a mensagem informativa
    do validador — o frontend deve exibir esse "detail" como alerta.
    """
    nova_vaga = Vaga(
        usuario_id=usuario_atual.id,
        titulo=payload.titulo,
        empresa=payload.empresa,
        descricao=payload.descricao,
    )

    db.add(nova_vaga)
    db.commit()
    db.refresh(nova_vaga)

    return _para_response(nova_vaga)


@router.get(
    "",
    response_model=list[VagaResponse],
    summary="Listar vagas salvas pelo usuário autenticado (reuso - US-019)",
)
def listar_vagas(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
) -> list[VagaResponse]:
    """RN-015: retorna exclusivamente as vagas vinculadas ao usuário autenticado."""
    vagas = db.scalars(
        select(Vaga)
        .where(Vaga.usuario_id == usuario_atual.id)
        .order_by(Vaga.criado_em.desc())
    ).all()

    return [_para_response(v) for v in vagas]


@router.get(
    "/{vaga_id}",
    response_model=VagaResponse,
    summary="Recuperar uma vaga específica do usuário autenticado",
)
def obter_vaga(
    vaga_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_usuario_atual),
) -> VagaResponse:
    vaga = db.scalar(
        select(Vaga).where(Vaga.id == vaga_id, Vaga.usuario_id == usuario_atual.id)
    )

    if vaga is None:
        # RN-015: não revela se a vaga pertence a outro usuário — apenas 404 genérico.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaga não encontrada.",
        )

    return _para_response(vaga)