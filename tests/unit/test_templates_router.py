import uuid

from fastapi.testclient import TestClient

from app.core.persistencia.models.usuario import Usuario
from app.core.service.template_service import (
    TEMPLATES,
    CurriculoNaoEncontradoError,
    FormatoExportacaoInvalidoError,
    NenhumaAnaliseEncontradaError,
    TemplateNaoEncontradoError,
    VersaoExportacaoInvalidaError,
)
from app.main import app
from app.web.routers.templates_router import get_template_service, get_usuario_repository

client = TestClient(app)


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[str, Usuario]):
        self.usuarios = usuarios

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)


class TemplateServiceFalso:
    def __init__(self):
        self.deve_recusar_sem_analise = False
        self.deve_recusar_curriculo = False
        self.deve_recusar_template = False
        self.deve_recusar_formato = False
        self.deve_recusar_versao = False
        self.conteudo_exportado = (b"conteudo-pdf", "curriculo.pdf", "application/pdf")
        self.ultima_versao_recebida = None

    def listar_templates(self, id_usuario):
        if self.deve_recusar_sem_analise:
            raise NenhumaAnaliseEncontradaError
        return TEMPLATES

    def exportar_curriculo(self, id_usuario, id_curriculo, id_template, formato, versao="original"):
        self.ultima_versao_recebida = versao
        if self.deve_recusar_curriculo:
            raise CurriculoNaoEncontradoError
        if self.deve_recusar_template:
            raise TemplateNaoEncontradoError(id_template)
        if self.deve_recusar_formato:
            raise FormatoExportacaoInvalidoError(formato)
        if self.deve_recusar_versao:
            raise VersaoExportacaoInvalidaError(versao)
        return self.conteudo_exportado


def _usuario() -> Usuario:
    return Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_listar_templates_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_template_service] = lambda: TemplateServiceFalso()

    response = client.get("/templates", params={"email": "nao-cadastrado@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_listar_templates_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: TemplateServiceFalso()

    response = client.get("/templates", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    corpo = response.json()
    assert len(corpo["templates"]) >= 3


def test_listar_templates_sem_analise_retorna_403():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    service_falso.deve_recusar_sem_analise = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get("/templates", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 403


def test_exportar_curriculo_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_template_service] = lambda: TemplateServiceFalso()

    response = client.get(
        "/templates/exportar",
        params={
            "email": "nao-cadastrado@example.com",
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "pdf",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_exportar_curriculo_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: TemplateServiceFalso()

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "pdf",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"conteudo-pdf"


def test_exportar_curriculo_com_curriculo_nao_encontrado_retorna_404():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    service_falso.deve_recusar_curriculo = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "pdf",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_exportar_curriculo_com_template_invalido_retorna_404():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    service_falso.deve_recusar_template = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "inexistente",
            "formato": "pdf",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_exportar_curriculo_com_formato_invalido_retorna_400():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    service_falso.deve_recusar_formato = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "jpg",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_exportar_curriculo_com_versao_invalida_retorna_400():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    service_falso.deve_recusar_versao = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "pdf",
            "versao": "rascunho",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_exportar_curriculo_repassa_versao_default_original():
    usuario = _usuario()
    service_falso = TemplateServiceFalso()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_template_service] = lambda: service_falso

    response = client.get(
        "/templates/exportar",
        params={
            "email": usuario.email,
            "id_curriculo": str(uuid.uuid4()),
            "id_template": "moderno",
            "formato": "pdf",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert service_falso.ultima_versao_recebida == "original"
