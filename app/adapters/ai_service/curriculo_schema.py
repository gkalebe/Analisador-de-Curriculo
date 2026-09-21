"""Contrato de dados do pipeline de geração estruturada de currículo.

Este schema Pydantic é o único contrato compartilhado pelas 3 etapas do
pipeline (`curriculo_estruturado_client.py` na Etapa 1, `curriculo_validador.py`
na Etapa 2 e `curriculo_template_exporter.py` na Etapa 3). Ele fica isolado
num módulo próprio, sem depender de nenhuma das 3 etapas, exatamente para que
qualquer uma delas possa ser trocada — outro provedor de IA, outra lib de
validação, outro motor de template — sem que as demais percebam a mudança.

É também o `response_schema` passado direto para a API do Gemini (JSON mode):
a IA é forçada pela própria API a preencher exatamente estes campos, no
formato exato, nunca "reescrevendo" o currículo em texto livre.
"""

from pydantic import BaseModel, Field


class ContatoCurriculo(BaseModel):
    email: str = ""
    telefone: str = ""
    linkedin: str = ""
    cidade: str = ""


class ExperienciaCurriculo(BaseModel):
    cargo: str = ""
    empresa: str = ""
    periodo_inicio: str = ""
    periodo_fim: str = ""
    descricao_bullets: list[str] = Field(default_factory=list)


class FormacaoCurriculo(BaseModel):
    curso: str = ""
    instituicao: str = ""
    periodo: str = ""


class IdiomaCurriculo(BaseModel):
    idioma: str = ""
    nivel: str = ""


class DadosCurriculoEstruturado(BaseModel):
    nome_completo: str = ""
    titulo_profissional: str = ""
    contato: ContatoCurriculo = Field(default_factory=ContatoCurriculo)
    resumo_profissional: str = ""
    experiencias: list[ExperienciaCurriculo] = Field(default_factory=list)
    formacao: list[FormacaoCurriculo] = Field(default_factory=list)
    habilidades_tecnicas: list[str] = Field(default_factory=list)
    idiomas: list[IdiomaCurriculo] = Field(default_factory=list)
    certificacoes: list[str] = Field(default_factory=list)


# Campos de texto simples tratados como obrigatórios pela Etapa 2: um
# currículo sem nome/título/resumo não é utilizável. Os campos em lista
# (experiencias, formacao, habilidades_tecnicas, idiomas, certificacoes) NUNCA
# entram aqui — uma lista vazia costuma ser um dado real (ex.: candidato sem
# certificações), não um erro de extração, então não faz sentido "reparar"
# uma lista vazia com retry de IA.
CAMPOS_TEXTO_OBRIGATORIOS = ("nome_completo", "titulo_profissional", "resumo_profissional")
