import pytest

from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _desativar_rate_limit():
    """
    Desliga o rate limiting (login, cadastro, recuperar-senha) durante os testes.

    O limiter usa armazenamento em memória por processo, então sem isso as chamadas de
    TODOS os testes que batem nesses endpoints (em qualquer arquivo) somam na mesma
    contagem. Hoje a suíte fica dentro do limite, mas à medida que mais testes forem
    adicionados a suíte ficaria frágil — os últimos testes de cada execução passariam
    a tomar 429 mesmo estando corretos, um falso negativo silencioso e difícil de
    depurar. Desligado aqui; a proteção real segue ativa em produção.
    """
    limiter.enabled = False
    yield
    limiter.enabled = True
