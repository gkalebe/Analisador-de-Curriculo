import uuid
from datetime import datetime

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.web.paginacao import PaginacaoMeta


class SimulacaoIniciarRequest(BaseModel):
    email: EmailStr | None = None
    id_vaga: uuid.UUID


TAMANHO_MINIMO_RESPOSTA = 10
TAMANHO_MAXIMO_RESPOSTA = 4000
MAXIMO_PERGUNTAS_POR_SIMULACAO = 20


class RespostaPerguntaRequest(BaseModel):
    id_pergunta: uuid.UUID
    resposta: str = Field(min_length=TAMANHO_MINIMO_RESPOSTA, max_length=TAMANHO_MAXIMO_RESPOSTA)

    @field_validator("resposta", mode="before")
    @classmethod
    def remover_espacos_nas_pontas(cls, valor):
        # O tamanho mínimo vale para o texto útil: "          " ou "ok" não contam como resposta.
        return valor.strip() if isinstance(valor, str) else valor


class AvaliacaoSimulacaoRequest(BaseModel):
    email: EmailStr | None = None
    respostas: list[RespostaPerguntaRequest] = Field(min_length=1, max_length=MAXIMO_PERGUNTAS_POR_SIMULACAO)

    @model_validator(mode="after")
    def rejeitar_perguntas_repetidas(self):
        ids = [item.id_pergunta for item in self.respostas]
        if len(set(ids)) != len(ids):
            raise ValueError("Cada pergunta deve ser respondida uma única vez.")
        return self


class DimensaoFeedback(BaseModel):
    nota: float | None = None
    comentario: str = ""


class FeedbackRespostaResponse(BaseModel):
    clareza: DimensaoFeedback
    objetividade: DimensaoFeedback
    coerencia: DimensaoFeedback
    alinhamento: DimensaoFeedback
    feedback_geral: str = ""


class PerguntaSimulacaoResponse(BaseModel):
    id_pergunta: str
    tipo: str
    texto: str
    resposta: str | None = None
    feedback: FeedbackRespostaResponse | None = None
    respondida_em: str | None = None


StatusSimulacao = Literal["pendente", "avaliada"]


class SimulacaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_simulacao: uuid.UUID
    id_vaga: uuid.UUID
    vaga_titulo: str | None = None
    data_criacao: datetime
    status: StatusSimulacao
    # Simulação do fluxo antigo (feedback por pergunta): somente leitura.
    legada: bool = False
    avaliada_em: datetime | None = None
    nota_final: float | None = Field(default=None, validation_alias="nota_geral")
    feedback_geral: str | None = None
    perguntas: list[PerguntaSimulacaoResponse]


class SimulacaoItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_simulacao: uuid.UUID
    id_vaga: uuid.UUID
    vaga_titulo: str | None = None
    data_criacao: datetime
    status: StatusSimulacao
    legada: bool = False
    avaliada_em: datetime | None = None
    nota_final: float | None = Field(default=None, validation_alias="nota_geral")
    total_perguntas: int
    total_respondidas: int


class SimulacaoListResponse(BaseModel):
    simulacoes: list[SimulacaoItemResponse]
    paginacao: PaginacaoMeta
