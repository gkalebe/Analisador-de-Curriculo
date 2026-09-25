import uuid
from datetime import datetime

from pydantic import BaseModel


class CurriculoDadosEstruturados(BaseModel):
    nome: str | None = None
    email: str | None = None
    telefone: str | None = None
    resumo: str | None = None
    formacao: str | None = None
    experiencia_profissional: str | None = None
    habilidades: str | None = None


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
    dados: CurriculoDadosEstruturados | None = None


class CurriculoAtualizacaoRequest(CurriculoDadosEstruturados):
    pass
