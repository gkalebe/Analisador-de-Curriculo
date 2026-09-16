from pydantic import BaseModel


class TemplatePreviewFicticio(BaseModel):
    nome: str
    email: str
    telefone: str
    resumo: str
    experiencia_profissional: str
    formacao: str
    habilidades: str


class TemplateResponse(BaseModel):
    id_template: str
    nome: str
    descricao: str
    preview_ficticio: TemplatePreviewFicticio


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
