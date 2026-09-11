from datetime import date

from pydantic import BaseModel, EmailStr, Field


class CadastrarUsuarioRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    data_nascimento: date
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class UsuarioResponse(BaseModel):
    id_usuario: str
    mensagem: str


class SolicitarExclusaoResponse(BaseModel):
    token_confirmacao: str
    mensagem: str


class ConfirmarExclusaoRequest(BaseModel):
    token: str = Field(min_length=1)


class SolicitarRecuperacaoSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=8, max_length=128)


class MensagemResponse(BaseModel):
    mensagem: str
