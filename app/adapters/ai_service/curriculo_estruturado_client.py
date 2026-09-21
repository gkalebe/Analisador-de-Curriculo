"""Etapa 1 do pipeline: geração de conteúdo estruturado via IA (Gemini).

Por que esta etapa é isolada das outras 2: é a ÚNICA parte do pipeline que
fala com um provedor de IA. Se o Gemini sair do ar, mudar de preço, ou o time
decidir trocar de provedor, só este arquivo muda — a validação (Etapa 2) e a
montagem do documento (Etapa 3) continuam funcionando exatamente iguais,
porque as duas só conhecem o contrato Pydantic (`curriculo_schema.py`), nunca
a API do Gemini.

A IA aqui NUNCA gera o documento final nem texto já formatado: ela só devolve
um JSON validado contra `DadosCurriculoEstruturado` (JSON mode + response
schema da própria API do Gemini, que restringe a resposta no nível da API —
não é um "por favor responda em JSON" no prompt, que a IA pode ignorar). Isso
é o que elimina o corte/perda de informação: o texto que sai da IA é só dado
estruturado, nunca prosa que outra etapa precise "encaixar" num template.
"""

import json

from pydantic import BaseModel, ValidationError

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado
from app.core.config import get_settings

TIMEOUT_SEGUNDOS = 45

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


def _schema_compativel_com_gemini(modelo: type[BaseModel]) -> dict:
    """Converte um schema Pydantic para o dict de schema que a API do Gemini
    (`google-generativeai`) aceita como `response_schema`.

    `model_json_schema()` do Pydantic v2 gera chaves ("default", "title") e
    referências ("$ref"/"$defs" para os submodelos aninhados, como
    `ContatoCurriculo` e `ExperienciaCurriculo`) que o conversor de schema
    desta versão do SDK do Gemini não entende — falha com
    `ValueError: Unknown field for Schema: default`. Por isso resolvemos as
    referências (inline) e removemos as chaves não suportadas antes de
    enviar, ficando só com o que o `protos.Schema` do Gemini aceita (type,
    properties, items, required, enum, description).
    """
    schema_bruto = modelo.model_json_schema()
    definicoes = schema_bruto.get("$defs", {})
    chaves_nao_suportadas = {"default", "title", "$defs", "additionalProperties"}

    def resolver(no):
        if isinstance(no, dict):
            if "$ref" in no:
                nome_ref = no["$ref"].rsplit("/", 1)[-1]
                return resolver(definicoes[nome_ref])
            return {chave: resolver(valor) for chave, valor in no.items() if chave not in chaves_nao_suportadas}
        if isinstance(no, list):
            return [resolver(item) for item in no]
        return no

    return resolver(schema_bruto)


class IARespostaInvalidaError(Exception):
    """JSON malformado ou que não corresponde ao schema, mesmo vindo da API."""


class _CampoUnico(BaseModel):
    """Schema mínimo usado só no retry cirúrgico de um campo — não herda de
    `DadosCurriculoEstruturado` de propósito, para a resposta da IA vir com
    um único campo, mantendo o retry barato."""

    valor: str = ""


class GeradorCurriculoEstruturadoIA:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name if model_name is not None else settings.gemini_model_name

    def gerar(self, informacoes_brutas: str) -> DadosCurriculoEstruturado:
        """Gera o JSON estruturado completo a partir das informações brutas.

        Levanta `IAConfiguracaoAusenteError` (sem API key), `IAIndisponivelError`
        (Gemini fora do ar/timeout) ou `IARespostaInvalidaError` (resposta que
        não é um JSON válido ou não bate com o schema).
        """
        texto_resposta = self._chamar_gemini(PROMPT_SISTEMA + informacoes_brutas, DadosCurriculoEstruturado)
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
        texto_resposta = self._chamar_gemini(prompt, _CampoUnico)
        dados_campo = self._parsear_resposta(texto_resposta, _CampoUnico)
        return dados_campo.valor

    def _chamar_gemini(self, prompt: str, response_schema: type[BaseModel]) -> str:
        if not self.api_key:
            raise IAConfiguracaoAusenteError("Defina GEMINI_API_KEY no .env para gerar currículos estruturados.")

        import google.api_core.exceptions
        import google.generativeai as genai

        genai.configure(api_key=self.api_key, transport="rest")
        modelo = genai.GenerativeModel(self.model_name)
        configuracao_geracao = genai.types.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_schema_compativel_com_gemini(response_schema),
        )
        try:
            resposta = modelo.generate_content(
                prompt,
                generation_config=configuracao_geracao,
                request_options={"timeout": TIMEOUT_SEGUNDOS},
            )
        except google.api_core.exceptions.GoogleAPICallError as erro:
            raise IAIndisponivelError(
                f"O serviço de IA (Gemini) não respondeu em {TIMEOUT_SEGUNDOS}s ou recusou a requisição. "
                "Tente novamente em instantes."
            ) from erro
        return resposta.text

    def _parsear_resposta(self, texto_resposta: str, schema: type[BaseModel]) -> BaseModel:
        try:
            dados_brutos = json.loads(texto_resposta)
        except (json.JSONDecodeError, TypeError) as erro:
            raise IARespostaInvalidaError("A IA não retornou um JSON válido.") from erro
        try:
            return schema.model_validate(dados_brutos)
        except ValidationError as erro:
            raise IARespostaInvalidaError(f"O JSON retornado não corresponde ao schema esperado: {erro}") from erro
