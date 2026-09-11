import re
import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

REGRAS_SENHA = (
    "mínimo de 8 caracteres",
    "pelo menos 1 letra maiúscula",
    "pelo menos 1 número",
)


def validar_regras_senha(senha: str) -> str:
    regras_violadas = []
    if len(senha) < 8:
        regras_violadas.append(REGRAS_SENHA[0])
    if not re.search(r"[A-Z]", senha):
        regras_violadas.append(REGRAS_SENHA[1])
    if not re.search(r"\d", senha):
        regras_violadas.append(REGRAS_SENHA[2])

    if regras_violadas:
        raise ValueError(f"Senha não atende às regras mínimas: {', '.join(regras_violadas)}.")
    return senha


class SolicitarRecuperacaoSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=8, max_length=128)


class CadastrarUsuarioRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=150)
    data_nascimento: date
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("Nome não pode ser vazio.")
        return valor.strip()

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, valor: str) -> str:
        return validar_regras_senha(valor)


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class UsuarioResponse(BaseModel):
    id_usuario: uuid.UUID
    nome: str
    email: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


class MensagemResponse(BaseModel):
    mensagem: str
