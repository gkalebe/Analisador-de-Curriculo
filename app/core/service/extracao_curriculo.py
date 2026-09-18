import json

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)

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
