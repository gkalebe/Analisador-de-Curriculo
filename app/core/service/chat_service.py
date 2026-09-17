import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.core.persistencia.chat_repository import ChatRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models.mensagem_chat import MensagemChat


class CurriculoNaoEncontradoError(Exception):
    pass


class CurriculoSemTextoError(Exception):
    pass


class PerguntaVaziaError(Exception):
    pass


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.curriculo_repository = CurriculoRepository(db)
        self.ai_service_adapter = AIServiceAdapter()

    def enviar_mensagem(
        self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID, pergunta: str
    ) -> tuple[MensagemChat, MensagemChat]:
        pergunta_normalizada = (pergunta or "").strip()
        if not pergunta_normalizada:
            raise PerguntaVaziaError

        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        if not curriculo.texto_extraido:
            raise CurriculoSemTextoError

        mensagens_anteriores = self.chat_repository.listar_por_curriculo(id_usuario, id_curriculo)
        historico = [(mensagem.autor, mensagem.conteudo) for mensagem in mensagens_anteriores]

        mensagem_usuario = self.chat_repository.criar(
            MensagemChat(
                id_usuario=id_usuario,
                id_curriculo=id_curriculo,
                autor="usuario",
                conteudo=pergunta_normalizada,
            )
        )

        resposta_texto = self.ai_service_adapter.responder_chat_curriculo(
            curriculo.texto_extraido, historico, pergunta_normalizada
        )

        mensagem_assistente = self.chat_repository.criar(
            MensagemChat(
                id_usuario=id_usuario,
                id_curriculo=id_curriculo,
                autor="assistente",
                conteudo=resposta_texto.strip(),
            )
        )

        return mensagem_usuario, mensagem_assistente

    def listar_historico(self, id_usuario: uuid.UUID, id_curriculo: uuid.UUID) -> list[MensagemChat]:
        curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
        if curriculo is None or curriculo.id_usuario != id_usuario:
            raise CurriculoNaoEncontradoError

        return self.chat_repository.listar_por_curriculo(id_usuario, id_curriculo)
