import uuid
from datetime import datetime

from pydantic import BaseModel

from app.web.paginacao import PaginacaoMeta
from app.web.schemas_analise import CertificacaoSugeridaResponse, ItemPlanoDesenvolvimentoResponse


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


class VagaDoPlano(BaseModel):
    id_analise: uuid.UUID
    vaga_titulo: str


class ItemPlanoConsolidado(ItemPlanoDesenvolvimentoResponse):
    vagas: list[VagaDoPlano]
    frequencia: int


class ResumoPlano(BaseModel):
    alta: int
    media: int
    baixa: int
    total: int


class PlanoDesenvolvimentoResponse(BaseModel):
    total_analises: int
    sem_analises: bool
    sem_lacunas: bool
    mensagem: str
    resumo: ResumoPlano
    itens: list[ItemPlanoConsolidado]
    certificacoes_opcionais: list[CertificacaoSugeridaResponse]
