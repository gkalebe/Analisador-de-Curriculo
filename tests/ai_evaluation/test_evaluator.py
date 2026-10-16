import json

from tests.ai_evaluation.evaluator import evaluate_comparison

CURRICULO_SINTETICO = "Ana Silva. Desenvolveu APIs internas em Python para atendimento ao cliente."


def _resposta(trecho_original: str) -> str:
    return json.dumps(
        {
            "pontuacao": 75,
            "resumo": "A experiência em Python é aderente à vaga.",
            "observacoes": "A experiência relevante está descrita no currículo.",
            "palavras_chave": {"correspondentes": ["Python"], "ausentes": ["Docker"]},
            "diagnostico_ats": {"pontos_fortes": [], "o_que_reorganizar": [], "o_que_retirar": []},
            "sugestoes_reescrita": [
                {
                    "campo": "experiencia_profissional",
                    "trecho_original": trecho_original,
                    "sugestao_otimizada": "Desenvolveu APIs internas em Python.",
                    "motivo": "Destaca a tecnologia já citada.",
                }
            ],
            "curriculo_estruturado": {"nome_completo": "Ana Silva"},
        }
    )


def test_evaluate_comparison_accepts_synthetic_grounded_response_without_network_calls():
    avaliacao = evaluate_comparison(
        CURRICULO_SINTETICO,
        _resposta("Desenvolveu APIs internas em Python para atendimento ao cliente."),
    )

    assert avaliacao.contract_valid
    assert avaliacao.grounded_suggestions == 1
    assert avaliacao.ungrounded_suggestions == 0
    assert avaliacao.issues == ()


def test_evaluate_comparison_marks_ungrounded_suggestion():
    avaliacao = evaluate_comparison(CURRICULO_SINTETICO, _resposta("Liderou uma migração para Kubernetes."))

    assert avaliacao.contract_valid
    assert avaliacao.grounded_suggestions == 0
    assert avaliacao.ungrounded_suggestions == 1
    assert avaliacao.issues == ("sugestao_0_trecho_original_nao_encontrado_no_curriculo",)
