import uuid

from fastapi.testclient import TestClient

from app.adapters.curriculo_parser.curriculo_parser import FormatoNaoSuportadoError
from app.core.persistencia.models import Usuario
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
        self.uploads_processados: list[dict] = []

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
