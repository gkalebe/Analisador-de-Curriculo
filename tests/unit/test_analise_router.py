import uuid

from fastapi.testclient import TestClient

from app.core.persistencia.models import Usuario, Vaga
from app.core.service.analisador_service import (
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
)
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
        self.settings = type("Settings", (), {"max_vaga_description_chars": 5000})()
        self.vagas_criadas: list[dict] = []
        self.deve_recusar_vazia = False
        self.deve_recusar_longa = False

    def cadastrar_vaga(self, id_usuario, descricao, titulo="", requisitos="", area=""):
        if self.deve_recusar_vazia:
            raise DescricaoVagaObrigatoriaError
        if self.deve_recusar_longa:
            raise DescricaoVagaMuitoLongaError
        vaga = Vaga(
            id_vaga=uuid.uuid4(),
            titulo=titulo or None,
            descricao=descricao,
            requisitos=requisitos or None,
            area=area or None,
            id_usuario=id_usuario,
        )
        self.vagas_criadas.append(vaga)
        return vaga

    def listar_vagas_usuario(self, id_usuario):
        return [vaga for vaga in self.vagas_criadas if vaga.id_usuario == id_usuario]


def _usuario() -> Usuario:
    return Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_formulario_sem_email_nao_lista_vagas():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.get("/analises/vagas/nova")

    app.dependency_overrides.clear()
    assert response.status_code == 200


def test_formulario_com_email_desconhecido_mostra_erro():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.get("/analises/vagas/nova", params={"email": "nao-cadastrado@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "Não encontramos um usuário" in response.text


def test_criar_vaga_com_sucesso():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises/vagas",
        data={
            "email": usuario.email,
            "titulo": "Dev Python",
            "descricao": "Vaga para desenvolvedor Python pleno.",
            "requisitos": "Python, SQL",
            "area": "Tecnologia",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "Vaga salva com sucesso" in response.text


def test_criar_vaga_com_email_desconhecido_retorna_400():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_analisador_service] = lambda: AnalisadorServiceFalso()

    response = client.post(
        "/analises/vagas",
        data={"email": "nao-cadastrado@example.com", "descricao": "Vaga qualquer."},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_criar_vaga_com_descricao_vazia_retorna_400():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_vazia = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises/vagas",
        data={"email": usuario.email, "descricao": "   "},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "obrigatória" in response.text


def test_criar_vaga_com_descricao_longa_retorna_400():
    usuario = _usuario()
    service_falso = AnalisadorServiceFalso()
    service_falso.deve_recusar_longa = True
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_analisador_service] = lambda: service_falso

    response = client.post(
        "/analises/vagas",
        data={"email": usuario.email, "descricao": "a" * 6000},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 400
    assert "no máximo" in response.text
