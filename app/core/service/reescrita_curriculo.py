"""Reescrita determinística do currículo a partir da análise já salva — sem IA.

Quando o usuário clica em "Transformar em Template ATS", tudo que a reescrita precisa já
está no banco, em `Analise.observacoes` (ver `AnalisadorService._obter_sugestoes_mais_recentes`):

- `sugestoes_reescrita`: pares (trecho_original → versao_otimizada), com o `campo` em que o
  trecho está. Aplicamos localizando o trecho no currículo estruturado e substituindo.
- `diagnostico_ats.a_remover`: itens a tirar. Aplicamos removendo o item inteiro (uma
  formação, uma habilidade, um bullet...) quando ele corresponde ao texto indicado.

O que NÃO aplicamos de propósito, e devolvemos no relatório para o usuário decidir:

- `palavras_chave_faltantes`: inserir uma ferramenta/competência que o candidato não citou
  é inventar dado — a regra do produto é que toda sugestão precisa ser defensável em
  entrevista. Só o próprio candidato sabe o que domina.
- `a_reorganizar`: vem como orientação em texto livre ("destacar X antes de Y"), sem
  estrutura para aplicar mecanicamente.
- Um termo vago dentro de uma frase (não é um item inteiro): remover a palavra quebraria
  a frase; isso só faria sentido reescrevendo-a, o que não fazemos aqui.

Isso troca 1 requisição de IA (cara, lenta e sujeita a cota/sobrecarga) por uma operação
instantânea e previsível, cujo resultado o usuário revisa na pré-visualização.
"""

import re
from difflib import SequenceMatcher

from app.core.service.extracao_curriculo import normalizar_dados_curriculo

LIMIAR_SIMILARIDADE = 0.82

# Mesmos valores que a IA devolve em `sugestoes_reescrita[].campo` (ver
# AIServiceAdapter._montar_prompt_comparacao) → grupos de slots do currículo estruturado.
_GRUPO_POR_CAMPO = {
    "resumo": "resumo",
    "formacao": "formacao",
    "experiencia_profissional": "experiencia",
    "habilidades": "habilidades",
}

_SUBSTITUICOES_TIPOGRAFICAS = str.maketrans(
    {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "\xa0": " ", "•": " "}
)


def _normalizar(texto: str) -> str:
    texto = (texto or "").translate(_SUBSTITUICOES_TIPOGRAFICAS).lower()
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto.strip(" .;:,-\"'")


def _similaridade(a: str, b: str) -> float:
    a, b = _normalizar(a), _normalizar(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _padrao_flexivel(trecho: str) -> re.Pattern | None:
    """Regex que casa o trecho ignorando diferenças de espaçamento, caixa e tipografia
    (travessão vs hífen, aspas curvas vs retas)."""
    tokens = _normalizar(trecho).split()
    if not tokens:
        return None
    partes = []
    for token in tokens:
        escapado = re.escape(token)
        escapado = escapado.replace(r"\-", "[-—–]").replace(r"'", "['’‘]").replace(r"\"", "[\"“”]")
        partes.append(escapado)
    return re.compile(r"\s+".join(partes), re.IGNORECASE)


def _dividir_versao(versao: str, por_virgula: bool = False) -> list[str]:
    texto = versao.replace(",", "\n") if por_virgula else versao
    itens = [linha.strip(" \t-•*") for linha in texto.split("\n")]
    return [item for item in itens if item]


class _Slot:
    """Um texto editável do currículo estruturado: ou um campo string (ex.: resumo) ou um
    item de lista (ex.: um bullet de experiência), com referência direta ao container."""

    def __init__(self, grupo: str, container, chave, eh_item_lista: bool, por_virgula: bool = False):
        self.grupo = grupo
        self.container = container
        self.chave = chave
        self.eh_item_lista = eh_item_lista
        self.por_virgula = por_virgula

    @property
    def texto(self) -> str:
        return self.container[self.chave] or ""

    def substituir(self, novo_texto: str) -> None:
        if self.eh_item_lista:
            novos = _dividir_versao(novo_texto, self.por_virgula) or [""]
            self.container[self.chave : self.chave + 1] = novos
        else:
            self.container[self.chave] = novo_texto.strip()


class _Lista:
    """Uma lista inteira (bullets de uma experiência, habilidades...) para quando a IA citou
    o bloco todo como trecho original."""

    def __init__(self, grupo: str, lista: list, por_virgula: bool = False):
        self.grupo = grupo
        self.lista = lista
        self.por_virgula = por_virgula

    def textos_juntos(self) -> list[str]:
        itens = [item for item in self.lista if item]
        return [", ".join(itens), "\n".join(itens), " ".join(itens)] if itens else []

    def substituir(self, novo_texto: str) -> None:
        self.lista[:] = _dividir_versao(novo_texto, self.por_virgula)


def _enumerar_slots(dados: dict) -> tuple[list[_Slot], list[_Lista]]:
    slots: list[_Slot] = []
    listas: list[_Lista] = []

    slots.append(_Slot("resumo", dados, "resumo_profissional", False))
    slots.append(_Slot("outros", dados, "titulo_profissional", False))

    for experiencia in dados["experiencias"]:
        slots.append(_Slot("experiencia", experiencia, "cargo", False))
        slots.append(_Slot("experiencia", experiencia, "empresa", False))
        bullets = experiencia["descricao_bullets"]
        slots.extend(_Slot("experiencia", bullets, indice, True) for indice in range(len(bullets)))
        listas.append(_Lista("experiencia", bullets))

    for formacao in dados["formacao"]:
        slots.append(_Slot("formacao", formacao, "curso", False))
        slots.append(_Slot("formacao", formacao, "instituicao", False))

    habilidades = dados["habilidades_tecnicas"]
    slots.extend(_Slot("habilidades", habilidades, indice, True, por_virgula=True) for indice in range(len(habilidades)))
    listas.append(_Lista("habilidades", habilidades, por_virgula=True))

    certificacoes = dados["certificacoes"]
    slots.extend(_Slot("outros", certificacoes, indice, True) for indice in range(len(certificacoes)))
    listas.append(_Lista("outros", certificacoes))

    for secao in dados["secoes_adicionais"]:
        itens = secao["itens"]
        slots.extend(_Slot("outros", itens, indice, True) for indice in range(len(itens)))
        listas.append(_Lista("outros", itens))

    for idioma in dados["idiomas"]:
        slots.append(_Slot("outros", idioma, "idioma", False))

    return slots, listas


def _aplicar_reescrita(dados: dict, trecho: str, versao: str, campo: str | None) -> bool:
    grupo_preferido = _GRUPO_POR_CAMPO.get(campo or "")
    padrao = _padrao_flexivel(trecho)
    if padrao is None:
        return False

    # Slots/listas são re-enumerados a cada sugestão porque uma substituição anterior pode
    # ter mudado o tamanho de uma lista (um bullet virou dois).
    slots, listas = _enumerar_slots(dados)
    ordens = [grupo_preferido, None] if grupo_preferido else [None]

    for grupo in ordens:
        candidatos = [slot for slot in slots if grupo is None or slot.grupo == grupo]

        # 1) Trecho é exatamente um slot inteiro (a menos de caixa/espaços/tipografia) → troca o slot.
        for slot in candidatos:
            if slot.texto and _normalizar(slot.texto) == _normalizar(trecho):
                slot.substituir(versao)
                return True

        # 2) Trecho aparece dentro de um slot maior (uma frase do resumo) → troca só o trecho.
        #    Vem antes da comparação por similaridade: "fez coisas" dentro de "Ela fez coisas"
        #    é parecido o bastante com o slot inteiro, mas o certo é trocar só o trecho.
        for slot in candidatos:
            texto = slot.texto
            if texto and padrao.search(texto):
                novo, quantidade = padrao.subn(lambda _m: versao.strip(), texto, count=1)
                if quantidade:
                    if slot.eh_item_lista:
                        slot.substituir(novo)
                    else:
                        slot.container[slot.chave] = novo
                    return True

        # 3) Trecho é quase um slot inteiro (a IA parafraseou de leve ao citar) → troca o slot.
        for slot in candidatos:
            if slot.texto and _similaridade(slot.texto, trecho) >= LIMIAR_SIMILARIDADE:
                slot.substituir(versao)
                return True

        # 4) Trecho é um bloco inteiro (todos os bullets de uma experiência, a lista de
        #    habilidades) → troca a lista inteira pelos itens da versão otimizada.
        for lista in listas:
            if grupo is not None and lista.grupo != grupo:
                continue
            if any(_similaridade(junto, trecho) >= LIMIAR_SIMILARIDADE for junto in lista.textos_juntos()):
                lista.substituir(versao)
                return True

    return False


def _textos_do_item(valor) -> list[str]:
    """Textos pelos quais um item pode ser identificado: para um dict (formação,
    experiência, idioma), cada campo isoladamente e a descrição completa; para uma
    string, ela mesma."""
    if isinstance(valor, dict):
        campos = [v for v in valor.values() if isinstance(v, str) and v.strip()]
        return campos + [" — ".join(campos)] if campos else []
    return [str(valor)] if str(valor or "").strip() else []


def _corresponde_para_remocao(textos_item: list[str], alvo: str) -> bool:
    alvo_norm = _normalizar(alvo)
    if not alvo_norm:
        return False
    for texto in textos_item:
        item_norm = _normalizar(texto)
        if not item_norm:
            continue
        if item_norm == alvo_norm or _similaridade(texto, alvo) >= LIMIAR_SIMILARIDADE:
            return True
        # "Ensino Médio" deve remover "Ensino Médio — Escola X (2015)"; exigimos que o alvo
        # cubra uma parte relevante do item para não apagar algo só por compartilhar uma palavra.
        if alvo_norm in item_norm and len(alvo_norm) >= max(4, len(item_norm) * 0.4):
            return True
        if item_norm in alvo_norm and len(item_norm) >= 4:
            return True
    return False


def _limpar_alvo_remocao(alvo: str) -> str:
    alvo = alvo.strip().strip("\"'“”‘’")
    # "Formação: Ensino Médio" → "Ensino Médio"
    sem_rotulo = re.sub(r"^[^:]{1,40}:\s*", "", alvo)
    return (sem_rotulo or alvo).strip().strip("\"'“”‘’")


def _listas_removiveis(dados: dict) -> list[list]:
    listas: list[list] = [dados["formacao"], dados["experiencias"], dados["idiomas"]]
    listas.extend([dados["habilidades_tecnicas"], dados["certificacoes"]])
    listas.extend(experiencia["descricao_bullets"] for experiencia in dados["experiencias"])
    listas.extend(secao["itens"] for secao in dados["secoes_adicionais"])
    return listas


def _aplicar_remocao(dados: dict, alvo: str) -> bool:
    alvo = _limpar_alvo_remocao(alvo)
    removeu = False
    for lista in _listas_removiveis(dados):
        for indice in range(len(lista) - 1, -1, -1):
            if _corresponde_para_remocao(_textos_do_item(lista[indice]), alvo):
                del lista[indice]
                removeu = True
    return removeu


def _alvo_ainda_presente(dados: dict, alvo: str) -> bool:
    """Depois das reescritas, o item a remover pode já ter sumido (a versão otimizada o
    substituiu). Nesse caso a remoção está, na prática, feita."""
    padrao = _padrao_flexivel(_limpar_alvo_remocao(alvo))
    if padrao is None:
        return False
    slots, _ = _enumerar_slots(dados)
    return any(padrao.search(slot.texto) for slot in slots if slot.texto)


def aplicar_sugestoes_sem_ia(dados_atuais: dict, sugestoes: dict, texto_bruto: str = "") -> tuple[dict, dict]:
    """Aplica as sugestões da análise no currículo estruturado, sem IA.

    Retorna `(dados_reescritos, relatorio)`. O relatório diz o que foi e o que não foi
    aplicado, para o front informar o usuário:

        {
          "reescritas": {"total": 4, "aplicadas": 3, "nao_aplicadas": ["<trecho>"]},
          "remocoes": {"total": 2, "aplicadas": ["Ensino Médio"], "nao_aplicadas": ["proativo"],
                       "ja_ausentes": ["<item que nunca existiu no currículo>"]},
          "palavras_chave_faltantes": ["Docker"],   # nunca inseridas automaticamente
          "a_reorganizar": ["..."],                 # orientação, não aplicável mecanicamente
          "total_aplicadas": 4
        }
    """
    dados = normalizar_dados_curriculo(dados_atuais, texto_bruto)
    sugestoes = sugestoes or {}

    diagnostico = sugestoes.get("diagnostico_ats") or {}
    remocoes = [str(item).strip() for item in diagnostico.get("a_remover") or [] if str(item).strip()]
    # Medido ANTES das reescritas: um item a remover que já sumiu por causa de uma reescrita
    # conta como removido; um que nunca existiu no currículo não conta como nada.
    presentes_antes = {alvo: _alvo_ainda_presente(dados, alvo) for alvo in remocoes}

    reescritas = [
        s for s in sugestoes.get("sugestoes_reescrita") or [] if isinstance(s, dict) and (s.get("versao_otimizada") or "").strip()
    ]
    reescritas_nao_aplicadas: list[str] = []
    reescritas_aplicadas = 0
    for sugestao in reescritas:
        trecho = (sugestao.get("trecho_original") or "").strip()
        versao = sugestao["versao_otimizada"].strip()
        if trecho and _aplicar_reescrita(dados, trecho, versao, sugestao.get("campo")):
            reescritas_aplicadas += 1
        else:
            reescritas_nao_aplicadas.append(trecho or versao)

    remocoes_aplicadas: list[str] = []
    remocoes_nao_aplicadas: list[str] = []
    remocoes_ja_ausentes: list[str] = []
    for alvo in remocoes:
        if _aplicar_remocao(dados, alvo):
            remocoes_aplicadas.append(alvo)
        elif not presentes_antes[alvo]:
            remocoes_ja_ausentes.append(alvo)
        elif not _alvo_ainda_presente(dados, alvo):
            remocoes_aplicadas.append(alvo)
        else:
            remocoes_nao_aplicadas.append(alvo)

    relatorio = {
        "reescritas": {
            "total": len(reescritas),
            "aplicadas": reescritas_aplicadas,
            "nao_aplicadas": reescritas_nao_aplicadas,
        },
        "remocoes": {
            "total": len(remocoes) - len(remocoes_ja_ausentes),
            "aplicadas": remocoes_aplicadas,
            "nao_aplicadas": remocoes_nao_aplicadas,
            "ja_ausentes": remocoes_ja_ausentes,
        },
        "palavras_chave_faltantes": [str(p) for p in sugestoes.get("palavras_chave_faltantes") or []],
        "a_reorganizar": [str(p) for p in diagnostico.get("a_reorganizar") or []],
        "total_aplicadas": reescritas_aplicadas + len(remocoes_aplicadas),
    }
    return normalizar_dados_curriculo(dados, texto_bruto), relatorio
