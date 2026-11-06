from app.web.paginacao import ParametrosPaginacao, calcular_total


def _contagem_proibida():
    raise AssertionError("a contagem não deveria ser consultada")


def test_sem_limit_total_e_o_tamanho_da_lista():
    assert calcular_total(3, ParametrosPaginacao(), _contagem_proibida) == 3


def test_pagina_incompleta_deduz_total_sem_contar():
    assert calcular_total(2, ParametrosPaginacao(limit=5, offset=10), _contagem_proibida) == 12


def test_pagina_cheia_consulta_contagem():
    assert calcular_total(5, ParametrosPaginacao(limit=5, offset=0), lambda: 42) == 42


def test_pagina_vazia_alem_do_fim_consulta_contagem():
    assert calcular_total(0, ParametrosPaginacao(limit=5, offset=50), lambda: 7) == 7
