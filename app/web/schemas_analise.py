import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.web.paginacao import PaginacaoMeta


class AnaliseResponse(BaseModel):
    id_analise: uuid.UUID
    id_curriculo: uuid.UUID
    id_vaga: uuid.UUID
    pontuacao: float | None
    observacoes: str | None
    data_analise: datetime
    titulo_vaga: str | None = None
    nome_curriculo: str | None = None
    curriculo_possui_edicao: bool = False

    model_config = {"from_attributes": True}


class AnaliseListResponse(BaseModel):
    analises: list[AnaliseResponse]
    paginacao: PaginacaoMeta


class RecomendacaoCompetenciaResponse(BaseModel):
    competencia: str
    tipo: Literal["obrigatorio", "desejavel"]
    status: Literal["parcial", "nao_evidenciado"]
    orientacoes: list[str]
    onde_evidenciar: str | None = None
    origem: Literal["ia", "padrao"]


class RecomendacoesCompetenciasResponse(BaseModel):
    id_analise: uuid.UUID
    sem_lacunas: bool
    recomendacoes: list[RecomendacaoCompetenciaResponse]
