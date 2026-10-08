import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import get_settings
from app.core.persistencia.models.usuario import Usuario
from app.core.service.auth_service import FINALIDADE_ACESSO
from app.main import app
from app.web.dependencies import get_usuario_repository
from app.web.routers.vagas_router import get_analisador_service

client = TestClient(app)


class UsuarioRepositorioFalso:
    def __init__(self, usuario):
        self.usuario = usuario
        self.ids_buscados = []

    def buscar_por_id(self, id_usuario):
        self.ids_buscados.append(id_usuario)
        return self.usuario if id_usuario == self.usuario.id_usuario else None


class AnalisadorServiceFalso:
    def __init__(self):
        self.ids_usuario = []

    def listar_vagas_usuario(self, id_usuario):
        self.ids_usuario.append(id_usuario)
        return []


def _token(id_usuario):
    return jwt.encode(
        {
            "sub": str(id_usuario),
            "finalidade": FINALIDADE_ACESSO,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        get_settings().secret_key,
        algorithm="HS256",
    )


def test_rotas_protegidas_rejeitam_requisicoes_sem_token():
    app.dependency_overrides.clear()
    paths = [
        "/api/vagas?email=vitima@example.com",
        "/analises?email=vitima@example.com",
        "/analises/curriculos?email=vitima@example.com",
        "/templates?email=vitima@example.com",
        "/painel/historico?email=vitima@example.com",
        "/chat/mensagens?email=vitima@example.com",
        "/simulador?email=vitima@example.com",
        "/usuarios/me",
    ]

    try:
        for path in paths:
            assert client.get(path).status_code == 401, path
    finally:
        app.dependency_overrides.clear()


def test_rota_protegida_rejeita_token_invalido():
    response = client.get("/api/vagas", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


def test_rota_protegida_rejeita_token_com_subject_invalido():
    token = jwt.encode(
        {
            "sub": 123,
            "finalidade": FINALIDADE_ACESSO,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        get_settings().secret_key,
        algorithm="HS256",
    )

    response = client.get("/api/vagas", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_email_nao_altera_identidade_resolvida_pelo_token():
    id_usuario_token = uuid.uuid4()
    usuario = Usuario(
        id_usuario=id_usuario_token,
        nome="Usuário autenticado",
        email="autenticado@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    repositorio = UsuarioRepositorioFalso(usuario)
    service = AnalisadorServiceFalso()
    app.dependency_overrides[get_usuario_repository] = lambda: repositorio
    app.dependency_overrides[get_analisador_service] = lambda: service

    try:
        response = client.get(
            "/api/vagas",
            params={"email": "vitima@example.com"},
            headers={"Authorization": f"Bearer {_token(id_usuario_token)}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert repositorio.ids_buscados == [id_usuario_token]
    assert service.ids_usuario == [id_usuario_token]


def test_token_de_usuario_inexistente_retorna_401():
    usuario = Usuario(
        id_usuario=uuid.uuid4(),
        nome="Usuário",
        email="usuario@example.com",
        senha_hash="hash",
        perfil="candidato",
    )
    repositorio = UsuarioRepositorioFalso(usuario)
    app.dependency_overrides[get_usuario_repository] = lambda: repositorio

    try:
        response = client.get(
            "/api/vagas",
            headers={"Authorization": f"Bearer {_token(uuid.uuid4())}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
