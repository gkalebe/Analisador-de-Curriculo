"""
Schemas Pydantic para a funcionalidade US-005 - Colar descrição textual de uma vaga.

Validar a entrada do usuário antes de chegar à camada de
persistência (Model), incluindo o limite de 5.000 caracteres exigido
pelo critério de aceite da US-005.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

LIMITE_CARACTERES_DESCRICAO = 5000


class VagaCreate(BaseModel):
    """Payload recebido do frontend ao colar a descrição da vaga."""

    titulo: str | None = Field(
        default=None,
        max_length=200,
        description="Título da vaga (opcional).",
    )
    empresa: str | None = Field(
        default=None,
        max_length=150,
        description="Nome da empresa (opcional).",
    )
    descricao: str = Field(
        ...,
        min_length=1,
        description="Descrição textual completa da vaga (obrigatória).",
    )

    @field_validator("descricao")
    @classmethod
    def validar_limite_de_caracteres(cls, valor: str) -> str:
        """
        Critério de aceite (US-005):
        "Bloqueia envio acima do limite com alerta informativo."

        A validação ocorre aqui, antes de qualquer persistência. Se
        violada, o FastAPI responde automaticamente com 422 Unprocessable
        Entity contendo esta mensagem, que o frontend deve exibir ao
        usuário como alerta.
        """
        texto_limpo = valor.strip()

        if len(texto_limpo) == 0:
            raise ValueError("A descrição da vaga não pode estar vazia.")

        if len(texto_limpo) > LIMITE_CARACTERES_DESCRICAO:
            excedente = len(texto_limpo) - LIMITE_CARACTERES_DESCRICAO
            raise ValueError(
                f"A descrição da vaga excede o limite de "
                f"{LIMITE_CARACTERES_DESCRICAO} caracteres em {excedente} "
                f"caractere(s). Reduza o texto para continuar."
            )

        return texto_limpo


class VagaResponse(BaseModel):
    """Retorno da API após a vaga ser associada à sessão de análise do usuário."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str | None
    empresa: str | None
    descricao: str
    criado_em: datetime
    caracteres_utilizados: int
    limite_caracteres: int = LIMITE_CARACTERES_DESCRICAO