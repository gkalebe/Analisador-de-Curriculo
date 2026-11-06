from datetime import datetime

from pydantic import BaseModel, Field


class PlanoCatalogoResponse(BaseModel):
    codigo: str
    nome: str
    preco_centavos: int
    moeda: str
    intervalo: str
    limite_analises: int
    limite_estruturacoes: int
    limite_mensagens_chat: int
    limite_entrevistas: int
    limite_curriculos: int
    creditos_orcamento: int
    creditos_analise: int
    creditos_demais_operacoes: int


class PlanosCatalogoResponse(BaseModel):
    planos: list[PlanoCatalogoResponse]


class UsoPlanoResponse(BaseModel):
    plano: PlanoCatalogoResponse
    inicio_janela: datetime | None
    fim_janela: datetime | None
    usos: dict[str, int]
    assinatura_status: str | None = None
    plano_pendente_codigo: str | None = None
    cancelamento_agendado: bool = False
    acesso_ate: datetime | None = None


class UsoAtualResponse(BaseModel):
    uso: UsoPlanoResponse


class AlterarPlanoRequest(BaseModel):
    plano_codigo: str = Field(min_length=1, max_length=20)


class LinkAssinaturaResponse(BaseModel):
    url: str


class MensagemAssinaturaResponse(BaseModel):
    mensagem: str
