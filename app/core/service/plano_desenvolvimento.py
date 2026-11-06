"""US-015 — Plano de desenvolvimento e certificações sugeridas.

Para cada requisito não atendido (as mesmas lacunas da US-014) o plano traz uma trilha de
estudo e, quando a IA indicar, certificações reconhecidas. Sem trilha da IA, entra uma trilha
padrão — assim todo requisito não atendido sempre tem uma sugestão. Sem lacunas, o plano
informa isso e mantém apenas as certificações opcionais.
"""

from app.core.service.recomendacoes_competencias import (
    competencias_correspondem,
    texto_limpo,
    identificar_lacunas,
    normalizar_competencia,
)

PRIORIDADES = ("alta", "media", "baixa")
LIMITE_CERTIFICACOES = 3
LIMITE_PASSOS_TRILHA = 5
LIMITE_CERTIFICACOES_OPCIONAIS = 6
MENSAGEM_SEM_LACUNAS = (
    "Seu currículo atende a todos os requisitos identificados nesta vaga. As certificações abaixo "
    "são opcionais e servem para se diferenciar."
)
MENSAGEM_COM_LACUNAS = "Siga as trilhas abaixo, começando pelas prioridades altas, para aumentar sua aderência."


def prioridade_padrao(tipo: str, status: str) -> str:
    if tipo == "obrigatorio":
        return "alta" if status == "nao_evidenciado" else "media"
    return "media" if status == "nao_evidenciado" else "baixa"


def trilha_padrao(competencia: str) -> list[str]:
    return [
        f"Estude os fundamentos de {competencia} em um curso introdutório ou na documentação oficial.",
        f"Aplique {competencia} em um projeto prático e publique o resultado no GitHub ou portfólio.",
        f"Depois de praticar, inclua o projeto no currículo citando {competencia} com o termo exato da vaga.",
    ]


def _certificacoes(bruto, limite: int = LIMITE_CERTIFICACOES) -> list[dict]:
    certificacoes = []
    vistos = set()
    for item in bruto if isinstance(bruto, list) else []:
        if isinstance(item, str):
            item = {"nome": item}
        if not isinstance(item, dict):
            continue
        nome = texto_limpo(item.get("nome"))
        chave = normalizar_competencia(nome)
        if not nome or chave in vistos:
            continue
        vistos.add(chave)
        certificacoes.append(
            {"nome": nome, "emissor": texto_limpo(item.get("emissor")), "motivo": texto_limpo(item.get("motivo"))}
        )
        if len(certificacoes) == limite:
            break
    return certificacoes


def _trilha(bruto) -> list[str]:
    if not isinstance(bruto, list):
        return []
    return [passo for passo in (texto_limpo(p) for p in bruto) if passo][:LIMITE_PASSOS_TRILHA]


def montar_plano_desenvolvimento(resultado: dict) -> dict:
    plano_ia = resultado.get("plano_desenvolvimento")
    plano_ia = plano_ia if isinstance(plano_ia, dict) else {}
    itens_ia = [item for item in plano_ia.get("itens") or [] if isinstance(item, dict)]

    itens = []
    for lacuna in identificar_lacunas(resultado):
        da_ia = next(
            (item for item in itens_ia if competencias_correspondem(texto_limpo(item.get("competencia")), lacuna["competencia"])),
            {},
        )
        trilha = _trilha(da_ia.get("trilha"))
        prioridade = da_ia.get("prioridade")
        itens.append(
            {
                **lacuna,
                "prioridade": prioridade
                if prioridade in PRIORIDADES
                else prioridade_padrao(lacuna["tipo"], lacuna["status"]),
                "certificacoes": _certificacoes(da_ia.get("certificacoes")),
                "trilha": trilha or trilha_padrao(lacuna["competencia"]),
                # Plano já normalizado (relido do banco) preserva a origem gravada.
                "origem": (da_ia.get("origem") if da_ia.get("origem") in ("ia", "padrao") else "ia")
                if trilha
                else "padrao",
            }
        )
    itens.sort(key=lambda item: PRIORIDADES.index(item["prioridade"]))

    return {
        "sem_lacunas": not itens,
        "mensagem": MENSAGEM_COM_LACUNAS if itens else MENSAGEM_SEM_LACUNAS,
        "itens": itens,
        "certificacoes_opcionais": _certificacoes(
            plano_ia.get("certificacoes_opcionais"), LIMITE_CERTIFICACOES_OPCIONAIS
        ),
    }


def consolidar_planos(planos_por_analise: list[tuple[dict, dict]]) -> dict:
    """Junta os planos de várias análises (mais recente primeiro) no dashboard do usuário.

    `planos_por_analise` é uma lista de (referência da análise, plano). A mesma competência
    pedida em várias vagas vira um item só, com a maior prioridade e a lista de vagas.
    """
    por_competencia: dict[str, dict] = {}
    opcionais: list[dict] = []
    for referencia, plano in planos_por_analise:
        for item in plano["itens"]:
            chave = normalizar_competencia(item["competencia"])
            atual = por_competencia.get(chave)
            if atual is None:
                por_competencia[chave] = {**item, "vagas": [referencia]}
                continue
            atual["vagas"].append(referencia)
            if PRIORIDADES.index(item["prioridade"]) < PRIORIDADES.index(atual["prioridade"]):
                atual["prioridade"] = item["prioridade"]
            if item["tipo"] == "obrigatorio":
                atual["tipo"] = "obrigatorio"
            if item["status"] == "nao_evidenciado":
                atual["status"] = "nao_evidenciado"
            if not atual["certificacoes"] and item["certificacoes"]:
                atual["certificacoes"] = item["certificacoes"]
            if atual["origem"] == "padrao" and item["origem"] == "ia":
                atual["trilha"], atual["origem"] = item["trilha"], "ia"
        opcionais.extend(plano["certificacoes_opcionais"])

    itens = sorted(
        por_competencia.values(),
        key=lambda item: (PRIORIDADES.index(item["prioridade"]), -len(item["vagas"])),
    )
    resumo = {prioridade: sum(1 for item in itens if item["prioridade"] == prioridade) for prioridade in PRIORIDADES}
    return {
        "total_analises": len(planos_por_analise),
        "sem_analises": not planos_por_analise,
        "sem_lacunas": bool(planos_por_analise) and not itens,
        "mensagem": MENSAGEM_COM_LACUNAS if itens else MENSAGEM_SEM_LACUNAS if planos_por_analise else "",
        "resumo": {**resumo, "total": len(itens)},
        "itens": [{**item, "frequencia": len(item["vagas"])} for item in itens],
        "certificacoes_opcionais": _certificacoes(opcionais, LIMITE_CERTIFICACOES_OPCIONAIS),
    }
