import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from sqlalchemy.exc import OperationalError

from app.adapters.ai_service.ai_service_adapter import IAIndisponivelError, IARespostaInvalidaError
from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista
from app.core.persistencia.models.vaga import Vaga
from app.core.service.uso_ia_service import UsoIAService
from app.core.service.simulador_service import (
    MAXIMO_PERGUNTAS_POR_SIMULACAO,
    RespostasInvalidasError,
    SimulacaoEmAvaliacaoError,
    SimulacaoJaAvaliadaError,
    SimulacaoNaoEncontradaError,
    SimuladorService,
    VagaNaoEncontradaError,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def simulador_service(mock_db):
    ai_adapter = MagicMock()
    service = SimuladorService(db=mock_db, ai_service_adapter=ai_adapter, uso_ia_service=MagicMock())
    return service


def _vaga(id_usuario, id_vaga=None):
    return Vaga(
        id_vaga=id_vaga or uuid.uuid4(),
        id_usuario=id_usuario,
        titulo="Desenvolvedor Backend",
        area="Tecnologia",
        requisitos="Python, FastAPI, SQL",
        descricao="Desenvolvimento de APIs para o time de produto.",
    )


def test_iniciar_simulacao_sem_vaga_lanca_erro(simulador_service):
    id_usuario = uuid.uuid4()
    with pytest.raises(VagaNaoEncontradaError):
        simulador_service.iniciar_simulacao(id_usuario=id_usuario, id_vaga=None)


def test_iniciar_simulacao_vaga_de_outro_usuario_lanca_erro(simulador_service):
    id_usuario = uuid.uuid4()
    vaga_de_outro = _vaga(id_usuario=uuid.uuid4())
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga_de_outro)

    with pytest.raises(VagaNaoEncontradaError):
        simulador_service.iniciar_simulacao(id_usuario=id_usuario, id_vaga=vaga_de_outro.id_vaga)


def test_iniciar_simulacao_gera_ao_menos_uma_pergunta_de_cada_tipo(simulador_service):
    id_usuario = uuid.uuid4()
    vaga = _vaga(id_usuario=id_usuario)
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    simulador_service.simulacao_repository.criar = MagicMock(side_effect=lambda s: s)

    resultado_ia = json.dumps(
        {
            "perguntas": [
                {"tipo": "comportamental", "texto": "Conte sobre um conflito em equipe."},
                {"tipo": "comportamental", "texto": "Conte sobre uma liderança que você exerceu."},
                {"tipo": "tecnica", "texto": "Como você projetaria uma API REST?"},
                {"tipo": "tecnica", "texto": "O que é um índice de banco de dados?"},
                {"tipo": "situacional", "texto": "Como você agiria com um prazo apertado?"},
                {"tipo": "situacional", "texto": "Como você lidaria com um bug em produção?"},
            ]
        }
    )
    simulador_service.ai_service_adapter.gerar_perguntas_entrevista.return_value = resultado_ia

    simulacao = simulador_service.iniciar_simulacao(id_usuario=id_usuario, id_vaga=vaga.id_vaga)

    assert simulacao.id_usuario == id_usuario
    assert simulacao.id_vaga == vaga.id_vaga
    tipos = [p["tipo"] for p in simulacao.perguntas]
    assert "comportamental" in tipos
    assert "tecnica" in tipos
    assert "situacional" in tipos
    assert len(simulacao.perguntas) == 6
    assert all(p["resposta"] is None for p in simulacao.perguntas)
    assert all(p["id_pergunta"] for p in simulacao.perguntas)


def test_iniciar_simulacao_completa_tipos_faltantes_quando_ia_falha(simulador_service):
    id_usuario = uuid.uuid4()
    vaga = _vaga(id_usuario=id_usuario)
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    simulador_service.simulacao_repository.criar = MagicMock(side_effect=lambda s: s)

    # IA devolve algo fora do formato esperado (texto cru, não-JSON) — o serviço precisa
    # garantir a cobertura mínima (RN de aceite) mesmo assim.
    simulador_service.ai_service_adapter.gerar_perguntas_entrevista.return_value = "não é um JSON válido"

    simulacao = simulador_service.iniciar_simulacao(id_usuario=id_usuario, id_vaga=vaga.id_vaga)

    tipos = {p["tipo"] for p in simulacao.perguntas}
    assert tipos == {"comportamental", "tecnica", "situacional"}


def _simulacao_pendente(id_usuario, id_vaga=None, total=2):
    return SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(),
        id_usuario=id_usuario,
        id_vaga=id_vaga or uuid.uuid4(),
        perguntas=[
            {
                "id_pergunta": str(uuid.uuid4()),
                "tipo": "tecnica" if i % 2 == 0 else "comportamental",
                "texto": f"Pergunta {i + 1}?",
                "resposta": None,
                "feedback": None,
                "respondida_em": None,
            }
            for i in range(total)
        ],
    )


def _respostas_para(simulacao):
    return {p["id_pergunta"]: f"Resposta completa número {i}" for i, p in enumerate(simulacao.perguntas, start=1)}


def _json_avaliacao(ordens, nota=8, feedback_geral="Bom desempenho geral."):
    dimensao = {"nota": nota, "comentario": "Comentário."}
    return json.dumps(
        {
            "avaliacoes": [
                {
                    "ordem": ordem,
                    "clareza": dimensao,
                    "objetividade": {"nota": 6, "comentario": "Mais direto."},
                    "coerencia": dimensao,
                    "alinhamento": {"nota": 10, "comentario": "Alinhada."},
                    "feedback_geral": f"Feedback da pergunta {ordem}.",
                }
                for ordem in ordens
            ],
            "feedback_geral": feedback_geral,
        }
    )


@pytest.fixture
def servico_avaliacao(simulador_service):
    """Serviço com repositórios simulados: devolve (service, simulacao, vaga)."""
    id_usuario = uuid.uuid4()
    vaga = _vaga(id_usuario=id_usuario)
    simulacao = _simulacao_pendente(id_usuario, vaga.id_vaga)
    repo = simulador_service.simulacao_repository
    repo.buscar_por_id = MagicMock(return_value=simulacao)
    repo.buscar_por_id_para_atualizacao = MagicMock(return_value=simulacao)

    def _salvar(sim, perguntas, feedback_geral, nota_final, avaliada_em):
        sim.perguntas = perguntas
        sim.feedback_geral = feedback_geral
        sim.nota_final = nota_final
        sim.avaliada_em = avaliada_em
        return sim

    repo.salvar_avaliacao = MagicMock(side_effect=_salvar)
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    return simulador_service, simulacao, vaga


def test_avaliar_simulacao_grava_feedback_de_todas_as_perguntas_em_uma_chamada_de_ia(servico_avaliacao):
    service, simulacao, vaga = servico_avaliacao
    respostas = _respostas_para(simulacao)
    service.ai_service_adapter.avaliar_respostas_entrevista.return_value = _json_avaliacao([1, 2])

    resultado = service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, respostas)

    service.ai_service_adapter.avaliar_respostas_entrevista.assert_called_once()
    texto_vaga, itens = service.ai_service_adapter.avaliar_respostas_entrevista.call_args.args
    assert texto_vaga == service._montar_texto_vaga(vaga)
    assert [i["ordem"] for i in itens] == [1, 2]
    assert itens[0]["resposta"] == "Resposta completa número 1"
    service.uso_ia_service.reservar.assert_called_once_with(simulacao.id_usuario, "entrevista_avaliacao")

    assert resultado.status == "avaliada"
    assert resultado.avaliada_em is not None
    assert resultado.feedback_geral == "Bom desempenho geral."
    # média de (8 + 6 + 8 + 10) / 4 = 8.0 em cada pergunta
    assert resultado.nota_final == 8.0
    primeira = resultado.perguntas[0]
    assert primeira["resposta"] == "Resposta completa número 1"
    assert primeira["feedback"]["clareza"] == {"nota": 8.0, "comentario": "Comentário."}
    assert primeira["feedback"]["alinhamento"]["nota"] == 10.0
    assert primeira["feedback"]["feedback_geral"] == "Feedback da pergunta 1."
    assert primeira["respondida_em"] is not None


def test_avaliar_simulacao_trava_a_linha_da_simulacao_depois_de_reservar_a_cota(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    ordem_chamadas = []
    service.uso_ia_service.reservar.side_effect = lambda *a, **k: (
        ordem_chamadas.append("reservar") or MagicMock()
    )
    service.simulacao_repository.buscar_por_id_para_atualizacao.side_effect = lambda *a, **k: (
        ordem_chamadas.append("travar") or simulacao
    )
    service.ai_service_adapter.avaliar_respostas_entrevista.return_value = _json_avaliacao([1, 2])

    service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    assert ordem_chamadas == ["reservar", "travar"]


def test_avaliar_simulacao_com_resposta_faltando_nao_chama_ia_nem_reserva_cota(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    respostas = _respostas_para(simulacao)
    respostas.pop(simulacao.perguntas[0]["id_pergunta"])

    with pytest.raises(RespostasInvalidasError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, respostas)

    service.uso_ia_service.reservar.assert_not_called()
    service.ai_service_adapter.avaliar_respostas_entrevista.assert_not_called()


def test_avaliar_simulacao_com_pergunta_de_outra_simulacao_lanca_erro(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    respostas = _respostas_para(simulacao)
    respostas[str(uuid.uuid4())] = "Resposta para uma pergunta que não existe aqui"

    with pytest.raises(RespostasInvalidasError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, respostas)

    service.ai_service_adapter.avaliar_respostas_entrevista.assert_not_called()


def test_avaliar_simulacao_ja_avaliada_lanca_conflito_sem_reservar_cota(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    simulacao.avaliada_em = datetime.now(timezone.utc)

    with pytest.raises(SimulacaoJaAvaliadaError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    service.uso_ia_service.reservar.assert_not_called()


def test_avaliar_simulacao_antiga_com_feedback_por_pergunta_e_somente_leitura(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    simulacao.perguntas[0]["resposta"] = "Resposta antiga"
    simulacao.perguntas[0]["feedback"] = {"clareza": {"nota": 7, "comentario": "ok"}}

    with pytest.raises(SimulacaoJaAvaliadaError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))


def test_avaliar_simulacao_concluida_por_outra_requisicao_durante_a_reserva_lanca_conflito(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    pendente = SimulacaoEntrevista(
        id_simulacao=simulacao.id_simulacao,
        id_usuario=simulacao.id_usuario,
        id_vaga=simulacao.id_vaga,
        perguntas=simulacao.perguntas,
    )
    concluida = SimulacaoEntrevista(
        id_simulacao=simulacao.id_simulacao,
        id_usuario=simulacao.id_usuario,
        id_vaga=simulacao.id_vaga,
        perguntas=simulacao.perguntas,
        avaliada_em=datetime.now(timezone.utc),
    )
    # A leitura inicial (sem lock) vê "pendente"; depois do lock, a outra requisição já concluiu.
    service.simulacao_repository.buscar_por_id = MagicMock(return_value=pendente)
    service.simulacao_repository.buscar_por_id_para_atualizacao = MagicMock(return_value=concluida)

    with pytest.raises(SimulacaoJaAvaliadaError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    service.ai_service_adapter.avaliar_respostas_entrevista.assert_not_called()
    service.simulacao_repository.salvar_avaliacao.assert_not_called()


@pytest.mark.parametrize(
    "resposta_ia",
    [
        "isto não é JSON",
        json.dumps({"avaliacoes": []}),
        # falta a pergunta 2
        json.dumps(json.loads(_json_avaliacao([1])) | {}),
        # nota fora de 0-10
        json.dumps(
            {
                "avaliacoes": [
                    {
                        "ordem": ordem,
                        "clareza": {"nota": 11, "comentario": "x"},
                        "objetividade": {"nota": 5, "comentario": "x"},
                        "coerencia": {"nota": 5, "comentario": "x"},
                        "alinhamento": {"nota": 5, "comentario": "x"},
                    }
                    for ordem in (1, 2)
                ]
            }
        ),
        # pergunta repetida
        _json_avaliacao([1, 1]),
    ],
)
def test_avaliar_simulacao_com_resposta_invalida_da_ia_libera_a_reserva_e_nao_grava(servico_avaliacao, resposta_ia):
    service, simulacao, _ = servico_avaliacao
    reserva = MagicMock()
    contexto = service.uso_ia_service.reservar.return_value
    contexto.__enter__.return_value = reserva
    contexto.__exit__.return_value = False  # propaga a exceção como o contextmanager real
    service.ai_service_adapter.avaliar_respostas_entrevista.return_value = resposta_ia

    with pytest.raises(IARespostaInvalidaError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    # O __exit__ do contexto recebeu a exceção (é nele que o UsoIAService libera a reserva).
    assert contexto.__exit__.call_args.args[0] is IARespostaInvalidaError
    service.simulacao_repository.salvar_avaliacao.assert_not_called()
    assert simulacao.avaliada_em is None


def test_avaliar_simulacao_com_resposta_invalida_libera_a_cota_de_verdade(servico_avaliacao):
    # Usa o UsoIAService real (só o repositório é simulado) para provar o ciclo reservar -> liberar.
    service, simulacao, _ = servico_avaliacao
    reserva = SimpleNamespace(id_uso=uuid.uuid4(), estado="reservado")
    uso_ia = UsoIAService(db=None)
    uso_ia.repository = MagicMock()
    uso_ia.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="pro")
    uso_ia.repository.reservar.return_value = reserva
    service.uso_ia_service = uso_ia
    service.ai_service_adapter.avaliar_respostas_entrevista.return_value = "não é JSON"

    with pytest.raises(IARespostaInvalidaError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    assert uso_ia.repository.reservar.call_args.kwargs["tipo_operacao"] == "entrevista_avaliacao"
    uso_ia.repository.finalizar.assert_called_once_with(reserva.id_uso, "liberado")


def test_avaliar_simulacao_com_sucesso_consome_a_cota(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    reserva = SimpleNamespace(id_uso=uuid.uuid4(), estado="reservado")
    uso_ia = UsoIAService(db=None)
    uso_ia.repository = MagicMock()
    uso_ia.repository.obter_usuario.return_value = SimpleNamespace(plano_codigo="pro")
    uso_ia.repository.reservar.return_value = reserva
    service.uso_ia_service = uso_ia
    service.ai_service_adapter.avaliar_respostas_entrevista.return_value = _json_avaliacao([1, 2])

    service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    uso_ia.repository.finalizar.assert_called_once_with(reserva.id_uso, "consumido")


def test_avaliar_simulacao_quando_ia_falha_libera_a_reserva(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao
    contexto = service.uso_ia_service.reservar.return_value
    contexto.__exit__.return_value = False
    service.ai_service_adapter.avaliar_respostas_entrevista.side_effect = IAIndisponivelError("fora do ar")

    with pytest.raises(IAIndisponivelError):
        service.avaliar_simulacao(simulacao.id_usuario, simulacao.id_simulacao, _respostas_para(simulacao))

    assert contexto.__exit__.call_args.args[0] is IAIndisponivelError
    service.simulacao_repository.salvar_avaliacao.assert_not_called()


def test_avaliar_simulacao_de_outro_usuario_nao_encontrada(servico_avaliacao):
    service, simulacao, _ = servico_avaliacao

    with pytest.raises(SimulacaoNaoEncontradaError):
        service.avaliar_simulacao(uuid.uuid4(), simulacao.id_simulacao, _respostas_para(simulacao))

    service.uso_ia_service.reservar.assert_not_called()


def test_repetir_simulacao_cria_nova_simulacao_para_a_mesma_vaga_sem_alterar_a_original(simulador_service):
    id_usuario = uuid.uuid4()
    vaga = _vaga(id_usuario=id_usuario)
    original = _simulacao_pendente(id_usuario, vaga.id_vaga)
    original.avaliada_em = datetime.now(timezone.utc)
    perguntas_originais = [dict(p) for p in original.perguntas]
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=original)
    simulador_service.simulacao_repository.criar = MagicMock(side_effect=lambda s: s)
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    simulador_service.ai_service_adapter.gerar_perguntas_entrevista.return_value = "texto inválido"

    nova = simulador_service.repetir_simulacao(id_usuario, original.id_simulacao)

    assert nova is not original
    assert nova.id_vaga == original.id_vaga
    assert nova.status == "pendente"
    assert all(p["resposta"] is None for p in nova.perguntas)
    simulador_service.uso_ia_service.reservar.assert_called_once_with(id_usuario, "entrevista_inicio")
    assert original.perguntas == perguntas_originais
    assert original.status == "avaliada"


def test_repetir_simulacao_de_outro_usuario_nao_encontrada(simulador_service):
    original = _simulacao_pendente(uuid.uuid4())
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=original)

    with pytest.raises(SimulacaoNaoEncontradaError):
        simulador_service.repetir_simulacao(uuid.uuid4(), original.id_simulacao)

    simulador_service.uso_ia_service.reservar.assert_not_called()


def test_excluir_simulacao_do_proprio_usuario_remove_sem_devolver_cota(simulador_service):
    id_usuario = uuid.uuid4()
    simulacao = _simulacao_pendente(id_usuario)
    repo = simulador_service.simulacao_repository
    repo.buscar_por_id_para_atualizacao = MagicMock(return_value=simulacao)
    repo.excluir = MagicMock()

    simulador_service.excluir_simulacao(id_usuario, simulacao.id_simulacao)

    repo.buscar_por_id_para_atualizacao.assert_called_once_with(
        simulacao.id_simulacao, id_usuario=id_usuario, nowait=True
    )
    repo.excluir.assert_called_once_with(simulacao)
    simulador_service.uso_ia_service.reservar.assert_not_called()


def test_excluir_simulacao_em_avaliacao_faz_rollback_e_lanca_conflito(simulador_service):
    id_usuario = uuid.uuid4()
    id_simulacao = uuid.uuid4()
    repo = simulador_service.simulacao_repository
    repo.db = MagicMock()
    repo.excluir = MagicMock()
    erro_lock = OperationalError("SELECT ... FOR UPDATE NOWAIT", {}, SimpleNamespace(pgcode="55P03"))
    repo.buscar_por_id_para_atualizacao = MagicMock(side_effect=erro_lock)

    with pytest.raises(SimulacaoEmAvaliacaoError, match="sendo avaliada"):
        simulador_service.excluir_simulacao(id_usuario, id_simulacao)

    repo.db.rollback.assert_called_once()
    repo.excluir.assert_not_called()


def test_interpretar_perguntas_limita_ao_teto_do_schema_preservando_tipos_obrigatorios(simulador_service):
    excesso = json.dumps(
        {
            "perguntas": [
                {"tipo": "tecnica", "texto": f"Pergunta técnica {i}?"}
                for i in range(MAXIMO_PERGUNTAS_POR_SIMULACAO + 5)
            ]
        }
    )

    perguntas = simulador_service._interpretar_perguntas(excesso)

    assert len(perguntas) == MAXIMO_PERGUNTAS_POR_SIMULACAO
    assert {p["tipo"] for p in perguntas} == {"comportamental", "tecnica", "situacional"}


def test_excluir_simulacao_de_outro_usuario_ou_inexistente_nao_encontrada(simulador_service):
    repo = simulador_service.simulacao_repository
    repo.excluir = MagicMock()
    repo.db = MagicMock()
    alheia = _simulacao_pendente(uuid.uuid4())
    for retorno in (alheia, None):
        repo.buscar_por_id_para_atualizacao = MagicMock(return_value=retorno)
        with pytest.raises(SimulacaoNaoEncontradaError):
            simulador_service.excluir_simulacao(uuid.uuid4(), alheia.id_simulacao)

    repo.excluir.assert_not_called()


def test_status_e_nota_de_simulacoes_pendente_avaliada_e_antiga():
    pendente = _simulacao_pendente(uuid.uuid4())
    assert (pendente.status, pendente.legada, pendente.nota_geral) == ("pendente", False, None)

    avaliada = _simulacao_pendente(uuid.uuid4())
    avaliada.avaliada_em = datetime.now(timezone.utc)
    avaliada.nota_final = 7.5
    assert (avaliada.status, avaliada.legada, avaliada.nota_geral) == ("avaliada", False, 7.5)

    antiga = _simulacao_pendente(uuid.uuid4())
    antiga.perguntas[0]["resposta"] = "Resposta"
    antiga.perguntas[0]["feedback"] = {
        "clareza": {"nota": 8, "comentario": ""},
        "objetividade": {"nota": 6, "comentario": ""},
        "coerencia": {"nota": None, "comentario": ""},
        "alinhamento": {"nota": 7, "comentario": ""},
        "feedback_geral": "ok",
    }
    assert (antiga.status, antiga.legada) == ("avaliada", True)
    assert antiga.nota_geral == 7.0
    assert antiga.total_respondidas == 1


def test_obter_simulacao_de_outro_usuario_nao_encontrada(simulador_service):
    id_usuario = uuid.uuid4()
    simulacao_de_outro = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(), id_usuario=uuid.uuid4(), id_vaga=uuid.uuid4(), perguntas=[]
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao_de_outro)

    with pytest.raises(SimulacaoNaoEncontradaError):
        simulador_service.obter_simulacao(id_usuario=id_usuario, id_simulacao=simulacao_de_outro.id_simulacao)


def test_montar_texto_vaga_com_dados_complementares(simulador_service):
    vaga = Vaga(
        id_vaga=uuid.uuid4(),
        id_usuario=uuid.uuid4(),
        titulo="Engenheiro de Software",
        empresa="Tech Corp",
        area="Tecnologia",
        descricao="Desenvolvimento de plataformas.",
        responsabilidades="Liderar equipe e projetar arquitetura.",
        requisitos_obrigatorios="Python e Docker.",
        requisitos_desejaveis="Kubernetes.",
        competencias="Comunicação e liderança.",
    )

    texto = simulador_service._montar_texto_vaga(vaga)

    assert "Título da Vaga: Engenheiro de Software" in texto
    assert "Empresa: Tech Corp" in texto
    assert "Descrição da Vaga:\nDesenvolvimento de plataformas." in texto
    assert "Responsabilidades:\nLiderar equipe e projetar arquitetura." in texto
    assert "Requisitos Obrigatórios:\nPython e Docker." in texto
    assert "Requisitos Desejáveis:\nKubernetes." in texto
    assert "Competências:\nComunicação e liderança." in texto
