from unittest.mock import MagicMock

from app.adapters.ai_service.ai_service_adapter import IAConfiguracaoAusenteError, IAIndisponivelError
from app.core.service.extracao_curriculo import (
    CAMPOS_CURRICULO,
    dados_curriculo_vazios,
    extrair_dados_estruturados_curriculo,
    normalizar_dados_editados,
)

RESPOSTA_IA_PADRAO = (
    '{"nome": "Ana Silva", "email": "ana@email.com", "telefone": "", '
    '"resumo": "Resumo.", "formacao": "Formação.", '
    '"experiencia_profissional": "Experiência.", "habilidades": "Python"}'
)


def test_extrair_dados_com_texto_vazio_retorna_dados_vazios():
    ai_adapter = MagicMock()
    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "   ")

    assert resultado == dados_curriculo_vazios("   ")
    ai_adapter.extrair_dados_estruturados.assert_not_called()


def test_extrair_dados_com_sucesso_retorna_campos_estruturados():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = RESPOSTA_IA_PADRAO

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome"] == "Ana Silva"
    assert resultado["habilidades"] == "Python"
    assert resultado["texto_bruto"] == "texto bruto"


def test_extrair_dados_remove_cercas_markdown_da_resposta():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = f"```json\n{RESPOSTA_IA_PADRAO}\n```"

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome"] == "Ana Silva"


def test_extrair_dados_com_ia_indisponivel_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.side_effect = IAIndisponivelError("timeout")

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome"] == ""
    assert resultado["texto_bruto"] == "texto bruto"


def test_extrair_dados_sem_configuracao_de_ia_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.side_effect = IAConfiguracaoAusenteError("sem chave")

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome"] == ""


def test_extrair_dados_com_resposta_nao_json_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = "não é json"

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado == dados_curriculo_vazios("texto bruto")


def test_normalizar_dados_editados_preenche_campos_ausentes():
    resultado = normalizar_dados_editados({"nome": "Ana"}, texto_bruto="texto original")

    assert resultado["nome"] == "Ana"
    for campo in CAMPOS_CURRICULO:
        assert campo in resultado
    assert resultado["texto_bruto"] == "texto original"


def test_normalizar_dados_editados_preserva_texto_bruto_proprio():
    resultado = normalizar_dados_editados({"nome": "Ana", "texto_bruto": "texto editado"}, texto_bruto="fallback")

    assert resultado["texto_bruto"] == "texto editado"
