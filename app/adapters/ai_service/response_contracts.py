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

    @field_validator("tipo", mode="before")
    @classmethod
    def normalizar_tipo(cls, valor: str) -> str:
        if not isinstance(valor, str):
            return valor
        v = valor.strip().lower()
        if "obrigat" in v:
            return "obrigatorio"
        if "desej" in v or "pref" in v or "diferencial" in v:
            return "desejavel"
        return v

    @field_validator("status", mode="before")
    @classmethod
    def normalizar_status(cls, valor: str) -> str:
        if not isinstance(valor, str):
            return valor
        v = valor.strip().lower().replace("-", "_").replace(" ", "_")
        v = v.replace("não", "nao").replace("parcialmente", "parcial")
        if "nao" in v or "ausente" in v or "falta" in v:
            return "nao_evidenciado"
        if "parcial" in v:
            return "parcial"
        if "evidenciad" in v or "atendido" in v or "presente" in v or "cumpre" in v:
            return "evidenciado"
        return v


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


class DimensaoAvaliacaoEntrevista(BaseModel):
    model_config = ConfigDict(extra="ignore")

    nota: float = Field(ge=0, le=10)
    comentario: str = ""

    @field_validator("nota", mode="before")
    @classmethod
    def rejeitar_booleano_como_nota(cls, valor):
        if isinstance(valor, bool):
            raise ValueError("A nota precisa ser numérica.")
        return valor


class AvaliacaoPerguntaEntrevista(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Posição (1..N) da pergunta no roteiro enviado à IA; mais robusto que pedir que ela
    # devolva um UUID sem alterá-lo.
    ordem: int
    clareza: DimensaoAvaliacaoEntrevista
    objetividade: DimensaoAvaliacaoEntrevista
    coerencia: DimensaoAvaliacaoEntrevista
    alinhamento: DimensaoAvaliacaoEntrevista
    feedback_geral: str = ""


class ResultadoAvaliacaoEntrevista(BaseModel):
    model_config = ConfigDict(extra="ignore")

    avaliacoes: list[AvaliacaoPerguntaEntrevista]
    feedback_geral: str = ""


def interpretar_avaliacao_entrevista(resultado: str, total_perguntas: int) -> ResultadoAvaliacaoEntrevista:
    """Valida a avaliação em lote: JSON válido, notas de 0 a 10 e exatamente uma avaliação para
    cada pergunta (ordem 1..total_perguntas), sem faltar nem repetir. Qualquer desvio vira
    `IARespostaInvalidaError` — nunca uma simulação "avaliada" pela metade."""
    texto = (resultado or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    try:
        dados = json.loads(texto)
    except (json.JSONDecodeError, TypeError) as erro:
        raise IARespostaInvalidaError("A IA não retornou um JSON válido para a avaliação da entrevista.") from erro

    try:
        avaliacao = ResultadoAvaliacaoEntrevista.model_validate(dados)
    except (ValueError, TypeError) as erro:
        raise IARespostaInvalidaError("A resposta da IA não corresponde ao formato da avaliação da entrevista.") from erro

    ordens = [item.ordem for item in avaliacao.avaliacoes]
    if sorted(ordens) != list(range(1, total_perguntas + 1)):
        raise IARespostaInvalidaError("A IA não avaliou todas as perguntas da entrevista. Tente novamente.")
    return avaliacao
