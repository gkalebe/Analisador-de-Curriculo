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
    limite_curriculos: int
    creditos_orcamento: int
    creditos_analise: int

    @property
    def creditos_demais_operacoes(self) -> int:
        return self.creditos_orcamento - self.creditos_analise


# Cotas mensais por plano. Os limites por operação são o teto que o usuário enxerga; o
# orçamento de créditos (70% reservado para análises) é uma trava de custo de IA e foi
# dimensionado para comportar o uso máximo de todas as operações do plano.
PLANOS: dict[str, PlanoCatalogo] = {
    "free": PlanoCatalogo(
        codigo="free",
        nome="Gratuito",
        preco_centavos=0,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=3,
        limite_estruturacoes=1,
        limite_mensagens_chat=20,
        limite_entrevistas=0,
        limite_curriculos=3,
        creditos_orcamento=140,
        creditos_analise=98,
    ),
    "pro": PlanoCatalogo(
        codigo="pro",
        nome="PRO",
        preco_centavos=1999,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=20,
        limite_estruturacoes=4,
        limite_mensagens_chat=100,
        limite_entrevistas=5,
        limite_curriculos=15,
        creditos_orcamento=660,
        creditos_analise=462,
    ),
    "max": PlanoCatalogo(
        codigo="max",
        nome="MAX",
        preco_centavos=5499,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=60,
        limite_estruturacoes=10,
        limite_mensagens_chat=300,
        limite_entrevistas=15,
        limite_curriculos=50,
        creditos_orcamento=1850,
        creditos_analise=1295,
    ),
    "ultimate": PlanoCatalogo(
        codigo="ultimate",
        nome="ULTIMATE",
        preco_centavos=13999,
        moeda="BRL",
        intervalo="mensal",
        limite_analises=160,
        limite_estruturacoes=25,
        limite_mensagens_chat=800,
        limite_entrevistas=30,
        limite_curriculos=150,
        creditos_orcamento=4800,
        creditos_analise=3360,
    ),
}

PESO_CREDITOS_OPERACAO = {
    "analise_vaga": 10,
    "estruturacao_curriculo": 6,
    "mensagem_chat": 1,
    "entrevista_inicio": 2,
    "entrevista_avaliacao": 2,
}

OPERACOES_ANALISE = {"analise_vaga"}
LIMITES_OPERACAO = {
    "analise_vaga": "limite_analises",
    "estruturacao_curriculo": "limite_estruturacoes",
    "mensagem_chat": "limite_mensagens_chat",
    "entrevista_inicio": "limite_entrevistas",
    # Mesmo teto de `entrevista_inicio` dentro do ciclo vigente. Contabilizada separadamente no
    # envio das respostas (entrevistas iniciadas num ciclo anterior e avaliadas no atual usam a
    # cota de avaliação do ciclo atual).
    "entrevista_avaliacao": "limite_entrevistas",
}


def obter_plano(codigo: str | None) -> PlanoCatalogo:
    if codigo is None:
        return PLANOS["free"]
    try:
        return PLANOS[codigo]
    except KeyError as erro:
        raise ValueError(f"Código de plano desconhecido: {codigo}") from erro
