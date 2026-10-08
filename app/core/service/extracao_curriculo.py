"""Fonte única dos dados estruturados de um currículo (extração, normalização e cache).
A reescrita com as sugestões da análise fica em `reescrita_curriculo.py` e não usa IA.

O formato persistido em `Curriculo.dados_extraidos` / `Curriculo.dados_editados` é o
`DadosCurriculoEstruturado` (ver `app/adapters/ai_service/curriculo_schema.py`) serializado
em dict, mais a chave `texto_bruto` com o texto original do currículo. Esse schema tem
experiências com bullets, formação, habilidades, idiomas, certificações e
`secoes_adicionais` para qualquer outra seção do currículo original — é o que permite ao
template ATS manter as MESMAS seções e dados do currículo enviado.

Antes, tudo era achatado em 7 strings (nome, email, telefone, resumo, formação,
experiência, habilidades): descrições de cada experiência, idiomas, certificações,
projetos etc. eram descartados já na extração e nunca chegavam ao template. Esse formato
"plano" continua existindo em dois lugares (tabela `candidato`, usada pela aba
"Currículo", e linhas antigas de `dados_extraidos`/`dados_editados` no banco), por isso
este módulo também sabe converter plano → estruturado (`estruturar_dados_planos`) e
estruturado → plano (`dados_planos_de`).
"""

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.adapters.ai_service.ai_service_adapter import (
    AIServiceAdapter,
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)
from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado

if TYPE_CHECKING:
    from app.core.persistencia.curriculo_repository import CurriculoRepository
    from app.core.persistencia.models.curriculo import Curriculo


# Campos "planos" do currículo: são as colunas da tabela `candidato` (aba "Currículo") e o
# formato antigo de `dados_extraidos`/`dados_editados`. Mantidos num único lugar para a
# conversão de/para o formato estruturado nunca divergir entre as features.
CAMPOS_CURRICULO = (
    "nome",
    "email",
    "telefone",
    "resumo",
    "formacao",
    "experiencia_profissional",
    "habilidades",
)

CAMPOS_ESTRUTURADOS = tuple(DadosCurriculoEstruturado.model_fields)

_CAMPOS_LISTA_DE_TEXTO = ("habilidades_tecnicas", "certificacoes")
_CAMPOS_LISTA_DE_OBJETOS = ("experiencias", "formacao", "idiomas", "secoes_adicionais")


def dados_curriculo_vazios(texto_bruto: str = "") -> dict:
    return DadosCurriculoEstruturado().model_dump() | {"texto_bruto": texto_bruto}


def _limpar_json_ia(texto: str | None) -> str:
    texto = (texto or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()
    return texto


def eh_formato_plano(dados: dict) -> bool:
    """Linhas antigas do banco e payloads da aba "Currículo" vêm com as 7 chaves planas,
    sem nenhuma das chaves do schema estruturado. "formacao" existe nos dois formatos,
    então não serve para distinguir."""
    exclusivas_estruturado = set(CAMPOS_ESTRUTURADOS) - {"formacao"}
    exclusivas_plano = set(CAMPOS_CURRICULO) - {"formacao"}
    if any(campo in dados for campo in exclusivas_estruturado):
        return False
    return any(campo in dados for campo in exclusivas_plano)


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (list, tuple)):
        return "\n".join(_texto(item) for item in valor if _texto(item))
    if isinstance(valor, dict):
        return " — ".join(str(v).strip() for v in valor.values() if v is not None and str(v).strip())
    return str(valor).strip()


def _lista_de_textos(valor, separar_virgulas: bool = False) -> list[str]:
    """Uma lista de strings vinda da IA/banco; se vier uma string única, divide por linha
    (e por vírgula só quando pedido — habilidades costumam vir "Python, SQL, Docker")."""
    if valor is None:
        return []
    if isinstance(valor, str):
        texto = valor.replace(",", "\n") if separar_virgulas else valor
        return _dividir_linhas(texto)
    if isinstance(valor, (list, tuple)):
        return [_texto(item) for item in valor if _texto(item)]
    return [_texto(valor)] if _texto(valor) else []


def _lista_de_objetos(valor, campo_principal: str) -> list[dict]:
    """A IA às vezes devolve uma string (ou lista de strings) onde o schema pede uma lista
    de objetos. Em vez de descartar o conteúdo, cada item vira um objeto só com o campo
    principal preenchido — perder dados do currículo é pior do que um item sem subcampos."""
    if valor is None:
        return []
    if isinstance(valor, dict):
        return [valor]
    if isinstance(valor, str):
        return [{campo_principal: item} for item in _lista_de_textos(valor)]
    if isinstance(valor, (list, tuple)):
        itens = []
        for item in valor:
            if isinstance(item, dict):
                itens.append(item)
            elif _texto(item):
                itens.append({campo_principal: _texto(item)})
        return itens
    return []


def _coagir_para_schema(dados: dict) -> dict:
    coagido: dict = {}
    for campo in ("nome_completo", "titulo_profissional", "resumo_profissional"):
        coagido[campo] = _texto(dados.get(campo))

    contato = dados.get("contato")
    if not isinstance(contato, dict):
        contato = {}
    coagido["contato"] = {
        chave: _texto(contato.get(chave) if chave in contato else dados.get(chave))
        for chave in ("email", "telefone", "linkedin", "cidade")
    }

    coagido["habilidades_tecnicas"] = _lista_de_textos(dados.get("habilidades_tecnicas"), separar_virgulas=True)
    coagido["certificacoes"] = _lista_de_textos(dados.get("certificacoes"))

    coagido["experiencias"] = [
        {
            "cargo": _texto(item.get("cargo")),
            "empresa": _texto(item.get("empresa")),
            "periodo_inicio": _texto(item.get("periodo_inicio")),
            "periodo_fim": _texto(item.get("periodo_fim")),
            "descricao_bullets": _lista_de_textos(item.get("descricao_bullets")),
        }
        for item in _lista_de_objetos(dados.get("experiencias"), "cargo")
    ]
    coagido["formacao"] = [
        {
            "curso": _texto(item.get("curso")),
            "instituicao": _texto(item.get("instituicao")),
            "periodo": _texto(item.get("periodo")),
        }
        for item in _lista_de_objetos(dados.get("formacao"), "curso")
    ]
    coagido["idiomas"] = [
        {"idioma": _texto(item.get("idioma")), "nivel": _texto(item.get("nivel"))}
        for item in _lista_de_objetos(dados.get("idiomas"), "idioma")
    ]
    coagido["secoes_adicionais"] = [
        {"titulo": _texto(item.get("titulo")), "itens": _lista_de_textos(item.get("itens"))}
        for item in _lista_de_objetos(dados.get("secoes_adicionais"), "titulo")
        if _texto(item.get("titulo")) or _lista_de_textos(item.get("itens"))
    ]
    return coagido


def estruturar_dados_planos(dados_planos: dict) -> dict:
    """Converte o formato plano (7 campos) para o schema estruturado.

    Usado para linhas antigas do banco, para currículos criados manualmente na aba
    "Currículo" (que só existem na tabela `candidato`) e para a edição estruturada por
    campo. Cada linha de "formacao"/"experiencia_profissional" vira um item; habilidades
    são separadas por vírgula ou quebra de linha."""
    dados_planos = dados_planos or {}
    return {
        "nome_completo": _texto(dados_planos.get("nome")),
        "titulo_profissional": "",
        "contato": {
            "email": _texto(dados_planos.get("email")),
            "telefone": _texto(dados_planos.get("telefone")),
            "linkedin": "",
            "cidade": "",
        },
        "resumo_profissional": _texto(dados_planos.get("resumo")),
        "experiencias": [
            {"cargo": linha} for linha in _dividir_linhas(_texto(dados_planos.get("experiencia_profissional")))
        ],
        "formacao": [{"curso": linha} for linha in _dividir_linhas(_texto(dados_planos.get("formacao")))],
        "habilidades_tecnicas": _lista_de_textos(dados_planos.get("habilidades"), separar_virgulas=True),
        "idiomas": [],
        "certificacoes": [],
        "secoes_adicionais": [],
    }


def _dividir_linhas(texto: str) -> list[str]:
    return [linha.strip(" \t-•*") for linha in texto.split("\n") if linha.strip(" \t-•*")]


def _formatar_experiencia(experiencia: dict) -> list[str]:
    cabecalho = " — ".join(parte for parte in (experiencia.get("cargo"), experiencia.get("empresa")) if parte)
    periodo = " - ".join(parte for parte in (experiencia.get("periodo_inicio"), experiencia.get("periodo_fim")) if parte)
    if periodo:
        cabecalho = f"{cabecalho} ({periodo})" if cabecalho else periodo
    linhas = [cabecalho] if cabecalho else []
    linhas.extend(f"  - {bullet}" for bullet in experiencia.get("descricao_bullets") or [])
    return linhas


def _formatar_formacao(formacao: dict) -> str:
    cabecalho = " — ".join(parte for parte in (formacao.get("curso"), formacao.get("instituicao")) if parte)
    if formacao.get("periodo"):
        cabecalho = f"{cabecalho} ({formacao['periodo']})" if cabecalho else formacao["periodo"]
    return cabecalho


def dados_planos_de(dados: dict) -> dict:
    """Projeta o schema estruturado nos 7 campos planos da tabela `candidato`
    (aba "Currículo"). É uma projeção com perda — por isso nunca é usada como fonte
    para exportação quando os dados estruturados existem."""
    dados = dados or {}
    contato = dados.get("contato") or {}
    linhas_experiencia: list[str] = []
    for experiencia in dados.get("experiencias") or []:
        linhas_experiencia.extend(_formatar_experiencia(experiencia))
    return {
        "nome": dados.get("nome_completo") or "",
        "email": contato.get("email") or "",
        "telefone": contato.get("telefone") or "",
        "resumo": dados.get("resumo_profissional") or "",
        "formacao": "\n".join(linha for linha in (_formatar_formacao(f) for f in dados.get("formacao") or []) if linha),
        "experiencia_profissional": "\n".join(linhas_experiencia),
        "habilidades": ", ".join(dados.get("habilidades_tecnicas") or []),
    }


def mesclar_dados_planos(dados_estruturados: dict, dados_planos: dict, texto_bruto: str = "") -> dict:
    """Aplica uma edição feita nos 7 campos planos (aba "Currículo") por cima dos dados
    estruturados SEM descartar o que a edição plana não representa (bullets das
    experiências, idiomas, certificações, seções adicionais...).

    Só os campos planos cujo valor mudou em relação à projeção atual são substituídos;
    os demais ficam exatamente como estavam. Campos ausentes/None no payload são
    ignorados (não contam como "apagar")."""
    base = normalizar_dados_curriculo(dados_estruturados, texto_bruto)
    projecao_atual = dados_planos_de(base)
    alterados = {
        campo: _texto(valor)
        for campo, valor in (dados_planos or {}).items()
        if campo in CAMPOS_CURRICULO and valor is not None and _texto(valor) != projecao_atual[campo]
    }
    if not alterados:
        return base

    novos = estruturar_dados_planos(projecao_atual | alterados)
    if "nome" in alterados:
        base["nome_completo"] = novos["nome_completo"]
    if "email" in alterados:
        base["contato"]["email"] = novos["contato"]["email"]
    if "telefone" in alterados:
        base["contato"]["telefone"] = novos["contato"]["telefone"]
    if "resumo" in alterados:
        base["resumo_profissional"] = novos["resumo_profissional"]
    if "formacao" in alterados:
        base["formacao"] = novos["formacao"]
    if "experiencia_profissional" in alterados:
        base["experiencias"] = novos["experiencias"]
    if "habilidades" in alterados:
        base["habilidades_tecnicas"] = novos["habilidades_tecnicas"]
    return base


def normalizar_dados_curriculo(dados: dict | None, texto_bruto: str = "") -> dict:
    """Garante que um dict (do banco, da IA ou de um payload) tenha exatamente o shape de
    `DadosCurriculoEstruturado` + `texto_bruto`. Aceita também o formato plano antigo.

    Levanta `ValueError` se, mesmo depois da coerção, o conteúdo não couber no schema —
    quem chama decide se cai para dados vazios (extração) ou propaga (aplicar sugestões)."""
    dados = dict(dados or {})
    texto_proprio = dados.pop("texto_bruto", None)
    if eh_formato_plano(dados):
        dados = estruturar_dados_planos(dados)
    try:
        validado = DadosCurriculoEstruturado.model_validate(_coagir_para_schema(dados))
    except ValidationError as erro:
        raise ValueError("Dados do currículo fora do formato esperado.") from erro
    return validado.model_dump() | {"texto_bruto": texto_proprio or texto_bruto}


def _interpretar_json_ia(resultado_ia: str | None) -> dict | None:
    try:
        dados_ia = json.loads(_limpar_json_ia(resultado_ia))
    except (json.JSONDecodeError, TypeError):
        return None
    return dados_ia if isinstance(dados_ia, dict) else None


def extrair_dados_estruturados_curriculo(ai_service_adapter: AIServiceAdapter, texto_extraido: str) -> dict:
    """
    Usa a IA para transformar o texto bruto extraído de um currículo no schema estruturado
    completo (contato, resumo, experiências com bullets, formação, habilidades, idiomas,
    certificações e seções adicionais). Em caso de indisponibilidade/erro de configuração
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

    dados_ia = _interpretar_json_ia(resultado_ia)
    if dados_ia is None:
        return dados_curriculo_vazios(texto_extraido)

    try:
        return normalizar_dados_curriculo(dados_ia, texto_extraido)
    except ValueError:
        return dados_curriculo_vazios(texto_extraido)


def dados_tem_conteudo(dados: dict) -> bool:
    dados = dados or {}
    if any((dados.get(campo) or "").strip() for campo in ("nome_completo", "titulo_profissional", "resumo_profissional")):
        return True
    if any((dados.get("contato") or {}).get(chave) for chave in ("email", "telefone", "linkedin", "cidade")):
        return True
    return any(dados.get(campo) for campo in _CAMPOS_LISTA_DE_TEXTO + _CAMPOS_LISTA_DE_OBJETOS)


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

    Linhas antigas no formato plano são convertidas para o schema estruturado na
    leitura (sem reescrever o banco).
    """
    texto_bruto = curriculo.texto_extraido or ""
    if curriculo.dados_editados:
        return normalizar_dados_curriculo(curriculo.dados_editados, texto_bruto)

    if curriculo.dados_extraidos:
        return normalizar_dados_curriculo(curriculo.dados_extraidos, texto_bruto)

    dados = extrair_dados_estruturados_curriculo(ai_service_adapter, texto_bruto)
    if dados_tem_conteudo(dados):
        curriculo_repository.salvar_dados_extraidos(curriculo, dados)
    return dados
