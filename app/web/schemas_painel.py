import uuid
from datetime import datetime

from pydantic import BaseModel

from app.web.paginacao import PaginacaoMeta


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
    paginacao: PaginacaoMeta
    lacunas_recorrentes: list[LacunaRecorrente]
