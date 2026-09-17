import uuid

from fastapi.testclient import TestClient

from app.core.persistencia.models.usuario import Usuario
from app.main import app
from app.web.routers.painel_router import get_plano_service, get_usuario_repository

client = TestClient(app)


class UsuarioRepositorioFalso:
    def __init__(self, usuarios: dict[str, Usuario]):
        self.usuarios = usuarios

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)


class PlanoServiceFalso:
    def __init__(self):
        self.resultado = {"historico": [], "lacunas_recorrentes": []}

    def obter_historico_e_lacunas(self, id_usuario):
        return self.resultado


def _usuario() -> Usuario:
    return Usuario(
        id_usuario=uuid.uuid4(),
        nome="Gabriel Kalebe",
        email="gabriel@example.com",
        senha_hash="hash",
        perfil="candidato",
    )


def test_obter_historico_com_email_desconhecido_retorna_404():
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({})
    app.dependency_overrides[get_plano_service] = lambda: PlanoServiceFalso()

    response = client.get("/painel/historico", params={"email": "nao-cadastrado@example.com"})

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_obter_historico_com_sucesso():
    usuario = _usuario()
    service_falso = PlanoServiceFalso()
    service_falso.resultado = {
        "historico": [
            {
                "id_analise": uuid.uuid4(),
                "data_analise": "2026-09-16T12:00:00Z",
                "vaga_titulo": "Dev Backend",
                "pontuacao": 85.0,
            }
        ],
        "lacunas_recorrentes": [{"competencia": "Docker", "frequencia": 2}],
    }
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_plano_service] = lambda: service_falso

    response = client.get("/painel/historico", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    corpo = response.json()
    assert corpo["historico"][0]["vaga_titulo"] == "Dev Backend"
    assert corpo["lacunas_recorrentes"][0]["competencia"] == "Docker"


def test_obter_historico_sem_analises_retorna_listas_vazias():
    usuario = _usuario()
    app.dependency_overrides[get_usuario_repository] = lambda: UsuarioRepositorioFalso({usuario.email: usuario})
    app.dependency_overrides[get_plano_service] = lambda: PlanoServiceFalso()

    response = client.get("/painel/historico", params={"email": usuario.email})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    corpo = response.json()
    assert corpo["historico"] == []
    assert corpo["lacunas_recorrentes"] == []
