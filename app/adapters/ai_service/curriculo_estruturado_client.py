"""Etapa 1 do pipeline: geração de conteúdo estruturado via o provider ativo.

Por que esta etapa é isolada das outras 2: é a ÚNICA parte do pipeline que
fala com um provedor de IA. A chamada passa pelo `AIServiceAdapter`, que escolhe
Claude ou Gemini pela configuração do servidor; a validação (Etapa 2) e a
montagem do documento (Etapa 3) continuam funcionando exatamente iguais,
porque as duas só conhecem o contrato Pydantic (`curriculo_schema.py`), nunca
a API de um provedor específico.

A IA aqui NUNCA gera o documento final nem texto já formatado: ela só devolve
um JSON validado contra `DadosCurriculoEstruturado` (JSON mode + response
schema nativo quando o provider oferece suporte; nos demais, o schema é
incluído na instrução e validado localmente). Isso elimina dependência de
SDKs de provider neste pipeline.
"""

import json

from pydantic import BaseModel, ValidationError

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    IARespostaInvalidaError,
)
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado

PROMPT_SISTEMA = """\
Você é um assistente de RH especializado em estruturar dados de currículo.

TAREFA: a partir das informações brutas fornecidas pelo usuário (texto livre, \
respostas de formulário ou um currículo antigo colado), preencha TODOS os \
campos do schema JSON fornecido.

REGRAS ESTRITAS:
1. Preencha todos os campos obrigatórios com base SOMENTE nas informações \
brutas fornecidas.
2. NUNCA invente, deduza ou complete dados que não estejam nas informações \
brutas (nem empresas, nem cargos, nem datas, nem números).
3. NUNCA resuma, corte ou omita experiências profissionais, formações, \
habilidades, idiomas ou certificações mencionadas nas informações brutas — \
liste TODAS elas, uma por item de lista.
4. Se um campo de texto não tiver informação suficiente nas informações \
brutas, retorne string vazia "". Se uma lista não tiver itens, retorne lista \
vazia []. Nunca invente um valor só para preencher o campo.
5. `descricao_bullets` de cada experiência deve conter as responsabilidades/ \
conquistas descritas para aquela experiência, cada uma como um item de lista \
separado (não junte tudo em uma única string).
6. Você NÃO deve reescrever o currículo em prosa nem gerar texto formatado \
para exibição — apenas extrair e estruturar os dados brutos nos campos do \
schema.

INFORMAÇÕES BRUTAS FORNECIDAS PELO USUÁRIO:
"""

PROMPT_RETRY_CAMPO = """\
Você é um assistente de RH. A partir das informações brutas de currículo \
abaixo, extraia SOMENTE o valor do campo "{nome_campo}" ({descricao_campo}).

Regras: baseie-se apenas no texto abaixo, nunca invente dados. Se não houver \
informação suficiente para esse campo específico, retorne string vazia "".

INFORMAÇÕES BRUTAS:
{informacoes_brutas}
"""

DESCRICOES_CAMPOS = {
    "nome_completo": "o nome completo da pessoa",
    "titulo_profissional": "o título/cargo profissional que melhor resume o perfil",
    "resumo_profissional": "um resumo profissional objetivo, de 2 a 4 frases",
}


class _CampoUnico(BaseModel):
    """Schema mínimo usado só no retry cirúrgico de um campo — não herda de
    `DadosCurriculoEstruturado` de propósito, para a resposta da IA vir com
    um único campo, mantendo o retry barato."""

    valor: str = ""


class GeradorCurriculoEstruturadoIA:
    def __init__(self, ai_service_adapter: AIServiceAdapter | None = None):
        self.ai_service_adapter = ai_service_adapter or AIServiceAdapter()

    def gerar(self, informacoes_brutas: str) -> DadosCurriculoEstruturado:
        """Gera o JSON estruturado completo a partir das informações brutas.

        Levanta `IAConfiguracaoAusenteError`, `IAIndisponivelError` ou
        `IARespostaInvalidaError` conforme a falha.
        """
        texto_resposta = self._chamar(
            PROMPT_SISTEMA + informacoes_brutas, DadosCurriculoEstruturado, "curriculo_estruturado"
        )
        return self._parsear_resposta(texto_resposta, DadosCurriculoEstruturado)

    def regenerar_campo(self, informacoes_brutas: str, nome_campo: str) -> str:
        """Retry cirúrgico: pede à IA SÓ o valor de um campo específico.

        Usada pela Etapa 2 (validação) quando um campo obrigatório volta
        vazio — muito mais barata que regenerar o currículo inteiro, pois o
        prompt e a resposta são mínimos.
        """
        descricao_campo = DESCRICOES_CAMPOS.get(nome_campo, nome_campo)
        prompt = PROMPT_RETRY_CAMPO.format(
            nome_campo=nome_campo,
            descricao_campo=descricao_campo,
            informacoes_brutas=informacoes_brutas,
        )
        texto_resposta = self._chamar(prompt, _CampoUnico, "curriculo_campo_retry")
        dados_campo = self._parsear_resposta(texto_resposta, _CampoUnico)
        return dados_campo.valor

    def _chamar(self, prompt: str, response_schema: type[BaseModel], operacao: str) -> str:
        return self.ai_service_adapter.gerar_resposta_estruturada(
            prompt,
            response_schema,
            operacao=operacao,
            temperatura=0.2,
        )

    def _parsear_resposta(self, texto_resposta: str, schema: type[BaseModel]) -> BaseModel:
        try:
            dados_brutos = json.loads(texto_resposta)
        except (json.JSONDecodeError, TypeError) as erro:
            raise IARespostaInvalidaError("A IA não retornou um JSON válido.") from erro
        try:
            return schema.model_validate(dados_brutos)
        except ValidationError as erro:
            raise IARespostaInvalidaError("O JSON retornado não corresponde ao schema esperado.") from erro
