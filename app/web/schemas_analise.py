import uuid
from datetime import datetime

from pydantic import BaseModel


class AnaliseResponse(BaseModel):
    id_analise: uuid.UUID
    id_curriculo: uuid.UUID
    id_vaga: uuid.UUID
    pontuacao: float | None
    observacoes: str | None
    data_analise: datetime
    titulo_vaga: str | None = None
    nome_curriculo: str | None = None

    model_config = {"from_attributes": True}


class AnaliseListResponse(BaseModel):
    analises: list[AnaliseResponse]
