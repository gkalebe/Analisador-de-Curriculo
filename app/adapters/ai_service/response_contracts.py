import json
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.adapters.ai_service.ai_service_adapter import IARespostaInvalidaError
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado


class PalavrasChaveAnalise(BaseModel):
    model_config = ConfigDict(extra="allow")

    correspondentes: list[str]
    ausentes: list[str]


class DiagnosticoATS(BaseModel):
    model_config = ConfigDict(extra="allow")

    pontos_fortes: list[str]
    o_que_reorganizar: list[str]
    o_que_retirar: list[str]


class SugestaoReescrita(BaseModel):
    model_config = ConfigDict(extra="allow")

    campo: Literal["resumo", "formacao", "experiencia_profissional", "habilidades"]
    trecho_original: str
    sugestao_otimizada: str = Field(
        validation_alias=AliasChoices("sugestao_otimizada", "versao_otimizada")
    )
    motivo: str = Field(validation_alias=AliasChoices("motivo", "justificativa"))


class RequisitoAvaliado(BaseModel):
    model_config = ConfigDict(extra="allow")

    requisito: str
    tipo: Literal["obrigatorio", "desejavel"]
    status: Literal["evidenciado", "parcial", "nao_evidenciado"]
    evidencia: str


class ResultadoComparacaoCurriculoVaga(BaseModel):
    model_config = ConfigDict(extra="allow")

    pontuacao: float = Field(ge=0, le=100)
    resumo: str
    observacoes: str
    palavras_chave: PalavrasChaveAnalise
    diagnostico_ats: DiagnosticoATS
    sugestoes_reescrita: list[SugestaoReescrita]
    requisitos_avaliados: list[RequisitoAvaliado] = Field(default_factory=list)
    curriculo_estruturado: DadosCurriculoEstruturado

    @field_validator("pontuacao", mode="before")
    @classmethod
    def rejeitar_booleano_como_pontuacao(cls, valor):
        if isinstance(valor, bool):
            raise ValueError("A pontuação precisa ser numérica.")
        return valor


def interpretar_resultado_comparacao(resultado: str) -> ResultadoComparacaoCurriculoVaga:
    texto = (resultado or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError) as erro:
        raise IARespostaInvalidaError("A IA não retornou um JSON válido para a análise.") from erro

    try:
        return ResultadoComparacaoCurriculoVaga.model_validate(dados)
    except (ValueError, TypeError) as erro:
        raise IARespostaInvalidaError("A resposta da IA não corresponde ao contrato da análise.") from erro
