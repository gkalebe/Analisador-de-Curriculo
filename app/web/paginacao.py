"""
Padrão único de paginação das listagens (GET /analises, /api/vagas, /painel/historico, /simulador).

- Query params: `limit` (1..LIMITE_MAXIMO, opcional) e `offset` (>= 0, padrão 0).
- Sem `limit`, a listagem devolve todos os itens a partir de `offset` — o comportamento
  anterior, para não quebrar os consumidores atuais do front.
- Toda resposta de listagem traz `paginacao: {total, limit, offset}`, onde `total` é a
  quantidade total de itens do usuário (independente de limit/offset).
"""
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel

LIMITE_MAXIMO = 100


@dataclass(frozen=True)
class ParametrosPaginacao:
    limit: int | None = None
    offset: int = 0


def get_paginacao(
    limit: int | None = Query(
        None,
        ge=1,
        le=LIMITE_MAXIMO,
        description=f"Máximo de itens por página (1-{LIMITE_MAXIMO}). Omitido: devolve todos.",
    ),
    offset: int = Query(0, ge=0, description="Quantidade de itens a pular (padrão 0)."),
) -> ParametrosPaginacao:
    return ParametrosPaginacao(limit=limit, offset=offset)


class PaginacaoMeta(BaseModel):
    total: int
    limit: int | None
    offset: int


def calcular_total(quantidade_pagina: int, paginacao: ParametrosPaginacao, contar: Callable[[], int]) -> int:
    """
    Devolve o total de itens, evitando a query de contagem quando ele já é dedutível
    da própria página (página incompleta e não vazia, ou primeira página sem limite).
    """
    pagina_incompleta = paginacao.limit is None or quantidade_pagina < paginacao.limit
    if pagina_incompleta and (quantidade_pagina > 0 or paginacao.offset == 0):
        return paginacao.offset + quantidade_pagina
    return contar()


def montar_meta(quantidade_pagina: int, paginacao: ParametrosPaginacao, contar: Callable[[], int]) -> PaginacaoMeta:
    return PaginacaoMeta(
        total=calcular_total(quantidade_pagina, paginacao, contar),
        limit=paginacao.limit,
        offset=paginacao.offset,
    )
