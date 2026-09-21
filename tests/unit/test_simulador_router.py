import uuid
from datetime import datetime
from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.persistencia.models.simulacao_entrevista import SimulacaoEntrevista
from app.core.persistencia.models.usuario import Usuario
from app.core.service.simulador_service import (
    PerguntaNaoEncontradaError,
    RespostaVaziaError,
    SimulacaoNaoEncontradaError,
    VagaNaoEncontradaError,
)
from app.main import app
from app.web.routers.simulador_router import get_simulador_service, get_usuario_repository

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
    repo_falso = MagicMock()
    repo_falso.buscar_por_email.return_value = None

    app.dependency_overrides[get_usuario_repository] = lambda: repo_falso
    try:
        response = client.post(
            "/simulador/iniciar",
            json={"email": "desconhecido@example.com", "id_vaga": str(uuid.uuid4())},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.clear()


def test_iniciar_simulacao_sem_vaga_valida():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.iniciar_simulacao.side_effect = VagaNaoEncontradaError

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
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

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
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


def test_responder_pergunta_resposta_vazia():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.responder_pergunta.side_effect = RespostaVaziaError("Digite uma resposta antes de enviar.")

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(
            f"/simulador/{uuid.uuid4()}/perguntas/{uuid.uuid4()}/resposta",
            json={"email": "teste@example.com", "resposta": "x"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "resposta" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_responder_pergunta_nao_encontrada():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.responder_pergunta.side_effect = PerguntaNaoEncontradaError

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(
            f"/simulador/{uuid.uuid4()}/perguntas/{uuid.uuid4()}/resposta",
            json={"email": "teste@example.com", "resposta": "Minha resposta"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.clear()


def test_responder_pergunta_com_sucesso():
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()
    id_simulacao = uuid.uuid4()
    id_pergunta = uuid.uuid4()
    usuario = _usuario(id_usuario)
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    simulacao_atualizada = SimulacaoEntrevista(
        id_simulacao=id_simulacao,
        id_usuario=id_usuario,
        id_vaga=id_vaga,
        data_criacao=datetime.now(),
        perguntas=[
            {
                "id_pergunta": str(id_pergunta),
                "tipo": "tecnica",
                "texto": "Como você projetaria uma API?",
                "resposta": "Usaria FastAPI.",
                "feedback": {
                    "clareza": {"nota": 8, "comentario": "Boa."},
                    "objetividade": {"nota": 7, "comentario": "Ok."},
                    "coerencia": {"nota": 9, "comentario": "Consistente."},
                    "alinhamento": {"nota": 6, "comentario": "Faltou citar a stack da vaga."},
                    "feedback_geral": "Bom, mas pode detalhar mais.",
                },
                "respondida_em": "2026-09-21T12:00:00+00:00",
            }
        ],
    )
    servico = MagicMock()
    servico.responder_pergunta.return_value = simulacao_atualizada

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.post(
            f"/simulador/{id_simulacao}/perguntas/{id_pergunta}/resposta",
            json={"email": "teste@example.com", "resposta": "Usaria FastAPI."},
        )
        assert response.status_code == status.HTTP_200_OK
        dados = response.json()
        pergunta = dados["perguntas"][0]
        assert pergunta["resposta"] == "Usaria FastAPI."
        assert pergunta["feedback"]["clareza"]["nota"] == 8
        assert pergunta["feedback"]["feedback_geral"] == "Bom, mas pode detalhar mais."
    finally:
        app.dependency_overrides.clear()


def test_obter_simulacao_nao_encontrada():
    usuario = _usuario()
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    servico = MagicMock()
    servico.obter_simulacao.side_effect = SimulacaoNaoEncontradaError

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
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

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_simulador_service] = lambda: servico
    try:
        response = client.get("/simulador?email=teste@example.com")
        assert response.status_code == status.HTTP_200_OK
        dados = response.json()["simulacoes"]
        assert len(dados) == 1
        assert dados[0]["total_perguntas"] == 2
        assert dados[0]["total_respondidas"] == 1
    finally:
        app.dependency_overrides.clear()
