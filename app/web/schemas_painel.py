import uuid
from datetime import datetime

from pydantic import BaseModel


class HistoricoAnaliseItem(BaseModel):
    id_analise: uuid.UUID
    data_analise: datetime
    vaga_titulo: str
    pontuacao: float | None

    model_config = {"from_attributes": True}


class LacunaRecorrente(BaseModel):
    competencia: str
    frequencia: int


class PainelHistoricoResponse(BaseModel):
    historico: list[HistoricoAnaliseItem]
    lacunas_recorrentes: list[LacunaRecorrente]
