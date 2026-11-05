from dataclasses import dataclass


@dataclass(frozen=True)
class PlanoCatalogo:
    codigo: str
    nome: str
    preco_centavos: int
    moeda: str
    intervalo: str
    limite_analises: int
    limite_estruturacoes: int
    limite_mensagens_chat: int
    limite_entrevistas: int
    limite_respostas_entrevista: int
    limite_curriculos: int
    creditos_orcamento: int
    creditos_analise: int

    @property
    def creditos_demais_operacoes(self) -> int:
        return self.creditos_orcamento - self.creditos_analise


PLANOS: dict[str, PlanoCatalogo] = {
    "free": PlanoCatalogo(
        codigo="free",
        nome="Gratuito",
        preco_centavos=0,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=2,
        limite_estruturacoes=1,
        limite_mensagens_chat=3,
        limite_entrevistas=0,
        limite_respostas_entrevista=0,
        limite_curriculos=100,
        creditos_orcamento=30,
        creditos_analise=21,
    ),
    "pro": PlanoCatalogo(
        codigo="pro",
        nome="PRO",
        preco_centavos=1990,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=10,
        limite_estruturacoes=2,
        limite_mensagens_chat=10,
        limite_entrevistas=1,
        limite_respostas_entrevista=5,
        limite_curriculos=100,
        creditos_orcamento=150,
        creditos_analise=105,
    ),
    "max": PlanoCatalogo(
        codigo="max",
        nome="MAX",
        preco_centavos=5490,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=28,
        limite_estruturacoes=5,
        limite_mensagens_chat=25,
        limite_entrevistas=4,
        limite_respostas_entrevista=24,
        limite_curriculos=300,
        creditos_orcamento=400,
        creditos_analise=280,
    ),
    "ultimate": PlanoCatalogo(
        codigo="ultimate",
        nome="ULTIMATE",
        preco_centavos=13990,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=65,
        limite_estruturacoes=10,
        limite_mensagens_chat=60,
        limite_entrevistas=10,
        limite_respostas_entrevista=60,
        limite_curriculos=300,
        creditos_orcamento=1000,
        creditos_analise=700,
    ),
}

PESO_CREDITOS_OPERACAO = {
    "analise_vaga": 10,
    "estruturacao_curriculo": 6,
    "mensagem_chat": 1,
    "entrevista_inicio": 4,
    "entrevista_feedback": 2,
}

OPERACOES_ANALISE = {"analise_vaga"}
LIMITES_OPERACAO = {
    "analise_vaga": "limite_analises",
    "estruturacao_curriculo": "limite_estruturacoes",
    "mensagem_chat": "limite_mensagens_chat",
    "entrevista_inicio": "limite_entrevistas",
    "entrevista_feedback": "limite_respostas_entrevista",
}


def obter_plano(codigo: str | None) -> PlanoCatalogo:
    if codigo is None:
        return PLANOS["free"]
    try:
        return PLANOS[codigo]
    except KeyError as erro:
        raise ValueError(f"Código de plano desconhecido: {codigo}") from erro
