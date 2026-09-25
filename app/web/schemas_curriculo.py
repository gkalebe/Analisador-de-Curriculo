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


class CurriculoAtualizacaoRequest(CurriculoDadosEstruturados):
    nome_curriculo: str | None = None


class CurriculoCriacaoManualRequest(CurriculoDadosEstruturados):
    nome_curriculo: str


class CurriculoEdicaoEstruturadaRequest(CurriculoDadosEstruturados):
    pass


class CurriculoEdicaoTextoLivreRequest(BaseModel):
    texto: str = ""


class CurriculoResponse(BaseModel):
    id_curriculo: uuid.UUID
    nome_arquivo: str
    tamanho_texto_extraido: int
    dados: CurriculoDadosEstruturados | None = None


class CurriculoItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    nome_arquivo: str
    nome_curriculo: str | None = None
    data_upload: datetime
    status_processamento: str
    possui_arquivo: bool = False


class CurriculoListResponse(BaseModel):
    curriculos: list[CurriculoItemResponse]


class CurriculoDetalhesResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    nome_arquivo: str
    nome_curriculo: str | None = None
    data_upload: datetime
    status_processamento: str
    texto_extraido: str | None = None
    possui_arquivo: bool = False
    dados: CurriculoDadosEstruturados | None = None


class CurriculoEdicaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    dados: dict[str, str] = {}
    possui_edicao: bool = False
    editado_em: datetime | None = None
    sugestoes: dict | None = None
