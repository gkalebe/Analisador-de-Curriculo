import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class VagaCreateRequest(BaseModel):
    email: EmailStr | None = None
    titulo: str = Field(default="", max_length=200)
    descricao: str = Field(min_length=1, max_length=20000)
    requisitos: str = Field(default="", max_length=5000)
    area: str = Field(default="", max_length=100)
    empresa: str = Field(default="", max_length=200)
    localizacao: str = Field(default="", max_length=200)
    modalidade: str = Field(default="", max_length=100)
    senioridade: str = Field(default="", max_length=100)
    tipo_contratacao: str = Field(default="", max_length=100)
    faixa_salarial: str = Field(default="", max_length=200)
    responsabilidades: str = Field(default="", max_length=10000)
    requisitos_obrigatorios: str = Field(default="", max_length=10000)
    requisitos_desejaveis: str = Field(default="", max_length=10000)
    competencias: str = Field(default="", max_length=5000)
    idiomas: str = Field(default="", max_length=2000)
    beneficios: str = Field(default="", max_length=5000)
    url_origem: str = Field(default="", max_length=2048)

    @field_validator("descricao")
    @classmethod
    def validar_descricao(cls, valor: str) -> str:
        valor_normalizado = (valor or "").strip()
        if not valor_normalizado:
            raise ValueError("A descrição da vaga é obrigatória.")
        return valor_normalizado


class VagaImportRequest(BaseModel):
    email: EmailStr | None = None
    url: str = Field(min_length=1, max_length=2048)


class VagaImportPreviewResponse(BaseModel):
    titulo: str = ""
    descricao: str
    requisitos: str = ""
    area: str = ""
    empresa: str = ""
    localizacao: str = ""
    modalidade: str = ""
    senioridade: str = ""
    tipo_contratacao: str = ""
    faixa_salarial: str = ""
    responsabilidades: str = ""
    requisitos_obrigatorios: str = ""
    requisitos_desejaveis: str = ""
    competencias: str = ""
    idiomas: str = ""
    beneficios: str = ""
    url_origem: str


class VagaResponse(BaseModel):
    id_vaga: uuid.UUID
    titulo: str | None
    descricao: str
    requisitos: str | None
    area: str | None
    empresa: str | None
    localizacao: str | None
    modalidade: str | None
    senioridade: str | None
    tipo_contratacao: str | None
    faixa_salarial: str | None
    responsabilidades: str | None
    requisitos_obrigatorios: str | None
    requisitos_desejaveis: str | None
    competencias: str | None
    idiomas: str | None
    beneficios: str | None
    url_origem: str | None
    data_criacao: datetime

    model_config = {"from_attributes": True}


class VagaListResponse(BaseModel):
    vagas: list[VagaResponse]
