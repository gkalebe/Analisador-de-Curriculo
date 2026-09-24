import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class BibliotecaCurriculoItemResponse(BaseModel):
    id_curriculo: uuid.UUID
    nome_arquivo: str
    data_upload: datetime
    origem: Literal["usuario", "ia"]
    vaga_titulo: str | None = None
    possui_arquivo: bool
    ultima_atividade: datetime


class BibliotecaCurriculosResponse(BaseModel):
    enviados_por_mim: list[BibliotecaCurriculoItemResponse]
    gerados_por_ia: list[BibliotecaCurriculoItemResponse]


class CurriculoDetalhesResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    nome_arquivo: str
    data_upload: datetime
    status_processamento: str
    texto_extraido: str | None = None


class SugestaoReescritaItem(BaseModel):
    campo: str | None = None
    trecho_original: str | None = None
    versao_otimizada: str | None = None
    justificativa: str | None = None


class CurriculoEdicaoSugestoesResponse(BaseModel):
    resumo: str | None = None
    palavras_chave_faltantes: list[str] = []
    diagnostico_ats: dict | None = None
    sugestoes_reescrita: list[SugestaoReescritaItem] = []


class CurriculoEdicaoDadosResponse(BaseModel):
    nome: str = ""
    email: str = ""
    telefone: str = ""
    resumo: str = ""
    formacao: str = ""
    experiencia_profissional: str = ""
    habilidades: str = ""
    texto_bruto: str = ""


class CurriculoEdicaoResponse(BaseModel):
    id_curriculo: uuid.UUID
    dados: CurriculoEdicaoDadosResponse
    possui_edicao: bool
    editado_em: datetime | None = None
    sugestoes: CurriculoEdicaoSugestoesResponse | None = None


class CurriculoEdicaoEstruturadaRequest(BaseModel):
    nome: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=200)
    telefone: str = Field(default="", max_length=50)
    resumo: str = Field(default="", max_length=3000)
    formacao: str = Field(default="", max_length=4000)
    experiencia_profissional: str = Field(default="", max_length=6000)
    habilidades: str = Field(default="", max_length=2000)


class CurriculoEdicaoTextoLivreRequest(BaseModel):
    texto: str = Field(min_length=1, max_length=20000)
