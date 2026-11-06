import json

import pytest

from app.adapters.ai_service.ai_service_adapter import IARespostaInvalidaError
from app.adapters.ai_service.response_contracts import interpretar_resultado_comparacao


@pytest.mark.parametrize("score", [-1, 101, True, "não é número"])
def test_comparison_contract_rejects_invalid_score(score):
    resposta = json.dumps({"pontuacao": score, "observacoes": "Teste."})

    with pytest.raises(IARespostaInvalidaError):
        interpretar_resultado_comparacao(resposta)


def test_comparison_contract_rejects_missing_score():
    with pytest.raises(IARespostaInvalidaError):
        interpretar_resultado_comparacao('{"observacoes": "Sem pontuação."}')


def test_comparison_contract_rejects_missing_structured_resume():
    resposta = {
        "pontuacao": 75,
        "resumo": "Aderência.",
        "observacoes": "Teste.",
        "palavras_chave": {"correspondentes": [], "ausentes": []},
        "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
        "sugestoes_reescrita": [],
    }

    with pytest.raises(IARespostaInvalidaError, match="contrato da análise"):
        interpretar_resultado_comparacao(json.dumps(resposta))


def test_comparison_contract_accepts_markdown_wrapped_json_and_valid_score():
    resposta = {
        "pontuacao": 75,
        "resumo": "Aderência.",
        "observacoes": "Teste.",
        "palavras_chave": {"correspondentes": [], "ausentes": []},
        "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
        "sugestoes_reescrita": [],
        "curriculo_estruturado": {"nome_completo": "Ana"},
    }
    resultado = interpretar_resultado_comparacao(f"```json\n{json.dumps(resposta)}\n```")

    assert resultado.pontuacao == 75
    assert resultado.observacoes == "Teste."


def test_comparison_contract_accepts_requirement_evidence_breakdown():
    resposta = {
        "pontuacao": 75,
        "resumo": "Aderência.",
        "observacoes": "Teste.",
        "palavras_chave": {"correspondentes": [], "ausentes": []},
        "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
        "sugestoes_reescrita": [],
        "requisitos_avaliados": [
            {
                "requisito": "Python",
                "tipo": "obrigatorio",
                "status": "evidenciado",
                "evidencia": "Experiência profissional descrita no currículo.",
            }
        ],
        "curriculo_estruturado": {"nome_completo": "Ana"},
    }

    resultado = interpretar_resultado_comparacao(json.dumps(resposta))

    assert resultado.requisitos_avaliados[0].tipo == "obrigatorio"
    assert resultado.requisitos_avaliados[0].status == "evidenciado"


def test_comparison_contract_normalizes_accented_and_formatted_requirement_types_and_status():
    resposta = {
        "pontuacao": 80,
        "resumo": "Aderência.",
        "observacoes": "Teste.",
        "palavras_chave": {"correspondentes": [], "ausentes": []},
        "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
        "sugestoes_reescrita": [],
        "requisitos_avaliados": [
            {
                "requisito": "Django",
                "tipo": "Obrigatório",
                "status": "não evidenciado",
                "evidencia": "Não encontrado.",
            },
            {
                "requisito": "FastAPI",
                "tipo": "desejável",
                "status": "nao-evidenciado",
                "evidencia": "Não citado.",
            },
            {
                "requisito": "Docker",
                "tipo": "diferencial",
                "status": "parcialmente atendido",
                "evidencia": "Menção básica.",
            },
        ],
        "curriculo_estruturado": {"nome_completo": "Ana"},
    }

    resultado = interpretar_resultado_comparacao(json.dumps(resposta))

    assert resultado.requisitos_avaliados[0].tipo == "obrigatorio"
    assert resultado.requisitos_avaliados[0].status == "nao_evidenciado"
    assert resultado.requisitos_avaliados[1].tipo == "desejavel"
    assert resultado.requisitos_avaliados[1].status == "nao_evidenciado"
    assert resultado.requisitos_avaliados[2].tipo == "desejavel"
    assert resultado.requisitos_avaliados[2].status == "parcial"


def _dimensoes(nota=8):
    return {
        "clareza": {"nota": nota, "comentario": "ok"},
        "objetividade": {"nota": nota, "comentario": "ok"},
        "coerencia": {"nota": nota, "comentario": "ok"},
        "alinhamento": {"nota": nota, "comentario": "ok"},
        "feedback_geral": "ok",
    }


def _avaliacao(ordens, nota=8):
    return json.dumps(
        {"avaliacoes": [{"ordem": o, **_dimensoes(nota)} for o in ordens], "feedback_geral": "Geral."}
    )


def test_avaliacao_entrevista_aceita_json_valido_e_com_markdown():
    from app.adapters.ai_service.response_contracts import interpretar_avaliacao_entrevista

    resultado = interpretar_avaliacao_entrevista(f"```json\n{_avaliacao([1, 2, 3])}\n```", 3)

    assert [a.ordem for a in resultado.avaliacoes] == [1, 2, 3]
    assert resultado.feedback_geral == "Geral."
    assert resultado.avaliacoes[0].clareza.nota == 8


@pytest.mark.parametrize(
    "resposta",
    [
        "não é json",
        "[]",
        json.dumps({"avaliacoes": "nada"}),
        _avaliacao([1, 2]),  # falta a pergunta 3
        _avaliacao([1, 2, 3, 4]),  # pergunta inexistente
        _avaliacao([1, 2, 2]),  # repetida
        _avaliacao([1, 2, 3], nota=10.5),
        _avaliacao([1, 2, 3], nota=-1),
        _avaliacao([1, 2, 3], nota=True),
        _avaliacao([1, 2, 3], nota="alta"),
    ],
)
def test_avaliacao_entrevista_rejeita_resposta_invalida(resposta):
    from app.adapters.ai_service.response_contracts import interpretar_avaliacao_entrevista

    with pytest.raises(IARespostaInvalidaError):
        interpretar_avaliacao_entrevista(resposta, 3)
