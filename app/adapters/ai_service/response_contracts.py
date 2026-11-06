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


class RecomendacaoCompetenciaIA(BaseModel):
    """US-014: orientação da IA para evidenciar uma competência em lacuna. A cobertura (uma
    recomendação por lacuna) é garantida depois, em core/service/recomendacoes_competencias.py."""

    model_config = ConfigDict(extra="allow")

    competencia: str
    orientacoes: list[str] = Field(default_factory=list)
    onde_evidenciar: str = ""


class CertificacaoSugeridaIA(BaseModel):
    model_config = ConfigDict(extra="allow")

    nome: str
    emissor: str = ""
    motivo: str = ""


class ItemPlanoDesenvolvimentoIA(BaseModel):
    model_config = ConfigDict(extra="allow")

    competencia: str
    prioridade: str = ""
    certificacoes: list[CertificacaoSugeridaIA] = Field(default_factory=list)
    trilha: list[str] = Field(default_factory=list)


class PlanoDesenvolvimentoIA(BaseModel):
    """US-015: trilha/certificações por lacuna, completadas em core/service/plano_desenvolvimento.py."""

    model_config = ConfigDict(extra="allow")

    itens: list[ItemPlanoDesenvolvimentoIA] = Field(default_factory=list)
    certificacoes_opcionais: list[CertificacaoSugeridaIA] = Field(default_factory=list)


class ResultadoComparacaoCurriculoVaga(BaseModel):
    model_config = ConfigDict(extra="allow")

    pontuacao: float = Field(ge=0, le=100)
    resumo: str
    observacoes: str
    palavras_chave: PalavrasChaveAnalise
    diagnostico_ats: DiagnosticoATS
    sugestoes_reescrita: list[SugestaoReescrita]
    requisitos_avaliados: list[RequisitoAvaliado] = Field(default_factory=list)
    recomendacoes_competencias: list[RecomendacaoCompetenciaIA] = Field(default_factory=list)
    plano_desenvolvimento: PlanoDesenvolvimentoIA = Field(default_factory=PlanoDesenvolvimentoIA)
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
