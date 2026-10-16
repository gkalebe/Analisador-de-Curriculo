from dataclasses import dataclass

from app.adapters.ai_service.response_contracts import interpretar_resultado_comparacao


@dataclass(frozen=True)
class EvaluationResult:
    contract_valid: bool
    grounded_suggestions: int
    ungrounded_suggestions: int
    issues: tuple[str, ...]


def evaluate_comparison(curriculo: str, resposta_ia: str) -> EvaluationResult:
    """Checagens determinísticas offline; não mede qualidade semântica da avaliação."""
    resultado = interpretar_resultado_comparacao(resposta_ia)
    grounded = 0
    ungrounded = 0
    issues = []

    for indice, sugestao in enumerate(resultado.sugestoes_reescrita or []):
        if sugestao.trecho_original and sugestao.trecho_original in curriculo:
            grounded += 1
        else:
            ungrounded += 1
            issues.append(f"sugestao_{indice}_trecho_original_nao_encontrado_no_curriculo")

    return EvaluationResult(
        contract_valid=True,
        grounded_suggestions=grounded,
        ungrounded_suggestions=ungrounded,
        issues=tuple(issues),
    )
