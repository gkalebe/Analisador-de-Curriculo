import uuid

from app.core.persistencia.models import Analise, Curriculo, Vaga
from app.core.service.plano_service import PlanoService


class AnaliseRepositorioFalso:
    def __init__(self, analises=None):
        self.analises = analises or []

    def listar_por_usuario(self, id_usuario):
        return [analise for analise in self.analises if analise.id_usuario == id_usuario]


def _criar_analise(id_usuario, pontuacao, requisitos, texto_curriculo, titulo_vaga="Vaga X"):
    vaga = Vaga(
        id_vaga=uuid.uuid4(),
        titulo=titulo_vaga,
        descricao="descricao",
        requisitos=requisitos,
        id_usuario=id_usuario,
    )
    curriculo = Curriculo(
        id_curriculo=uuid.uuid4(),
        nome_arquivo="cv.pdf",
        id_usuario=id_usuario,
        texto_extraido=texto_curriculo,
    )
    analise = Analise(
        id_analise=uuid.uuid4(),
        id_curriculo=curriculo.id_curriculo,
        id_vaga=vaga.id_vaga,
        id_usuario=id_usuario,
        pontuacao=pontuacao,
    )
    analise.vaga = vaga
    analise.curriculo = curriculo
    return analise


def _criar_service(analises):
    service = PlanoService(db=None)
    service.analise_repository = AnaliseRepositorioFalso(analises)
    return service


def test_obter_historico_retorna_data_vaga_e_pontuacao():
    id_usuario = uuid.uuid4()
    analise = _criar_analise(
        id_usuario, 85.0, "Python, Docker", "Tenho experiência com Python.", titulo_vaga="Dev Backend"
    )
    service = _criar_service([analise])

    resultado = service.obter_historico_e_lacunas(id_usuario)

    assert len(resultado["historico"]) == 1
    item = resultado["historico"][0]
    assert item["vaga_titulo"] == "Dev Backend"
    assert item["pontuacao"] == 85.0
    assert item["id_analise"] == analise.id_analise


def test_lacunas_recorrentes_ordenadas_por_frequencia():
    id_usuario = uuid.uuid4()
    analises = [
        _criar_analise(id_usuario, 70.0, "Python, Docker, AWS", "Sei Python e AWS."),
        _criar_analise(id_usuario, 60.0, "Python, Docker", "Sei apenas Python."),
        _criar_analise(id_usuario, 80.0, "Docker, Kubernetes", "Não sei nada disso."),
    ]
    service = _criar_service(analises)

    resultado = service.obter_historico_e_lacunas(id_usuario)

    lacunas = {item["competencia"]: item["frequencia"] for item in resultado["lacunas_recorrentes"]}
    assert lacunas["Docker"] == 3
    assert lacunas["Kubernetes"] == 1
    assert "Python" not in lacunas
    assert resultado["lacunas_recorrentes"][0]["competencia"] == "Docker"


def test_vaga_sem_requisitos_nao_gera_lacuna():
    id_usuario = uuid.uuid4()
    analise = _criar_analise(id_usuario, 50.0, "", "qualquer coisa")
    service = _criar_service([analise])

    resultado = service.obter_historico_e_lacunas(id_usuario)

    assert resultado["lacunas_recorrentes"] == []


def test_sem_analises_retorna_listas_vazias():
    service = _criar_service([])

    resultado = service.obter_historico_e_lacunas(uuid.uuid4())

    assert resultado["historico"] == []
    assert resultado["lacunas_recorrentes"] == []
