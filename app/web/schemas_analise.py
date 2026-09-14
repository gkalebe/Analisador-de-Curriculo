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

    model_config = {"from_attributes": True}


class AnaliseListResponse(BaseModel):
    analises: list[AnaliseResponse]
