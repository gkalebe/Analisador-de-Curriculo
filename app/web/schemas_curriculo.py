import uuid

from pydantic import BaseModel


class CurriculoResponse(BaseModel):
    id_curriculo: uuid.UUID
    nome_arquivo: str
    tamanho_texto_extraido: int
