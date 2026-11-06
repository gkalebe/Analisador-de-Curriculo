"""US-014 — Recomendações para evidenciar competências.

Funções puras sobre o resultado (dict) da comparação currículo × vaga. A IA sugere as
orientações, mas a cobertura é garantida aqui: toda competência em lacuna (requisito
"parcial"/"nao_evidenciado" ou palavra-chave ausente) recebe ao menos uma orientação. Quando a
IA não cobre uma lacuna, entra uma orientação padrão escrita de forma condicional ("se você já
tem..."), para nunca induzir o candidato a declarar algo que não fez.
"""

import json
import re
import unicodedata

STATUS_LACUNA = ("parcial", "nao_evidenciado")
CAMPOS_EVIDENCIA = ("resumo", "experiencia_profissional", "habilidades", "formacao", "projetos")
LIMITE_ORIENTACOES = 3


def resultado_analise_como_dict(observacoes: str | None) -> dict:
    """`Analise.observacoes` guarda o JSON da análise (ou texto puro em análises legadas)."""
    try:
        dados = json.loads(observacoes or "")
    except (json.JSONDecodeError, TypeError):
        return {}
    return dados if isinstance(dados, dict) else {}


def normalizar_competencia(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s+#./-]", " ", sem_acento.casefold())).strip()


def competencias_correspondem(a: str, b: str) -> bool:
    """Casa "Docker" com "Docker", "experiência com Docker" com "Docker" etc."""
    na, nb = normalizar_competencia(a), normalizar_competencia(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    menor, maior = sorted((na, nb), key=len)
    return len(menor) >= 2 and re.search(rf"(?<!\w){re.escape(menor)}(?!\w)", maior) is not None


def texto_limpo(valor) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def identificar_lacunas(resultado: dict) -> list[dict]:
    """Requisitos não atendidos + termos ausentes que não repetem um requisito já listado."""
    lacunas: list[dict] = []
    for item in resultado.get("requisitos_avaliados") or []:
        if not isinstance(item, dict):
            continue
        competencia = texto_limpo(item.get("requisito"))
        status = item.get("status")
        if competencia and status in STATUS_LACUNA:
            lacunas.append(
                {
                    "competencia": competencia,
                    "tipo": "obrigatorio" if item.get("tipo") == "obrigatorio" else "desejavel",
                    "status": status,
                }
            )

    ausentes = (resultado.get("palavras_chave") or {}).get("ausentes") or []
    for termo in ausentes:
        termo = texto_limpo(termo)
        if not termo or any(competencias_correspondem(termo, lacuna["competencia"]) for lacuna in lacunas):
            continue
        lacunas.append({"competencia": termo, "tipo": "desejavel", "status": "nao_evidenciado"})
    return lacunas


def orientacao_padrao(competencia: str, status: str) -> str:
    if status == "parcial":
        return (
            f"Seu currículo já indica algo relacionado a {competencia}, mas sem destaque. Se você usa "
            f"{competencia} na prática, descreva em um bullet de experiência o contexto, o que você fez "
            "e o resultado, usando o termo exato da vaga."
        )
    return (
        f"Não encontramos {competencia} no seu currículo. Se você tem experiência real com {competencia} "
        "(trabalho, projeto acadêmico, freelance ou curso), inclua-a com o termo exato da vaga. Se não "
        "tiver, não inclua: veja o plano de desenvolvimento para adquirir essa competência."
    )


def _orientacoes_da_ia(item: dict) -> list[str]:
    bruto = item.get("orientacoes")
    if bruto is None:
        bruto = item.get("orientacao")
    if isinstance(bruto, str):
        bruto = [bruto]
    if not isinstance(bruto, list):
        return []
    return [texto for texto in (texto_limpo(o) for o in bruto) if texto][:LIMITE_ORIENTACOES]


def montar_recomendacoes(resultado: dict) -> list[dict]:
    """Uma recomendação por lacuna, na ordem das lacunas, com ao menos uma orientação."""
    sugeridas = [
        item for item in (resultado.get("recomendacoes_competencias") or []) if isinstance(item, dict)
    ]
    recomendacoes = []
    for lacuna in identificar_lacunas(resultado):
        da_ia = next(
            (item for item in sugeridas if competencias_correspondem(texto_limpo(item.get("competencia")), lacuna["competencia"])),
            None,
        )
        orientacoes = _orientacoes_da_ia(da_ia) if da_ia else []
        onde = texto_limpo((da_ia or {}).get("onde_evidenciar"))
        recomendacoes.append(
            {
                **lacuna,
                "orientacoes": orientacoes or [orientacao_padrao(lacuna["competencia"], lacuna["status"])],
                "onde_evidenciar": onde if onde in CAMPOS_EVIDENCIA else None,
                # Recomendação já normalizada (relida do banco) preserva a origem gravada.
                "origem": (da_ia.get("origem") if da_ia.get("origem") in ("ia", "padrao") else "ia")
                if orientacoes
                else "padrao",
            }
        )
    return recomendacoes
