from pydantic import BaseModel, EmailStr, Field


class SolicitarRecuperacaoSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str
