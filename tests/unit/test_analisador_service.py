import uuid

import pytest

from app.core.persistencia.models import Vaga
from app.core.service.analisador_service import (
    AnalisadorService,
    DescricaoVagaMuitoLongaError,
    DescricaoVagaObrigatoriaError,
)


class VagaRepositorioFalso:
    def __init__(self):
        self.vagas: list[Vaga] = []

    def criar(self, vaga: Vaga) -> Vaga:
        vaga.id_vaga = uuid.uuid4()
        self.vagas.append(vaga)
        return vaga

    def buscar_por_id(self, id_vaga: uuid.UUID) -> Vaga | None:
        return next((vaga for vaga in self.vagas if vaga.id_vaga == id_vaga), None)

    def listar_por_usuario(self, id_usuario: uuid.UUID) -> list[Vaga]:
        return [vaga for vaga in self.vagas if vaga.id_usuario == id_usuario]


def _criar_service_com_fake() -> tuple[AnalisadorService, VagaRepositorioFalso]:
    service = AnalisadorService(db=None)
    fake = VagaRepositorioFalso()
    service.vaga_repository = fake
    return service, fake


def test_cadastrar_vaga_persiste_com_dados_completos():
    service, fake = _criar_service_com_fake()
    id_usuario = uuid.uuid4()

    vaga = service.cadastrar_vaga(
        id_usuario=id_usuario,
        descricao="Vaga para desenvolvedor Python.",
        titulo="Dev Python",
        requisitos="Python, SQL",
        area="Tecnologia",
    )

    assert vaga in fake.vagas
    assert vaga.titulo == "Dev Python"
    assert vaga.id_usuario == id_usuario


def test_cadastrar_vaga_aceita_apenas_descricao_obrigatoria():
    service, _ = _criar_service_com_fake()

    vaga = service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="Descrição mínima da vaga.")

    assert vaga.titulo is None
    assert vaga.requisitos is None
    assert vaga.area is None


def test_cadastrar_vaga_rejeita_descricao_vazia():
    service, _ = _criar_service_com_fake()

    with pytest.raises(DescricaoVagaObrigatoriaError):
        service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="   ")


def test_cadastrar_vaga_rejeita_descricao_acima_do_limite():
    service, _ = _criar_service_com_fake()
    service.settings = type("Settings", (), {"max_vaga_description_chars": 10})()

    with pytest.raises(DescricaoVagaMuitoLongaError):
        service.cadastrar_vaga(id_usuario=uuid.uuid4(), descricao="a" * 11)


def test_listar_vagas_usuario_retorna_apenas_do_usuario():
    service, fake = _criar_service_com_fake()
    id_usuario = uuid.uuid4()
    outro_usuario = uuid.uuid4()
    service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga do usuário")
    service.cadastrar_vaga(id_usuario=outro_usuario, descricao="Vaga de outro usuário")

    vagas = service.listar_vagas_usuario(id_usuario)

    assert len(vagas) == 1
    assert vagas[0].id_usuario == id_usuario
