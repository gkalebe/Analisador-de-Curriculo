import uuid
from datetime import datetime
from typing import Literal

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
    # Aceita tanto os 7 campos planos (edição campo a campo) quanto o currículo estruturado
    # completo (mesmo shape devolvido em CurriculoEdicaoResponse.dados) — o service decide
    # pelo formato recebido.
    model_config = {"extra": "allow"}


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
    nome_curriculo: str | None = None
    data_upload: datetime
    status_processamento: str
    texto_extraido: str | None = None
    possui_arquivo: bool = False
    dados: CurriculoDadosEstruturados | None = None


class CurriculoEdicaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_curriculo: uuid.UUID
    dados: dict = {}
    possui_edicao: bool = False
    editado_em: datetime | None = None
    sugestoes: dict | None = None
    # Preenchido só pela rota de aplicar sugestões: o que foi/não foi aplicado na reescrita.
    relatorio_aplicacao: dict | None = None
