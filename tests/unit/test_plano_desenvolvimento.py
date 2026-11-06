import json
import uuid

from app.core.persistencia.models.analise import Analise
from app.core.persistencia.models.vaga import Vaga
from app.core.service.plano_desenvolvimento import (
    MENSAGEM_SEM_LACUNAS,
    consolidar_planos,
    montar_plano_desenvolvimento,
)
from app.core.service.plano_service import PlanoService
from tests.unit.test_analisador_service import AIServiceAdapterFalso, _criar_service_completo_com_fakes


def _requisito(requisito, tipo, status):
    return {"requisito": requisito, "tipo": tipo, "status": status, "evidencia": ""}


def test_cada_requisito_nao_atendido_tem_trilha_e_prioridade():
    resultado = {
        "requisitos_avaliados": [
            _requisito("Python", "obrigatorio", "evidenciado"),
            _requisito("AWS", "obrigatorio", "nao_evidenciado"),
            _requisito("Docker", "obrigatorio", "parcial"),
            _requisito("Scrum", "desejavel", "parcial"),
        ],
        "plano_desenvolvimento": {
            "itens": [
                {
                    "competencia": "aws",
                    "prioridade": "alta",
                    "certificacoes": [
                        {"nome": "AWS Certified Cloud Practitioner", "emissor": "Amazon Web Services"},
                        {"nome": "AWS Certified Cloud Practitioner"},
                    ],
                    "trilha": ["Faça o AWS Skill Builder", "  ", "Suba uma API no EC2"],
                }
            ]
        },
    }

    plano = montar_plano_desenvolvimento(resultado)

    assert plano["sem_lacunas"] is False
    assert [item["competencia"] for item in plano["itens"]] == ["AWS", "Docker", "Scrum"]
    aws, docker, scrum = plano["itens"]
    assert aws["origem"] == "ia"
    assert aws["trilha"] == ["Faça o AWS Skill Builder", "Suba uma API no EC2"]
    # Certificação repetida aparece uma vez só.
    assert [c["nome"] for c in aws["certificacoes"]] == ["AWS Certified Cloud Practitioner"]
    assert (docker["prioridade"], docker["origem"]) == ("media", "padrao")
    assert scrum["prioridade"] == "baixa"
    assert all(item["trilha"] for item in plano["itens"])


def test_sem_lacunas_informa_e_mantem_certificacoes_opcionais():
    plano = montar_plano_desenvolvimento(
        {
            "requisitos_avaliados": [_requisito("Python", "obrigatorio", "evidenciado")],
            "plano_desenvolvimento": {
                "itens": [],
                "certificacoes_opcionais": [{"nome": "PCAP", "emissor": "Python Institute", "motivo": "Diferencial"}],
            },
        }
    )

    assert plano["sem_lacunas"] is True
    assert plano["mensagem"] == MENSAGEM_SEM_LACUNAS
    assert plano["itens"] == []
    assert plano["certificacoes_opcionais"][0]["nome"] == "PCAP"


def test_prioridade_invalida_da_ia_cai_na_regra_padrao():
    [item] = montar_plano_desenvolvimento(
        {
            "requisitos_avaliados": [_requisito("Kafka", "obrigatorio", "nao_evidenciado")],
            "plano_desenvolvimento": {"itens": [{"competencia": "Kafka", "prioridade": "urgente"}]},
        }
    )["itens"]

    assert item["prioridade"] == "alta"


def test_consolidar_planos_agrupa_competencia_repetida_entre_vagas():
    ref_a = {"id_analise": uuid.uuid4(), "vaga_titulo": "Backend"}
    ref_b = {"id_analise": uuid.uuid4(), "vaga_titulo": "DevOps"}
    plano_a = montar_plano_desenvolvimento({"requisitos_avaliados": [_requisito("Docker", "desejavel", "parcial")]})
    plano_b = montar_plano_desenvolvimento(
        {"requisitos_avaliados": [_requisito("docker", "obrigatorio", "nao_evidenciado")]}
    )

    consolidado = consolidar_planos([(ref_a, plano_a), (ref_b, plano_b)])

    assert consolidado["resumo"] == {"alta": 1, "media": 0, "baixa": 0, "total": 1}
    [item] = consolidado["itens"]
    assert item["frequencia"] == 2
    assert item["prioridade"] == "alta"
    assert item["tipo"] == "obrigatorio"
    assert [vaga["vaga_titulo"] for vaga in item["vagas"]] == ["Backend", "DevOps"]


def test_consolidar_sem_analises():
    consolidado = consolidar_planos([])

    assert consolidado["sem_analises"] is True
    assert consolidado["sem_lacunas"] is False
    assert consolidado["itens"] == []


class AnaliseRepositorioFalso:
    def __init__(self, analises):
        self.analises = analises

    def listar_por_usuario(self, id_usuario, limit=None, offset=0):
        return [a for a in self.analises if a.id_usuario == id_usuario]


def _analise(id_usuario, vaga, requisitos):
    analise = Analise(
        id_analise=uuid.uuid4(),
        id_usuario=id_usuario,
        id_vaga=vaga.id_vaga,
        id_curriculo=uuid.uuid4(),
        observacoes=json.dumps({"requisitos_avaliados": requisitos}),
    )
    analise.vaga = vaga
    return analise


def test_plano_service_usa_so_a_analise_mais_recente_de_cada_vaga():
    id_usuario = uuid.uuid4()
    vaga = Vaga(id_vaga=uuid.uuid4(), titulo="Backend", descricao="d", id_usuario=id_usuario)
    recente = _analise(id_usuario, vaga, [_requisito("Docker", "obrigatorio", "evidenciado")])
    antiga = _analise(id_usuario, vaga, [_requisito("Docker", "obrigatorio", "nao_evidenciado")])
    service = PlanoService(db=None)
    service.analise_repository = AnaliseRepositorioFalso([recente, antiga])

    plano = service.obter_plano_desenvolvimento(id_usuario)

    assert plano["total_analises"] == 1
    assert plano["sem_lacunas"] is True


def test_analise_grava_plano_de_desenvolvimento():
    service = _criar_service_completo_com_fakes()
    service.ai_service_adapter = AIServiceAdapterFalso(
        json.dumps(
            {
                "pontuacao": 60,
                "resumo": "r",
                "observacoes": "o",
                "palavras_chave": {"correspondentes": [], "ausentes": []},
                "requisitos_avaliados": [_requisito("AWS", "obrigatorio", "nao_evidenciado")],
                "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
                "sugestoes_reescrita": [],
                "curriculo_estruturado": {"nome_completo": "Ana"},
            }
        )
    )
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga cloud")

    analise = service.analisar_curriculo_para_vaga(id_usuario, vaga.id_vaga, b"cv", "cv.pdf", "pdf")
    plano = service.obter_plano_desenvolvimento_analise(id_usuario, analise.id_analise)

    salvo = json.loads(analise.observacoes)["plano_desenvolvimento"]
    assert salvo["itens"][0]["competencia"] == "AWS"
    assert plano["itens"][0]["prioridade"] == "alta"
    assert plano["itens"][0]["origem"] == "padrao"
