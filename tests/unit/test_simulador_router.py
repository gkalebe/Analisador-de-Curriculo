import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.adapters.ai_service.ai_service_adapter import (
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
    IARespostaInvalidaError,
)
from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista
from app.core.persistencia.models.usuario import Usuario
from app.core.persistencia.models.vaga import Vaga
from app.core.rate_limit import limiter
from app.core.service.simulador_service import (
    RespostasInvalidasError,
    SimulacaoEmAvaliacaoError,
    SimulacaoJaAvaliadaError,
    SimulacaoNaoEncontradaError,
    VagaNaoEncontradaError,
)
from app.core.service.uso_ia_service import CotaIAExcedidaError
from app.main import app
from app.web.dependencies import get_usuario_atual
from app.web.routers.simulador_router import (
    get_simulador_service,
)

client = TestClient(app)


def _usuario(id_usuario=None):
    return Usuario(
        id_usuario=id_usuario or uuid.uuid4(),
        nome="Teste",
        email="teste@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_iniciar_simulacao_usuario_nao_encontrado():
    try:
        response = client.post(
            "/simulador/iniciar",
            json={"email": "desconhecido@example.com", "id_vaga": str(uuid.uuid4())},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        app.dependency_overrides.clear()


def test_iniciar_simulacao_sem_vaga_valida():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.iniciar_simulacao.side_effect = VagaNaoEncontradaError

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(
            "/simulador/iniciar",
            json={"email": "teste@example.com", "id_vaga": str(uuid.uuid4())},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    finally:
        app.dependency_overrides.clear()


def test_iniciar_simulacao_com_sucesso():
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()
    usuario = _usuario(id_usuario)
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    simulacao = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(),
        id_usuario=id_usuario,
        id_vaga=id_vaga,
        data_criacao=datetime.now(),
        perguntas=[
            {
                "id_pergunta": str(uuid.uuid4()),
                "tipo": "comportamental",
                "texto": "Conte sobre um conflito.",
                "resposta": None,
                "feedback": None,
                "respondida_em": None,
            }
        ],
    )
    servico = MagicMock()
    servico.iniciar_simulacao.return_value = simulacao

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(
            "/simulador/iniciar",
            json={"email": "teste@example.com", "id_vaga": str(id_vaga)},
        )
        assert response.status_code == status.HTTP_201_CREATED
        dados = response.json()
        assert dados["id_vaga"] == str(id_vaga)
        assert len(dados["perguntas"]) == 1
        assert dados["perguntas"][0]["tipo"] == "comportamental"
    finally:
        app.dependency_overrides.clear()


def _simulacao_avaliada(id_usuario, id_simulacao, id_vaga, ids_perguntas):
    return SimulacaoEntrevista(
        id_simulacao=id_simulacao,
        id_usuario=id_usuario,
        id_vaga=id_vaga,
        data_criacao=datetime.now(),
        avaliada_em=datetime.now(),
        nota_final=7.5,
        feedback_geral="Boa entrevista.",
        perguntas=[
            {
                "id_pergunta": str(id_pergunta),
                "tipo": "tecnica",
                "texto": "Como você projetaria uma API?",
                "resposta": "Usaria FastAPI com camadas.",
                "feedback": {
                    "clareza": {"nota": 8, "comentario": "Boa."},
                    "objetividade": {"nota": 7, "comentario": "Ok."},
                    "coerencia": {"nota": 9, "comentario": "Consistente."},
                    "alinhamento": {"nota": 6, "comentario": "Faltou citar a stack da vaga."},
                    "feedback_geral": "Bom, mas pode detalhar mais.",
                },
                "respondida_em": "2026-09-21T12:00:00+00:00",
            }
            for id_pergunta in ids_perguntas
        ],
    )


def _payload_avaliacao(*ids, resposta="Minha resposta completa."):
    return {"respostas": [{"id_pergunta": str(i), "resposta": resposta} for i in ids]}


def _post_avaliar(servico, id_simulacao, payload, usuario=None):
    app.dependency_overrides[get_usuario_atual] = lambda: usuario or _usuario()
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        return client.post(f"/simulador/{id_simulacao}/avaliar", json=payload)
    finally:
        app.dependency_overrides.clear()


def test_avaliar_simulacao_com_sucesso_devolve_notas_feedback_e_nota_final():
    usuario = _usuario()
    id_simulacao, id_pergunta = uuid.uuid4(), uuid.uuid4()
    servico = MagicMock()
    servico.avaliar_simulacao.return_value = _simulacao_avaliada(
        usuario.id_usuario, id_simulacao, uuid.uuid4(), [id_pergunta]
    )

    response = _post_avaliar(servico, id_simulacao, _payload_avaliacao(id_pergunta), usuario)

    assert response.status_code == status.HTTP_200_OK
    dados = response.json()
    assert dados["status"] == "avaliada"
    assert dados["legada"] is False
    assert dados["nota_final"] == 7.5
    assert dados["feedback_geral"] == "Boa entrevista."
    pergunta = dados["perguntas"][0]
    assert pergunta["feedback"]["clareza"]["nota"] == 8
    assert pergunta["feedback"]["feedback_geral"] == "Bom, mas pode detalhar mais."
    servico.avaliar_simulacao.assert_called_once_with(
        id_usuario=usuario.id_usuario,
        id_simulacao=id_simulacao,
        respostas={str(id_pergunta): "Minha resposta completa."},
    )


def test_avaliar_simulacao_remove_espacos_das_pontas_das_respostas():
    usuario = _usuario()
    id_pergunta = uuid.uuid4()
    servico = MagicMock()
    servico.avaliar_simulacao.return_value = _simulacao_avaliada(
        usuario.id_usuario, uuid.uuid4(), uuid.uuid4(), [id_pergunta]
    )

    response = _post_avaliar(
        servico, uuid.uuid4(), _payload_avaliacao(id_pergunta, resposta="   resposta com espaços   "), usuario
    )

    assert response.status_code == status.HTTP_200_OK
    assert servico.avaliar_simulacao.call_args.kwargs["respostas"] == {str(id_pergunta): "resposta com espaços"}


@pytest.mark.parametrize(
    "resposta",
    ["", "          ", "curta", "x" * 9, "x" * 4001],
)
def test_avaliar_simulacao_rejeita_resposta_vazia_curta_ou_longa_demais(resposta):
    servico = MagicMock()

    response = _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(uuid.uuid4(), resposta=resposta))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    servico.avaliar_simulacao.assert_not_called()


def test_avaliar_simulacao_aceita_resposta_com_exatamente_os_limites():
    usuario = _usuario()
    id_pergunta = uuid.uuid4()
    servico = MagicMock()
    servico.avaliar_simulacao.return_value = _simulacao_avaliada(
        usuario.id_usuario, uuid.uuid4(), uuid.uuid4(), [id_pergunta]
    )

    for resposta in ("x" * 10, "x" * 4000):
        response = _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(id_pergunta, resposta=resposta), usuario)
        assert response.status_code == status.HTTP_200_OK


def test_avaliar_simulacao_rejeita_lista_vazia_pergunta_duplicada_e_id_invalido():
    servico = MagicMock()
    repetido = uuid.uuid4()

    assert _post_avaliar(servico, uuid.uuid4(), {"respostas": []}).status_code == 422
    assert _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(repetido, repetido)).status_code == 422
    assert (
        _post_avaliar(servico, uuid.uuid4(), {"respostas": [{"id_pergunta": "nao-uuid", "resposta": "x" * 20}]}).status_code
        == 422
    )
    servico.avaliar_simulacao.assert_not_called()


@pytest.mark.parametrize(
    ("erro", "codigo_http"),
    [
        (SimulacaoNaoEncontradaError(), status.HTTP_404_NOT_FOUND),
        (SimulacaoJaAvaliadaError(), status.HTTP_409_CONFLICT),
        (RespostasInvalidasError("Responda todas as perguntas."), status.HTTP_422_UNPROCESSABLE_ENTITY),
        (IAIndisponivelError("fora do ar"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (IAConfiguracaoAusenteError("sem chave"), status.HTTP_503_SERVICE_UNAVAILABLE),
        (IARespostaInvalidaError("A IA devolveu algo inválido."), status.HTTP_502_BAD_GATEWAY),
    ],
)
def test_avaliar_simulacao_mapeia_erros_para_http(erro, codigo_http):
    servico = MagicMock()
    servico.avaliar_simulacao.side_effect = erro

    response = _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(uuid.uuid4()))

    assert response.status_code == codigo_http
    assert isinstance(response.json()["detail"], str) and response.json()["detail"]


def test_avaliar_simulacao_ia_invalida_informa_que_a_cota_nao_foi_consumida():
    servico = MagicMock()
    servico.avaliar_simulacao.side_effect = IARespostaInvalidaError("A IA devolveu algo inválido.")

    response = _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(uuid.uuid4()))

    assert "cota não foi consumida" in response.json()["detail"]


def test_avaliar_simulacao_cota_excedida_devolve_429_com_renovacao():
    servico = MagicMock()
    renovacao = datetime(2026, 12, 1, tzinfo=timezone.utc)
    servico.avaliar_simulacao.side_effect = CotaIAExcedidaError("entrevista_avaliacao", renovacao)

    response = _post_avaliar(servico, uuid.uuid4(), _payload_avaliacao(uuid.uuid4()))

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    detalhe = response.json()["detail"]
    assert detalhe["codigo"] == "cota_ia_excedida"
    assert detalhe["renovacao_em"] == renovacao.isoformat()


def test_endpoint_antigo_de_resposta_individual_foi_removido():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: MagicMock()
    try:
        response = client.post(
            f"/simulador/{uuid.uuid4()}/perguntas/{uuid.uuid4()}/resposta",
            json={"resposta": "Usaria FastAPI."},
        )
        assert response.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED)
    finally:
        app.dependency_overrides.clear()


def test_repetir_simulacao_cria_nova_simulacao():
    usuario = _usuario()
    id_vaga = uuid.uuid4()
    nova = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(),
        id_usuario=usuario.id_usuario,
        id_vaga=id_vaga,
        data_criacao=datetime.now(),
        perguntas=[
            {"id_pergunta": str(uuid.uuid4()), "tipo": "tecnica", "texto": "P?", "resposta": None, "feedback": None}
        ],
    )
    servico = MagicMock()
    servico.repetir_simulacao.return_value = nova
    id_original = uuid.uuid4()

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(f"/simulador/{id_original}/repetir")
        assert response.status_code == status.HTTP_201_CREATED
        dados = response.json()
        assert dados["id_simulacao"] == str(nova.id_simulacao)
        assert dados["status"] == "pendente"
        servico.repetir_simulacao.assert_called_once_with(usuario.id_usuario, id_original)

        servico.repetir_simulacao.side_effect = SimulacaoNaoEncontradaError
        assert client.post(f"/simulador/{id_original}/repetir").status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.clear()


def test_excluir_simulacao_retorna_204_404_e_409_quando_em_avaliacao():
    usuario = _usuario()
    servico = MagicMock()
    id_simulacao = uuid.uuid4()

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.delete(f"/simulador/{id_simulacao}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        servico.excluir_simulacao.assert_called_once_with(usuario.id_usuario, id_simulacao)

        servico.excluir_simulacao.side_effect = SimulacaoNaoEncontradaError
        assert client.delete(f"/simulador/{id_simulacao}").status_code == status.HTTP_404_NOT_FOUND

        servico.excluir_simulacao.side_effect = SimulacaoEmAvaliacaoError(
            "Esta entrevista está sendo avaliada; tente excluir quando terminar."
        )
        conflito = client.delete(f"/simulador/{id_simulacao}")
        assert conflito.status_code == status.HTTP_409_CONFLICT
        assert "sendo avaliada" in conflito.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_rotas_de_ia_do_simulador_aplicam_rate_limit():
    usuario = _usuario()
    id_simulacao, id_pergunta = uuid.uuid4(), uuid.uuid4()
    servico = MagicMock()
    servico.repetir_simulacao.return_value = _simulacao_avaliada(
        usuario.id_usuario, uuid.uuid4(), uuid.uuid4(), [id_pergunta]
    )
    servico.avaliar_simulacao.return_value = _simulacao_avaliada(
        usuario.id_usuario, id_simulacao, uuid.uuid4(), [id_pergunta]
    )

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    limiter.reset()
    limiter.enabled = True
    try:
        for _ in range(10):
            assert client.post(f"/simulador/{id_simulacao}/repetir").status_code == status.HTTP_201_CREATED
        assert client.post(f"/simulador/{id_simulacao}/repetir").status_code == status.HTTP_429_TOO_MANY_REQUESTS

        payload = _payload_avaliacao(id_pergunta)
        for _ in range(20):
            assert client.post(f"/simulador/{id_simulacao}/avaliar", json=payload).status_code == status.HTTP_200_OK
        assert (
            client.post(f"/simulador/{id_simulacao}/avaliar", json=payload).status_code
            == status.HTTP_429_TOO_MANY_REQUESTS
        )
    finally:
        limiter.reset()
        limiter.enabled = False
        app.dependency_overrides.clear()


def test_obter_simulacao_nao_encontrada():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.obter_simulacao.side_effect = SimulacaoNaoEncontradaError

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.get(f"/simulador/{uuid.uuid4()}?email=teste@example.com")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.clear()


def test_listar_simulacoes():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    simulacao = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(),
        id_usuario=usuario.id_usuario,
        id_vaga=uuid.uuid4(),
        data_criacao=datetime.now(),
        perguntas=[
            {"id_pergunta": str(uuid.uuid4()), "tipo": "tecnica", "texto": "P1", "resposta": "R1"},
            {"id_pergunta": str(uuid.uuid4()), "tipo": "comportamental", "texto": "P2", "resposta": None},
        ],
    )
    servico = MagicMock()
    servico.listar_simulacoes_usuario.return_value = [simulacao]

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.get("/simulador?email=teste@example.com")
        assert response.status_code == status.HTTP_200_OK
        dados = response.json()["simulacoes"]
        assert len(dados) == 1
        assert dados[0]["total_perguntas"] == 2
        assert dados[0]["total_respondidas"] == 1
        assert dados[0]["status"] == "pendente"
        assert dados[0]["nota_final"] is None
        assert dados[0]["vaga_titulo"] is None
        assert response.json()["paginacao"] == {"total": 1, "limit": None, "offset": 0}
        servico.listar_simulacoes_usuario.assert_called_once_with(usuario.id_usuario, limit=None, offset=0)
    finally:
        app.dependency_overrides.clear()


def test_listar_simulacoes_traz_titulo_da_vaga_status_e_nota_inclusive_das_antigas():
    usuario = _usuario()
    vaga = Vaga(id_vaga=uuid.uuid4(), id_usuario=usuario.id_usuario, titulo="Dev Backend", descricao="x")
    avaliada = _simulacao_avaliada(usuario.id_usuario, uuid.uuid4(), vaga.id_vaga, [uuid.uuid4()])
    avaliada.vaga = vaga
    antiga = _simulacao_avaliada(usuario.id_usuario, uuid.uuid4(), vaga.id_vaga, [uuid.uuid4()])
    antiga.avaliada_em = None
    antiga.nota_final = None
    antiga.vaga = vaga
    servico = MagicMock()
    servico.listar_simulacoes_usuario.return_value = [avaliada, antiga]

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        itens = client.get("/simulador").json()["simulacoes"]
    finally:
        app.dependency_overrides.clear()

    assert itens[0]["vaga_titulo"] == "Dev Backend"
    assert (itens[0]["status"], itens[0]["legada"], itens[0]["nota_final"]) == ("avaliada", False, 7.5)
    # Antiga: sem avaliada_em/nota_final gravadas; a nota é calculada do feedback por pergunta.
    assert (itens[1]["status"], itens[1]["legada"], itens[1]["nota_final"]) == ("avaliada", True, 7.5)


def test_listar_simulacoes_paginado_usa_contagem_do_servico():
    usuario = _usuario()
    servico = MagicMock()
    servico.listar_simulacoes_usuario.return_value = []
    servico.contar_simulacoes_usuario.return_value = 7

    app.dependency_overrides[get_usuario_atual] = lambda: usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.get("/simulador", params={"limit": 5, "offset": 10})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["paginacao"] == {"total": 7, "limit": 5, "offset": 10}
        servico.listar_simulacoes_usuario.assert_called_once_with(usuario.id_usuario, limit=5, offset=10)
    finally:
        app.dependency_overrides.clear()
