import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class VagaCreateRequest(BaseModel):
    email: EmailStr
    titulo: str = Field(default="", max_length=200)
    descricao: str = Field(min_length=1)
    requisitos: str = Field(default="", max_length=5000)
    area: str = Field(default="", max_length=100)

    @field_validator("descricao")
    @classmethod
    def validar_descricao(cls, valor: str) -> str:
        valor_normalizado = (valor or "").strip()
        if not valor_normalizado:
            raise ValueError("A descrição da vaga é obrigatória.")
        return valor_normalizado


class VagaResponse(BaseModel):
    id_vaga: uuid.UUID
    titulo: str | None
    descricao: str
    requisitos: str | None
    area: str | None
    data_criacao: datetime

    model_config = {"from_attributes": True}


class VagaListResponse(BaseModel):
    vagas: list[VagaResponse]
