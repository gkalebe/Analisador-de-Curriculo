import uuid
from datetime import datetime

from pydantic import BaseModel


class CurriculoResponse(BaseModel):
    id_curriculo: uuid.UUID
    nome_arquivo: str
    tamanho_texto_extraido: int


class CurriculoItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    nome_arquivo: str
    data_upload: datetime
    status_processamento: str


class CurriculoListResponse(BaseModel):
    curriculos: list[CurriculoItemResponse]


class CurriculoDetalhesResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    nome_arquivo: str
    data_upload: datetime
    status_processamento: str
    texto_extraido: str | None = None
