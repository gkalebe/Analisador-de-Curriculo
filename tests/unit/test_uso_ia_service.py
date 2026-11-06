import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from fastapi.testclient import TestClient

from app.core.persistencia.uso_ia_repository import JanelaCobrancaExpiradaError, LimiteUsoIAExcedidoError
from app.core.service.catalogo_planos import PLANOS, PESO_CREDITOS_OPERACAO
from app.core.service.uso_ia_service import (
    CotaIAExcedidaError,
    CotaIATemporariamenteIndisponivelError,
    UsoIAService,
)
from app.main import app


@pytest.mark.parametrize("plano", PLANOS.values())
def test_catalogo_reserva_cerca_de_setenta_por_cento_do_orcamento_para_analises(plano):
    assert plano.creditos_analise / plano.creditos_orcamento == pytest.approx(0.7)


def test_pesos_de_operacao_cobrem_chat_entrevista_e_estrutura_curriculo():
    assert PESO_CREDITOS_OPERACAO == {
        "analise_vaga": 10,
        "estruturacao_curriculo": 6,
        "mensagem_chat": 1,
        "entrevista_inicio": 4,
        "entrevista_feedback": 2,
    }


def test_catalogo_http_exibe_preco_e_cotas_atualizados():
    resposta = TestClient(app).get("/assinaturas/planos")

    assert resposta.status_code == 200
    planos = {plano["codigo"]: plano for plano in resposta.json()["planos"]}
    assert planos["pro"]["preco_centavos"] == 1990
    assert planos["max"]["preco_centavos"] == 5490
    assert planos["ultimate"]["preco_centavos"] == 13990
    assert planos["pro"]["limite_mensagens_chat"] == 100
    assert planos["pro"]["limite_entrevistas"] == 3


def test_reserva_sucesso_finaliza_uso_como_consumido():
    service = UsoIAService(db=None)
    reserva = SimpleNamespace(id_uso=uuid.uuid4(), estado="reservado")
    service.repository = MagicMock()
    service.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="pro")
    service.repository.listar_usos_ativos.return_value = []
    service.repository.reservar.return_value = reserva

    with service.reservar(uuid.uuid4(), "mensagem_chat"):
        pass

    service.repository.finalizar.assert_called_once_with(reserva.id_uso, "consumido")


def test_falha_na_operacao_libera_reserva_e_propaga_erro():
    service = UsoIAService(db=None)
    reserva = SimpleNamespace(id_uso=uuid.uuid4(), estado="reservado")
    service.repository = MagicMock()
    service.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="pro")
    service.repository.listar_usos_ativos.return_value = []
    service.repository.reservar.return_value = reserva
    erro = RuntimeError("falha simulada")

    with pytest.raises(RuntimeError, match="falha simulada"):
        with service.reservar(uuid.uuid4(), "mensagem_chat"):
            raise erro

    service.repository.finalizar.assert_called_once_with(reserva.id_uso, "liberado")


def test_limite_excedido_expõe_tipo_de_operacao_e_renovacao():
    service = UsoIAService(db=None)
    renovacao = datetime.now(timezone.utc)
    service.repository = MagicMock()
    service.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="free")
    service.repository.reservar.side_effect = LimiteUsoIAExcedidoError("entrevista_inicio", renovacao)

    with pytest.raises(CotaIAExcedidaError) as erro:
        with service.reservar(uuid.uuid4(), "entrevista_inicio"):
            pytest.fail("A chamada de IA não deveria iniciar.")

    assert erro.value.tipo_operacao == "entrevista_inicio"
    assert erro.value.renovacao_em == renovacao


def test_ciclo_stripe_expirado_bloqueia_ia_ate_webhook_de_renovacao():
    service = UsoIAService(db=None)
    service.repository = MagicMock()
    service.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="pro")
    service.repository.reservar.side_effect = JanelaCobrancaExpiradaError

    with pytest.raises(CotaIATemporariamenteIndisponivelError):
        with service.reservar(uuid.uuid4(), "mensagem_chat"):
            pytest.fail("A chamada de IA não deveria iniciar.")


@pytest.mark.parametrize("plano", PLANOS.values())
def test_orcamento_de_creditos_comporta_todas_as_cotas_do_plano(plano):
    demais = (
        plano.limite_estruturacoes * PESO_CREDITOS_OPERACAO["estruturacao_curriculo"]
        + plano.limite_mensagens_chat * PESO_CREDITOS_OPERACAO["mensagem_chat"]
        + plano.limite_entrevistas * PESO_CREDITOS_OPERACAO["entrevista_inicio"]
        + plano.limite_respostas_entrevista * PESO_CREDITOS_OPERACAO["entrevista_feedback"]
    )
    assert plano.limite_analises * PESO_CREDITOS_OPERACAO["analise_vaga"] <= plano.creditos_analise
    assert demais <= plano.creditos_demais_operacoes
