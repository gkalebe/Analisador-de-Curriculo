import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SimulacaoIniciarRequest(BaseModel):
    email: EmailStr
    id_vaga: uuid.UUID


class RespostaSimulacaoRequest(BaseModel):
    email: EmailStr
    resposta: str = Field(min_length=1, max_length=4000)


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


class SimulacaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_simulacao: uuid.UUID
    id_vaga: uuid.UUID
    data_criacao: datetime
    perguntas: list[PerguntaSimulacaoResponse]


class SimulacaoItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id_simulacao: uuid.UUID
    id_vaga: uuid.UUID
    data_criacao: datetime
    total_perguntas: int
    total_respondidas: int


class SimulacaoListResponse(BaseModel):
    simulacoes: list[SimulacaoItemResponse]
