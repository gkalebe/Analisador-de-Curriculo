import uuid
from datetime import datetime
from unittest.mock import MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.persistencia.models.mensagem_chat import MensagemChat
from app.core.persistencia.models.usuario import Usuario
from app.main import app
from app.web.routers.chat_router import get_chat_service, get_usuario_repository

client = TestClient(app)


def test_enviar_mensagem_usuario_nao_encontrado():
    repo_falso = MagicMock()
    repo_falso.buscar_por_email.return_value = None

    app.dependency_overrides[get_usuario_repository] = lambda: repo_falso
    try:
        response = client.post(
            "/chat/mensagens",
            json={
                "email": "desconhecido@example.com",
                "pergunta": "Qualquer coisa",
                "id_curriculo": str(uuid.uuid4()),
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Não encontramos um usuário" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_enviar_mensagem_com_sucesso():
    id_usuario = uuid.uuid4()
    id_curriculo = uuid.uuid4()
    id_vaga = uuid.uuid4()

    usuario = Usuario(
        id_usuario=id_usuario,
        nome="Teste",
        email="teste@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    chat_servico = MagicMock()
    agora = datetime.now()
    msg_user = MensagemChat(
        id_mensagem=uuid.uuid4(),
        id_usuario=id_usuario,
        id_curriculo=id_curriculo,
        id_vaga=id_vaga,
        autor="usuario",
        conteudo="Qual a aderência?",
        data_envio=agora,
    )
    msg_ai = MensagemChat(
        id_mensagem=uuid.uuid4(),
        id_usuario=id_usuario,
        id_curriculo=id_curriculo,
        id_vaga=id_vaga,
        autor="assistente",
        conteudo="Excelente aderência!",
        data_envio=agora,
    )
    chat_servico.enviar_mensagem.return_value = (msg_user, msg_ai)

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_chat_service] = lambda: chat_servico
    try:
        response = client.post(
            "/chat/mensagens",
            json={
                "email": "teste@example.com",
                "pergunta": "Qual a aderência?",
                "id_curriculo": str(id_curriculo),
                "id_vaga": str(id_vaga),
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        dados = response.json()
        assert dados["mensagem_usuario"]["conteudo"] == "Qual a aderência?"
        assert dados["mensagem_assistente"]["conteudo"] == "Excelente aderência!"
        assert dados["mensagem_usuario"]["id_vaga"] == str(id_vaga)
    finally:
        app.dependency_overrides.clear()


def test_listar_mensagens_geral():
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()

    usuario = Usuario(
        id_usuario=id_usuario,
        nome="Teste",
        email="teste@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    chat_servico = MagicMock()
    msg = MensagemChat(
        id_mensagem=uuid.uuid4(),
        id_usuario=id_usuario,
        id_curriculo=None,
        id_vaga=id_vaga,
        autor="usuario",
        conteudo="Dúvida da vaga",
        data_envio=datetime.now(),
    )
    chat_servico.listar_historico.return_value = [msg]

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_chat_service] = lambda: chat_servico
    try:
        response = client.get(f"/chat/mensagens?email=teste@example.com&id_vaga={id_vaga}")
        assert response.status_code == status.HTTP_200_OK
        dados = response.json()
        assert len(dados["mensagens"]) == 1
        assert dados["mensagens"][0]["conteudo"] == "Dúvida da vaga"
        assert dados["mensagens"][0]["id_vaga"] == str(id_vaga)
    finally:
        app.dependency_overrides.clear()


def test_rotas_especificas_vaga():
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()

    usuario = Usuario(
        id_usuario=id_usuario,
        nome="Teste",
        email="teste@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    repo_usuario = MagicMock()
    repo_usuario.buscar_por_email.return_value = usuario

    chat_servico = MagicMock()
    agora = datetime.now()
    msg_user = MensagemChat(
        id_mensagem=uuid.uuid4(),
        id_usuario=id_usuario,
        id_curriculo=None,
        id_vaga=id_vaga,
        autor="usuario",
        conteudo="Sobre a vaga",
        data_envio=agora,
    )
    msg_ai = MensagemChat(
        id_mensagem=uuid.uuid4(),
        id_usuario=id_usuario,
        id_curriculo=None,
        id_vaga=id_vaga,
        autor="assistente",
        conteudo="Explicação da vaga",
        data_envio=agora,
    )
    chat_servico.enviar_mensagem.return_value = (msg_user, msg_ai)
    chat_servico.listar_historico.return_value = [msg_user, msg_ai]

    app.dependency_overrides[get_usuario_repository] = lambda: repo_usuario
    app.dependency_overrides[get_chat_service] = lambda: chat_servico
    try:
        # POST /chat/vagas/{id_vaga}/mensagens
        resp_post = client.post(
            f"/chat/vagas/{id_vaga}/mensagens",
            json={"email": "teste@example.com", "pergunta": "Sobre a vaga"},
        )
        assert resp_post.status_code == status.HTTP_201_CREATED

        # GET /chat/vagas/{id_vaga}/mensagens
        resp_get = client.get(f"/chat/vagas/{id_vaga}/mensagens?email=teste@example.com")
        assert resp_get.status_code == status.HTTP_200_OK
        assert len(resp_get.json()["mensagens"]) == 2
    finally:
        app.dependency_overrides.clear()
