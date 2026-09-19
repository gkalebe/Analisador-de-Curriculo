import uuid

from sqlalchemy.orm import Session

from app.adapters.ai_service.ai_service_adapter import AIServiceAdapter
from app.core.persistencia.chat_repository import ChatRepository
from app.core.persistencia.curriculo_repository import CurriculoRepository
from app.core.persistencia.models.mensagem_chat import MensagemChat
from app.core.persistencia.pergunta_anonimizada_repository import PerguntaAnonimizadaRepository
from app.core.persistencia.vaga_repository import VagaRepository


class CurriculoNaoEncontradoError(Exception):
    pass


class CurriculoSemTextoError(Exception):
    pass


class VagaNaoEncontradaError(Exception):
    pass


class ContextoChatObrigatorioError(Exception):
    pass


class PerguntaVaziaError(Exception):
    pass


class ChatService:
    def __init__(self, db: Session, ai_service_adapter: AIServiceAdapter | None = None):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.curriculo_repository = CurriculoRepository(db)
        self.vaga_repository = VagaRepository(db)
        self.pergunta_repository = PerguntaAnonimizadaRepository(db)
        self.ai_service_adapter = ai_service_adapter or AIServiceAdapter()

    @staticmethod
    def _montar_texto_vaga(vaga) -> str:
        partes = []
        if getattr(vaga, "titulo", None):
            partes.append(f"Título da Vaga: {vaga.titulo}")
        if getattr(vaga, "area", None):
            partes.append(f"Área: {vaga.area}")
        if getattr(vaga, "requisitos", None):
            partes.append(f"Requisitos:\n{vaga.requisitos}")
        if getattr(vaga, "descricao", None):
            partes.append(f"Descrição da Vaga:\n{vaga.descricao}")
        return "\n\n".join(partes)

    def enviar_mensagem(
        self,
        id_usuario: uuid.UUID,
        pergunta: str | uuid.UUID | None = None,
        id_curriculo: uuid.UUID | str | None = None,
        id_vaga: uuid.UUID | None = None,
    ) -> tuple[MensagemChat, MensagemChat]:
        # Suporte retrocompatível para chamada legada: enviar_mensagem(id_usuario, id_curriculo, pergunta)
        if isinstance(pergunta, uuid.UUID):
            id_curriculo_resolvido = pergunta
            pergunta_resolvida = str(id_curriculo or "")
            id_vaga_resolvido = id_vaga
        else:
            id_curriculo_resolvido = id_curriculo if isinstance(id_curriculo, uuid.UUID) else None
            pergunta_resolvida = str(pergunta or "")
            id_vaga_resolvido = id_vaga

        pergunta_normalizada = pergunta_resolvida.strip()
        if not pergunta_normalizada:
            raise PerguntaVaziaError

        if id_curriculo_resolvido is None and id_vaga_resolvido is None:
            raise ContextoChatObrigatorioError("Selecione um currículo, uma vaga ou ambos para conversar.")

        texto_curriculo: str | None = None
        if id_curriculo_resolvido is not None:
            curriculo = self.curriculo_repository.buscar_por_id(id_curriculo_resolvido)
            if curriculo is None or curriculo.id_usuario != id_usuario:
                raise CurriculoNaoEncontradoError
            if not curriculo.texto_extraido:
                raise CurriculoSemTextoError
            texto_curriculo = curriculo.texto_extraido

        texto_vaga: str | None = None
        if id_vaga_resolvido is not None:
            vaga = self.vaga_repository.buscar_por_id(id_vaga_resolvido)
            if vaga is None or vaga.id_usuario != id_usuario:
                raise VagaNaoEncontradaError
            texto_vaga = self._montar_texto_vaga(vaga)

        mensagens_anteriores = self.chat_repository.listar(
            id_usuario, id_curriculo=id_curriculo_resolvido, id_vaga=id_vaga_resolvido
        )
        historico = [(mensagem.autor, mensagem.conteudo) for mensagem in mensagens_anteriores]

        # Só gravamos a pergunta do usuário DEPOIS que a IA responder com sucesso. Se
        # persistíssemos antes e a chamada à IA falhasse (ex.: indisponibilidade
        # temporária do Gemini), a pergunta ficava salva sem resposta — órfã no
        # histórico para sempre, aparecendo como um espaço em branco na conversa.
        resposta_texto = self.ai_service_adapter.responder_chat(
            texto_curriculo=texto_curriculo,
            historico=historico,
            pergunta=pergunta_normalizada,
            texto_vaga=texto_vaga,
        )

        mensagem_usuario = self.chat_repository.criar(
            MensagemChat(
                id_usuario=id_usuario,
                id_curriculo=id_curriculo_resolvido,
                id_vaga=id_vaga_resolvido,
                autor="usuario",
                conteudo=pergunta_normalizada,
            )
        )

        mensagem_assistente = self.chat_repository.criar(
            MensagemChat(
                id_usuario=id_usuario,
                id_curriculo=id_curriculo_resolvido,
                id_vaga=id_vaga_resolvido,
                autor="assistente",
                conteudo=resposta_texto.strip(),
            )
        )

        return mensagem_usuario, mensagem_assistente

    def listar_historico(
        self,
        id_usuario: uuid.UUID,
        id_curriculo: uuid.UUID | None = None,
        id_vaga: uuid.UUID | None = None,
    ) -> list[MensagemChat]:
        if id_curriculo is None and id_vaga is None:
            raise ContextoChatObrigatorioError("Selecione um currículo, uma vaga ou ambos.")

        if id_curriculo is not None:
            curriculo = self.curriculo_repository.buscar_por_id(id_curriculo)
            if curriculo is None or curriculo.id_usuario != id_usuario:
                raise CurriculoNaoEncontradoError

        if id_vaga is not None:
            vaga = self.vaga_repository.buscar_por_id(id_vaga)
            if vaga is None or vaga.id_usuario != id_usuario:
                raise VagaNaoEncontradaError

        return self.chat_repository.listar(id_usuario, id_curriculo=id_curriculo, id_vaga=id_vaga)

    def encerrar_conversa(
        self,
        id_usuario: uuid.UUID,
        id_curriculo: uuid.UUID | None = None,
        id_vaga: uuid.UUID | None = None,
    ) -> int:
        """
        Encerra (sai d)o ChatBOT: extrai as perguntas do usuário para a árvore de dados —
        só o texto da pergunta, anonimizado, sem resposta e sem nenhum vínculo com o usuário,
        currículo ou vaga — e então apaga a conversa inteira do banco.
        """
        if id_curriculo is None and id_vaga is None:
            raise ContextoChatObrigatorioError("Selecione um currículo, uma vaga ou ambos.")

        mensagens = self.chat_repository.listar(id_usuario, id_curriculo=id_curriculo, id_vaga=id_vaga)
        if not mensagens:
            return 0

        perguntas = [m.conteudo for m in mensagens if m.autor == "usuario" and m.conteudo and m.conteudo.strip()]
        if perguntas:
            self.pergunta_repository.criar_lote(perguntas)

        self.chat_repository.excluir(mensagens)
        return len(mensagens)
