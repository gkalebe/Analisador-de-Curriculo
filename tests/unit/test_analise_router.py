import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.adapters.curriculo_parser.curriculo_parser import FormatoNaoSuportadoError
from app.core.persistencia.models import Usuario
from app.core.service.analisador_service import VagaNaoEncontradaError
from app.main import app
from app.web.routers.analise_router import get_analisador_service, get_usuario_repository

client = TestClient(app)


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[str, Usuario]):
        self.usuarios = usuarios

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)


class AnalisadorServiceFalso:
    def __init__(self):
        self.settings = type("Settings", (), {"max_upload_size_mb": 5})()
        self.deve_recusar_formato = False
        self.deve_recusar_vaga = False
        self.deve_recusar_nao_implementado = False
        self.uploads_processados: list[dict] = []
        self.analises_criadas: list[dict] = []
        self.analises_para_listar: list = []
        self.arquivo_curriculo: tuple[bytes, str] = (b"conteudo pdf", "curriculo.pdf")

    def processar_upload_curriculo(self, conteudo, nome_arquivo, extensao, id_usuario):
        if self.deve_recusar_formato:
            raise FormatoNaoSuportadoError(extensao)
        resultado = {
            "id_curriculo": str(uuid.uuid4()),
            "nome_arquivo": nome_arquivo,
            "tamanho_texto_extraido": len(conteudo),
        }
        self.uploads_processados.append(resultado)
        return resultado

    def analisar_curriculo_para_vaga(self, id_usuario, id_vaga, conteudo, nome_arquivo, extensao):
        if self.deve_recusar_formato:
            raise FormatoNaoSuportadoError(extensao)
        if self.deve_recusar_vaga:
            raise VagaNaoEncontradaError
        if self.deve_recusar_nao_implementado:
            raise NotImplementedError
        analise = SimpleNamespace(
            id_analise=uuid.uuid4(),
            id_curriculo=uuid.uuid4(),
            id_vaga=id_vaga,
            pontuacao=87.5,
            observacoes="Bom encaixe com a vaga.",
            data_analise=datetime.now(timezone.utc),
        )
        self.analises_criadas.append(analise)
        return analise

    def listar_analises_usuario(self, id_usuario):
        if self.deve_recusar_nao_implementado:
            raise NotImplementedError
        return self.analises_para_listar

    def obter_arquivo_curriculo(self, id_usuario, id_curriculo):
        return self.arquivo_curriculo


def _usuario() -> Usuario:
    return Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_upload_curriculo_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises/upload",
        data={"email": "nao-cadastrado@example.com"},
        files={"file": ("curriculo.pdf", b"conteudo qualquer", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_upload_curriculo_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises/upload",
        data={"email": usuario.email},
        files={"file": ("curriculo.pdf", b"conteudo do curriculo", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    corpo = response.json()
    assert corpo["nome_arquivo"] == "curriculo.pdf"
    assert corpo["tamanho_texto_extraido"] == len(b"conteudo do curriculo")


def test_upload_curriculo_com_formato_nao_suportado_retorna_400():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_formato = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises/upload",
        data={"email": usuario.email},
        files={"file": ("curriculo.txt", b"conteudo", "text/plain")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "Formato não suportado" in response.json()["detail"]


def test_upload_curriculo_com_arquivo_acima_do_limite_retorna_400():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    conteudo_grande = b"a" * (6 * 1024 * 1024)
    response = client.post(
        "/analises/upload",
        data={"email": usuario.email},
        files={"file": ("curriculo.pdf", conteudo_grande, "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "limite" in response.json()["detail"]


def test_criar_analise_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises",
        data={"email": "nao-cadastrado@example.com", "id_vaga": str(uuid.uuid4())},
        files={"file": ("curriculo.pdf", b"conteudo qualquer", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_criar_analise_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises",
        data={"email": usuario.email, "id_vaga": str(uuid.uuid4())},
        files={"file": ("curriculo.pdf", b"conteudo do curriculo", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 201
    corpo = response.json()
    assert corpo["pontuacao"] == 87.5
    assert corpo["observacoes"] == "Bom encaixe com a vaga."


def test_criar_analise_com_vaga_nao_encontrada_retorna_404():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_vaga = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises",
        data={"email": usuario.email, "id_vaga": str(uuid.uuid4())},
        files={"file": ("curriculo.pdf", b"conteudo", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 404
    assert "Vaga não encontrada" in response.json()["detail"]


def test_criar_analise_com_formato_nao_suportado_retorna_400():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_formato = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises",
        data={"email": usuario.email, "id_vaga": str(uuid.uuid4())},
        files={"file": ("curriculo.txt", b"conteudo", "text/plain")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "Formato não suportado" in response.json()["detail"]


def test_criar_analise_ainda_nao_implementada_retorna_501():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_nao_implementado = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises",
        data={"email": usuario.email, "id_vaga": str(uuid.uuid4())},
        files={"file": ("curriculo.pdf", b"conteudo", "application/pdf")},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 501


def test_listar_analises_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.get("/analises", params={"email": "nao-cadastrado@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_listar_analises_com_sucesso():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.analises_para_listar = [
        SimpleNamespace(
            id_analise=uuid.uuid4(),
            id_curriculo=uuid.uuid4(),
            id_vaga=uuid.uuid4(),
            pontuacao=42.0,
            observacoes="ok",
            data_analise=datetime.now(timezone.utc),
        )
    ]
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.get("/analises", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert len(response.json()["analises"]) == 1


def test_listar_analises_ainda_nao_implementada_retorna_501():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_nao_implementado = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.get("/analises", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 501


def test_baixar_arquivo_curriculo_pdf_retorna_content_disposition_inline():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.arquivo_curriculo = (b"conteudo pdf", "curriculo.pdf")
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.get(
        f"/analises/curriculos/{uuid.uuid4()}/download",
        params={"email": usuario.email},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("inline")


def test_baixar_arquivo_curriculo_docx_retorna_content_disposition_attachment():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.arquivo_curriculo = (b"conteudo docx", "curriculo.docx")
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.get(
        f"/analises/curriculos/{uuid.uuid4()}/download",
        params={"email": usuario.email},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment")
