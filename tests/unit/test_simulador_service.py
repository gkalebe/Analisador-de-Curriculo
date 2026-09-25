import json
import uuid
from unittest.mock import MagicMock

import pytest

from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista
from app.core.persistencia.models.vaga import Vaga
from app.core.service.simulador_service import (
    PerguntaNaoEncontradaError,
    RespostaVaziaError,
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
    service = SimuladorService(db=mock_db, ai_service_adapter=ai_adapter)
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


def test_responder_pergunta_com_resposta_vazia_lanca_erro(simulador_service):
    id_usuario = uuid.uuid4()
    id_simulacao = uuid.uuid4()
    id_pergunta = str(uuid.uuid4())
    simulacao = SimulacaoEntrevista(
        id_simulacao=id_simulacao,
        id_usuario=id_usuario,
        id_vaga=uuid.uuid4(),
        perguntas=[{"id_pergunta": id_pergunta, "tipo": "tecnica", "texto": "Pergunta?", "resposta": None}],
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao)

    with pytest.raises(RespostaVaziaError):
        simulador_service.responder_pergunta(
            id_usuario=id_usuario, id_simulacao=id_simulacao, id_pergunta=id_pergunta, resposta="   "
        )


def test_responder_pergunta_simulacao_nao_encontrada(simulador_service):
    id_usuario = uuid.uuid4()
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=None)

    with pytest.raises(SimulacaoNaoEncontradaError):
        simulador_service.responder_pergunta(
            id_usuario=id_usuario, id_simulacao=uuid.uuid4(), id_pergunta=str(uuid.uuid4()), resposta="Resposta"
        )


def test_responder_pergunta_de_outra_simulacao_nao_encontrada(simulador_service):
    id_usuario = uuid.uuid4()
    simulacao_de_outro = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(), id_usuario=uuid.uuid4(), id_vaga=uuid.uuid4(), perguntas=[]
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao_de_outro)

    with pytest.raises(SimulacaoNaoEncontradaError):
        simulador_service.responder_pergunta(
            id_usuario=id_usuario,
            id_simulacao=simulacao_de_outro.id_simulacao,
            id_pergunta=str(uuid.uuid4()),
            resposta="Resposta",
        )


def test_responder_pergunta_id_pergunta_invalido_lanca_erro(simulador_service):
    id_usuario = uuid.uuid4()
    id_simulacao = uuid.uuid4()
    simulacao = SimulacaoEntrevista(
        id_simulacao=id_simulacao,
        id_usuario=id_usuario,
        id_vaga=uuid.uuid4(),
        perguntas=[{"id_pergunta": str(uuid.uuid4()), "tipo": "tecnica", "texto": "Pergunta?", "resposta": None}],
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao)

    with pytest.raises(PerguntaNaoEncontradaError):
        simulador_service.responder_pergunta(
            id_usuario=id_usuario,
            id_simulacao=id_simulacao,
            id_pergunta=str(uuid.uuid4()),
            resposta="Resposta válida",
        )


def test_responder_pergunta_com_sucesso_grava_feedback(simulador_service):
    id_usuario = uuid.uuid4()
    id_simulacao = uuid.uuid4()
    id_vaga = uuid.uuid4()
    id_pergunta = str(uuid.uuid4())
    vaga = _vaga(id_usuario=id_usuario, id_vaga=id_vaga)

    simulacao = SimulacaoEntrevista(
        id_simulacao=id_simulacao,
        id_usuario=id_usuario,
        id_vaga=id_vaga,
        perguntas=[
            {
                "id_pergunta": id_pergunta,
                "tipo": "tecnica",
                "texto": "Como você projetaria uma API?",
                "resposta": None,
                "feedback": None,
                "respondida_em": None,
            }
        ],
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao)
    simulador_service.simulacao_repository.salvar_perguntas = MagicMock(
        side_effect=lambda s, perguntas: (setattr(s, "perguntas", perguntas), s)[1]
    )
    simulador_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)

    resultado_ia = json.dumps(
        {
            "clareza": {"nota": 8, "comentario": "Boa clareza."},
            "objetividade": {"nota": 7, "comentario": "Poderia ser mais direto."},
            "coerencia": {"nota": 9, "comentario": "Consistente."},
            "alinhamento": {"nota": 6, "comentario": "Falta citar tecnologias da vaga."},
            "feedback_geral": "Boa resposta, mas cite mais as tecnologias pedidas na vaga.",
        }
    )
    simulador_service.ai_service_adapter.avaliar_resposta_entrevista.return_value = resultado_ia

    resultado = simulador_service.responder_pergunta(
        id_usuario=id_usuario,
        id_simulacao=id_simulacao,
        id_pergunta=id_pergunta,
        resposta="Eu usaria FastAPI com uma camada de serviços.",
    )

    pergunta_atualizada = resultado.perguntas[0]
    assert pergunta_atualizada["resposta"] == "Eu usaria FastAPI com uma camada de serviços."
    assert pergunta_atualizada["feedback"]["clareza"]["nota"] == 8
    assert pergunta_atualizada["feedback"]["alinhamento"]["comentario"] == "Falta citar tecnologias da vaga."
    assert pergunta_atualizada["respondida_em"] is not None

    simulador_service.ai_service_adapter.avaliar_resposta_entrevista.assert_called_once_with(
        texto_vaga=simulador_service._montar_texto_vaga(vaga),
        pergunta="Como você projetaria uma API?",
        tipo="tecnica",
        resposta="Eu usaria FastAPI com uma camada de serviços.",
    )


def test_obter_simulacao_de_outro_usuario_nao_encontrada(simulador_service):
    id_usuario = uuid.uuid4()
    simulacao_de_outro = SimulacaoEntrevista(
        id_simulacao=uuid.uuid4(), id_usuario=uuid.uuid4(), id_vaga=uuid.uuid4(), perguntas=[]
    )
    simulador_service.simulacao_repository.buscar_por_id = MagicMock(return_value=simulacao_de_outro)

    with pytest.raises(SimulacaoNaoEncontradaError):
        simulador_service.obter_simulacao(id_usuario=id_usuario, id_simulacao=simulacao_de_outro.id_simulacao)
