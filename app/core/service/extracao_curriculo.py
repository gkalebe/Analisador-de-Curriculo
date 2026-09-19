import json
from typing import TYPE_CHECKING

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)

if TYPE_CHECKING:
    from app.core.persistencia.curriculo_repository import CurriculoRepository
    from app.core.persistencia.models.curriculo import Curriculo

# Campos estruturados de currículo compartilhados entre a exportação de templates e a
# edição de currículo — mantidos num único lugar para as duas features nunca divergirem.
CAMPOS_CURRICULO = (
    "nome",
    "email",
    "telefone",
    "resumo",
    "formacao",
    "experiencia_profissional",
    "habilidades",
)


def dados_curriculo_vazios(texto_bruto: str = "") -> dict:
    return {campo: "" for campo in CAMPOS_CURRICULO} | {"texto_bruto": texto_bruto}


def extrair_dados_estruturados_curriculo(ai_service_adapter: AIServiceAdapter, texto_extraido: str) -> dict:
    """
    Usa a IA para transformar o texto bruto extraído de um currículo em campos estruturados
    (nome, email, formação, experiência etc). Em caso de indisponibilidade/erro de configuração
    da IA ou resposta não interpretável, cai de volta nos campos vazios com texto_bruto
    preenchido, para a exportação/edição nunca quebrar por causa de uma falha externa.
    """
    texto_extraido = texto_extraido or ""
    if not texto_extraido.strip():
        return dados_curriculo_vazios(texto_extraido)

    try:
        resultado_ia = ai_service_adapter.extrair_dados_estruturados(texto_extraido)
    except (IAConfiguracaoAusenteError, IAIndisponivelError):
        return dados_curriculo_vazios(texto_extraido)

    texto = (resultado_ia or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    try:
        dados_ia = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return dados_curriculo_vazios(texto_extraido)

    if not isinstance(dados_ia, dict):
        return dados_curriculo_vazios(texto_extraido)

    return {campo: str(dados_ia.get(campo) or "") for campo in CAMPOS_CURRICULO} | {"texto_bruto": texto_extraido}


def normalizar_dados_editados(dados_editados: dict, texto_bruto: str = "") -> dict:
    """Garante que um dict de dados_editados (vindo do banco) tenha exatamente o shape esperado."""
    dados_editados = dados_editados or {}
    return {campo: str(dados_editados.get(campo) or "") for campo in CAMPOS_CURRICULO} | {
        "texto_bruto": dados_editados.get("texto_bruto") or texto_bruto
    }


def _dados_tem_conteudo(dados: dict) -> bool:
    return any((dados.get(campo) or "").strip() for campo in CAMPOS_CURRICULO)


def obter_dados_curriculo_com_cache(
    curriculo: "Curriculo",
    ai_service_adapter: AIServiceAdapter,
    curriculo_repository: "CurriculoRepository",
) -> dict:
    """
    Fonte única de dados estruturados de um currículo para edição/exportação/preview,
    nesta ordem de prioridade:

    1. `dados_editados` — edição manual do usuário (ou já com sugestões aplicadas):
       sempre vence, nunca chama IA.
    2. `dados_extraidos` — cache da extração por IA feita anteriormente para este
       currículo: reaproveitado sem nova chamada à IA.
    3. Extração nova por IA — só quando nenhum dos dois acima existe ainda. Se a
       extração tiver conteúdo de verdade, é salva em `dados_extraidos` para as
       próximas chamadas (próximo preview, próxima exportação, abrir a tela de
       edição) não dependerem da IA estar disponível de novo.

    Existe por causa de um problema real: exportar/pré-visualizar um currículo
    "original" chamava a IA a cada clique — caro, lento e frágil (uma exportação de
    documento não deveria poder falhar por causa de indisponibilidade/cota da IA).
    Compartilhada entre `TemplateService` (exportação) e `AnalisadorService` (tela de
    edição) para as duas nunca divergirem em como resolvem os dados de um currículo.
    """
    if curriculo.dados_editados:
        return normalizar_dados_editados(curriculo.dados_editados, curriculo.texto_extraido or "")

    if curriculo.dados_extraidos:
        return normalizar_dados_editados(curriculo.dados_extraidos, curriculo.texto_extraido or "")

    dados = extrair_dados_estruturados_curriculo(ai_service_adapter, curriculo.texto_extraido or "")
    if _dados_tem_conteudo(dados):
        curriculo_repository.salvar_dados_extraidos(curriculo, dados)
    return dados
