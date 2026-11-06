import json
import uuid

from app.core.persistencia.models.analise import Analise
from app.core.service.recomendacoes_competencias import (
    identificar_lacunas,
    montar_recomendacoes,
    resultado_analise_como_dict,
)
from tests.unit.test_analisador_service import AIServiceAdapterFalso, _criar_service_completo_com_fakes


def _resultado(**extra) -> dict:
    base = {
        "requisitos_avaliados": [
            {"requisito": "Python", "tipo": "obrigatorio", "status": "evidenciado", "evidencia": "5 anos"},
            {"requisito": "Docker", "tipo": "obrigatorio", "status": "parcial", "evidencia": "cita containers"},
            {"requisito": "Kubernetes", "tipo": "desejavel", "status": "nao_evidenciado", "evidencia": ""},
        ],
        "palavras_chave": {"correspondentes": ["Python"], "ausentes": ["Kubernetes", "Terraform"]},
    }
    base.update(extra)
    return base


def test_lacunas_incluem_requisitos_nao_atendidos_e_termos_ausentes_sem_duplicar():
    lacunas = identificar_lacunas(_resultado())

    assert [lacuna["competencia"] for lacuna in lacunas] == ["Docker", "Kubernetes", "Terraform"]
    assert lacunas[0] == {"competencia": "Docker", "tipo": "obrigatorio", "status": "parcial"}
    assert lacunas[2]["status"] == "nao_evidenciado"


def test_cada_competencia_em_lacuna_recebe_ao_menos_uma_orientacao():
    resultado = _resultado(
        recomendacoes_competencias=[
            {
                "competencia": "docker",
                "orientacoes": ["Troque 'containers' por 'Docker' no bullet da Acme, descrevendo o deploy."],
                "onde_evidenciar": "experiencia_profissional",
            },
            {"competencia": "Kubernetes", "orientacoes": ["   "]},
        ]
    )

    recomendacoes = montar_recomendacoes(resultado)

    assert len(recomendacoes) == 3
    assert all(r["orientacoes"] for r in recomendacoes)
    docker, kubernetes, terraform = recomendacoes
    assert docker["origem"] == "ia"
    assert docker["onde_evidenciar"] == "experiencia_profissional"
    # Orientação vazia da IA não conta: entra a padrão.
    assert kubernetes["origem"] == "padrao"
    assert terraform["origem"] == "padrao"


def test_orientacao_padrao_nunca_afirma_competencia_inexistente():
    [recomendacao] = montar_recomendacoes(
        {"requisitos_avaliados": [{"requisito": "Go", "tipo": "obrigatorio", "status": "nao_evidenciado"}]}
    )

    texto = recomendacao["orientacoes"][0]
    assert "Se você tem experiência real com Go" in texto
    assert "Se não tiver, não inclua" in texto


def test_correspondencia_respeita_limite_de_palavra():
    resultado = {
        "requisitos_avaliados": [{"requisito": "NoSQL", "tipo": "desejavel", "status": "nao_evidenciado"}],
        "recomendacoes_competencias": [{"competencia": "SQL", "orientacoes": ["Destaque SQL"]}],
    }

    [recomendacao] = montar_recomendacoes(resultado)

    assert recomendacao["origem"] == "padrao"


def test_sem_lacunas_nao_gera_recomendacoes():
    resultado = {
        "requisitos_avaliados": [{"requisito": "Python", "tipo": "obrigatorio", "status": "evidenciado"}],
        "palavras_chave": {"correspondentes": ["Python"], "ausentes": []},
    }

    assert montar_recomendacoes(resultado) == []


def test_resultado_analise_legado_em_texto_puro_vira_dict_vazio():
    assert resultado_analise_como_dict("Análise antiga em texto") == {}
    assert resultado_analise_como_dict(None) == {}


def test_analise_grava_recomendacoes_com_cobertura_garantida():
    service = _criar_service_completo_com_fakes()
    service.ai_service_adapter = AIServiceAdapterFalso(
        json.dumps(
            {
                "pontuacao": 70,
                "resumo": "Boa aderência.",
                "observacoes": "ok",
                "palavras_chave": {"correspondentes": [], "ausentes": ["Terraform"]},
                "requisitos_avaliados": [
                    {"requisito": "Docker", "tipo": "obrigatorio", "status": "parcial", "evidencia": "x"}
                ],
                "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
                "sugestoes_reescrita": [],
                "recomendacoes_competencias": [
                    {"competencia": "Docker", "orientacoes": ["Use o termo Docker no bullet de deploy."]}
                ],
                "curriculo_estruturado": {"nome_completo": "Ana"},
            }
        )
    )
    id_usuario = uuid.uuid4()
    vaga = service.cadastrar_vaga(id_usuario=id_usuario, descricao="Vaga Python com Docker")

    analise = service.analisar_curriculo_para_vaga(id_usuario, vaga.id_vaga, b"cv", "cv.pdf", "pdf")

    salvo = json.loads(analise.observacoes)["recomendacoes_competencias"]
    assert [r["competencia"] for r in salvo] == ["Docker", "Terraform"]
    assert [r["origem"] for r in salvo] == ["ia", "padrao"]


def test_obter_recomendacoes_de_analise_legada_usa_orientacoes_padrao():
    service = _criar_service_completo_com_fakes()
    id_usuario = uuid.uuid4()
    analise = service.analise_repository.criar(
        Analise(
            id_usuario=id_usuario,
            id_curriculo=uuid.uuid4(),
            id_vaga=uuid.uuid4(),
            observacoes=json.dumps(
                {"requisitos_avaliados": [{"requisito": "AWS", "tipo": "obrigatorio", "status": "nao_evidenciado"}]}
            ),
        )
    )

    dados = service.obter_recomendacoes_competencias(id_usuario, analise.id_analise)

    assert dados["sem_lacunas"] is False
    assert dados["recomendacoes"][0]["competencia"] == "AWS"
    assert dados["recomendacoes"][0]["origem"] == "padrao"


def test_recalcular_recomendacoes_gravadas_preserva_origem():
    primeira = montar_recomendacoes(_resultado())
    segunda = montar_recomendacoes({**_resultado(), "recomendacoes_competencias": primeira})

    assert segunda == primeira
