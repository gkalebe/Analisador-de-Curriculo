import uuid
from unittest.mock import MagicMock

import pytest

from app.core.persistencia.models.curriculo import Curriculo
from app.core.persistencia.models.mensagem_chat import MensagemChat
from app.core.persistencia.models.vaga import Vaga
from app.core.service.chat_service import (
    ChatService,
    ContextoChatObrigatorioError,
    CurriculoNaoEncontradoError,
    CurriculoSemTextoError,
    PerguntaVaziaError,
    VagaNaoEncontradaError,
)


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def chat_service(mock_db):
    ai_adapter = MagicMock()
    ai_adapter.responder_chat.return_value = "Resposta simulada da IA."
    service = ChatService(db=mock_db, ai_service_adapter=ai_adapter)
    return service


def test_enviar_mensagem_apenas_curriculo(chat_service):
    id_usuario = uuid.uuid4()
    id_curriculo = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=id_curriculo,
        id_usuario=id_usuario,
        nome_arquivo="curriculo.pdf",
        texto_extraido="Experiência em Python e FastAPI.",
    )

    chat_service.curriculo_repository.buscar_por_id = MagicMock(return_value=curriculo)
    chat_service.chat_repository.listar = MagicMock(return_value=[])
    chat_service.chat_repository.criar = MagicMock(side_effect=lambda m: m)

    msg_user, msg_ai = chat_service.enviar_mensagem(
        id_usuario=id_usuario,
        pergunta="Como melhorar meu resumo?",
        id_curriculo=id_curriculo,
    )

    assert msg_user.autor == "usuario"
    assert msg_user.conteudo == "Como melhorar meu resumo?"
    assert msg_user.id_curriculo == id_curriculo
    assert msg_user.id_vaga is None

    assert msg_ai.autor == "assistente"
    assert msg_ai.conteudo == "Resposta simulada da IA."
    assert msg_ai.id_curriculo == id_curriculo
    assert msg_ai.id_vaga is None

    chat_service.ai_service_adapter.responder_chat.assert_called_once_with(
        texto_curriculo="Experiência em Python e FastAPI.",
        historico=[],
        pergunta="Como melhorar meu resumo?",
        texto_vaga=None,
    )


def test_enviar_mensagem_apenas_vaga(chat_service):
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()
    vaga = Vaga(
        id_vaga=id_vaga,
        id_usuario=id_usuario,
        titulo="Desenvolvedor Python",
        area="Tecnologia",
        requisitos="Python, Docker, SQL",
        descricao="Desenvolvimento de APIs robustas.",
    )

    chat_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    chat_service.chat_repository.listar = MagicMock(return_value=[])
    chat_service.chat_repository.criar = MagicMock(side_effect=lambda m: m)

    msg_user, msg_ai = chat_service.enviar_mensagem(
        id_usuario=id_usuario,
        pergunta="Quais são os requisitos principais desta vaga?",
        id_vaga=id_vaga,
    )

    assert msg_user.id_curriculo is None
    assert msg_user.id_vaga == id_vaga
    assert msg_ai.id_vaga == id_vaga

    chamada_args = chat_service.ai_service_adapter.responder_chat.call_args[1]
    assert chamada_args["texto_curriculo"] is None
    assert "Desenvolvedor Python" in chamada_args["texto_vaga"]
    assert "Python, Docker, SQL" in chamada_args["texto_vaga"]


def test_enviar_mensagem_curriculo_e_vaga_correlacionados(chat_service):
    id_usuario = uuid.uuid4()
    id_curriculo = uuid.uuid4()
    id_vaga = uuid.uuid4()

    curriculo = Curriculo(
        id_curriculo=id_curriculo,
        id_usuario=id_usuario,
        nome_arquivo="curriculo.pdf",
        texto_extraido="Engenheiro de Software com experiência em Go e Kubernetes.",
    )
    vaga = Vaga(
        id_vaga=id_vaga,
        id_usuario=id_usuario,
        titulo="Tech Lead Backend",
        descricao="Liderança de times e sistemas distribuídos.",
    )

    chat_service.curriculo_repository.buscar_por_id = MagicMock(return_value=curriculo)
    chat_service.vaga_repository.buscar_por_id = MagicMock(return_value=vaga)
    chat_service.chat_repository.listar = MagicMock(return_value=[])
    chat_service.chat_repository.criar = MagicMock(side_effect=lambda m: m)

    msg_user, msg_ai = chat_service.enviar_mensagem(
        id_usuario=id_usuario,
        pergunta="Como adequar meu perfil para essa vaga de liderança?",
        id_curriculo=id_curriculo,
        id_vaga=id_vaga,
    )

    assert msg_user.id_curriculo == id_curriculo
    assert msg_user.id_vaga == id_vaga
    assert msg_ai.id_curriculo == id_curriculo
    assert msg_ai.id_vaga == id_vaga

    chamada_args = chat_service.ai_service_adapter.responder_chat.call_args[1]
    assert "Engenheiro de Software" in chamada_args["texto_curriculo"]
    assert "Tech Lead Backend" in chamada_args["texto_vaga"]


def test_enviar_mensagem_sem_contexto_lanca_erro(chat_service):
    id_usuario = uuid.uuid4()
    with pytest.raises(ContextoChatObrigatorioError):
        chat_service.enviar_mensagem(
            id_usuario=id_usuario,
            pergunta="Olá",
            id_curriculo=None,
            id_vaga=None,
        )


def test_enviar_mensagem_pergunta_vazia_lanca_erro(chat_service):
    id_usuario = uuid.uuid4()
    with pytest.raises(PerguntaVaziaError):
        chat_service.enviar_mensagem(
            id_usuario=id_usuario,
            pergunta="   ",
            id_curriculo=uuid.uuid4(),
        )


def test_enviar_mensagem_curriculo_nao_encontrado(chat_service):
    id_usuario = uuid.uuid4()
    chat_service.curriculo_repository.buscar_por_id = MagicMock(return_value=None)
    with pytest.raises(CurriculoNaoEncontradoError):
        chat_service.enviar_mensagem(
            id_usuario=id_usuario,
            pergunta="Dúvida",
            id_curriculo=uuid.uuid4(),
        )


def test_enviar_mensagem_curriculo_sem_texto(chat_service):
    id_usuario = uuid.uuid4()
    id_curriculo = uuid.uuid4()
    curriculo = Curriculo(
        id_curriculo=id_curriculo,
        id_usuario=id_usuario,
        nome_arquivo="curriculo.pdf",
        texto_extraido=None,
    )
    chat_service.curriculo_repository.buscar_por_id = MagicMock(return_value=curriculo)
    with pytest.raises(CurriculoSemTextoError):
        chat_service.enviar_mensagem(
            id_usuario=id_usuario,
            pergunta="Dúvida",
            id_curriculo=id_curriculo,
        )


def test_enviar_mensagem_vaga_nao_encontrada(chat_service):
    id_usuario = uuid.uuid4()
    chat_service.vaga_repository.buscar_por_id = MagicMock(return_value=None)
    with pytest.raises(VagaNaoEncontradaError):
        chat_service.enviar_mensagem(
            id_usuario=id_usuario,
            pergunta="Dúvida",
            id_vaga=uuid.uuid4(),
        )


def test_encerrar_conversa_extrai_perguntas_e_apaga_mensagens(chat_service):
    id_usuario = uuid.uuid4()
    id_curriculo = uuid.uuid4()
    mensagens = [
        MensagemChat(
            id_mensagem=uuid.uuid4(),
            id_usuario=id_usuario,
            id_curriculo=id_curriculo,
            autor="usuario",
            conteudo="Como melhorar meu resumo?",
        ),
        MensagemChat(
            id_mensagem=uuid.uuid4(),
            id_usuario=id_usuario,
            id_curriculo=id_curriculo,
            autor="assistente",
            conteudo="Resposta simulada da IA.",
        ),
    ]

    chat_service.chat_repository.listar = MagicMock(return_value=mensagens)
    chat_service.chat_repository.excluir = MagicMock()
    chat_service.pergunta_repository.criar_lote = MagicMock()

    total_removidas = chat_service.encerrar_conversa(id_usuario=id_usuario, id_curriculo=id_curriculo)

    assert total_removidas == 2
    chat_service.pergunta_repository.criar_lote.assert_called_once_with(["Como melhorar meu resumo?"])
    chat_service.chat_repository.excluir.assert_called_once_with(mensagens)


def test_encerrar_conversa_sem_mensagens_nao_chama_repositorios(chat_service):
    id_usuario = uuid.uuid4()
    id_vaga = uuid.uuid4()

    chat_service.chat_repository.listar = MagicMock(return_value=[])
    chat_service.chat_repository.excluir = MagicMock()
    chat_service.pergunta_repository.criar_lote = MagicMock()

    total_removidas = chat_service.encerrar_conversa(id_usuario=id_usuario, id_vaga=id_vaga)

    assert total_removidas == 0
    chat_service.pergunta_repository.criar_lote.assert_not_called()
    chat_service.chat_repository.excluir.assert_not_called()


def test_encerrar_conversa_sem_contexto_lanca_erro(chat_service):
    id_usuario = uuid.uuid4()
    with pytest.raises(ContextoChatObrigatorioError):
        chat_service.encerrar_conversa(id_usuario=id_usuario)


def test_listar_historico_validacoes(chat_service):
    id_usuario = uuid.uuid4()

    # Sem contexto
    with pytest.raises(ContextoChatObrigatorioError):
        chat_service.listar_historico(id_usuario)

    # Curriculo inexistente
    chat_service.curriculo_repository.buscar_por_id = MagicMock(return_value=None)
    with pytest.raises(CurriculoNaoEncontradoError):
        chat_service.listar_historico(id_usuario, id_curriculo=uuid.uuid4())

    # Vaga inexistente
    chat_service.vaga_repository.buscar_por_id = MagicMock(return_value=None)
    with pytest.raises(VagaNaoEncontradaError):
        chat_service.listar_historico(id_usuario, id_vaga=uuid.uuid4())
