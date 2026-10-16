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
