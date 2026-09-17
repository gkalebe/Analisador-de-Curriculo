import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ChatMensagemRequest(BaseModel):
    email: EmailStr
    pergunta: str = Field(min_length=1)


class MensagemChatResponse(BaseModel):
    id_mensagem: uuid.UUID
    autor: str
    conteudo: str
    data_envio: datetime

    model_config = {"from_attributes": True}


class ChatHistoricoResponse(BaseModel):
    mensagens: list[MensagemChatResponse]


class ChatEnviarResponse(BaseModel):
    mensagem_usuario: MensagemChatResponse
    mensagem_assistente: MensagemChatResponse
