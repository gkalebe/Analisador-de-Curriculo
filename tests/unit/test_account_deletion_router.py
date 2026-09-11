import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import get_settings
from app.main import app
from app.web.routers.auth_router import get_auth_service

client = TestClient(app)


class FakeUser:
    def __init__(self):
        self.id_usuario = uuid.uuid4()
        self.nome = "Andre"
        self.email = "andre@example.com"
        self.exclusao_solicitada_em = None


class FakeRepository:
    def __init__(self, user):
        self.user = user
        self.deleted = False

    def buscar_por_id(self, user_id):
        return self.user if user_id == self.user.id_usuario and not self.deleted else None

    def atualizar(self, user):
        return user

    def excluir(self, user):
        self.deleted = True


class FakeAuthService:
    def __init__(self):
        self.user = FakeUser()
        self.usuario_repository = FakeRepository(self.user)

    def solicitar_exclusao_conta(self, user_id):
        self.user.exclusao_solicitada_em = datetime.now(timezone.utc)
        return self.user

    def cancelar_exclusao_conta(self, user_id):
        self.user.exclusao_solicitada_em = None
        return self.user

    def confirmar_exclusao_conta(self, user_id):
        self.usuario_repository.excluir(self.user)


def _token(service):
    return jwt.encode(
        {
            "sub": str(service.user.id_usuario),
            "finalidade": "acesso",
            "exp": datetime.now(timezone.utc).timestamp() + 300,
        },
        get_settings().secret_key,
        algorithm="HS256",
    )


def test_fluxo_de_exclusao_tem_solicitacao_cancelamento_e_confirmacao():
    service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    headers = {"Authorization": f"Bearer {_token(service)}"}

    solicitacao = client.post("/usuarios/exclusao", headers=headers)
    assert solicitacao.status_code == 202
    assert service.user.exclusao_solicitada_em is not None

    cancelamento = client.post("/usuarios/exclusao/cancelar", headers=headers)
    assert cancelamento.status_code == 200
    assert service.user.exclusao_solicitada_em is None
    assert service.usuario_repository.deleted is False

    client.post("/usuarios/exclusao", headers=headers)
    confirmacao = client.post("/usuarios/exclusao/confirmar", headers=headers)

    app.dependency_overrides.clear()
    assert confirmacao.status_code == 200
    assert service.usuario_repository.deleted is True


def test_exclusao_rejeita_requisicao_sem_bearer():
    response = client.post("/usuarios/exclusao")

    assert response.status_code == 401
