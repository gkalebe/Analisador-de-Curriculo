from unittest.mock import MagicMock

import pytest

from app.adapters.ai_service.ai_service_adapter import (
    IAConfiguracaoAusenteError,
    IAIndisponivelError,
)
from app.core.persistencia.models.curriculo import Curriculo
from app.core.service.extracao_curriculo import (
    CAMPOS_CURRICULO,
    CAMPOS_ESTRUTURADOS,
    dados_curriculo_vazios,
    dados_planos_de,
    dados_tem_conteudo,
    eh_formato_plano,
    estruturar_dados_planos,
    extrair_dados_estruturados_curriculo,
    mesclar_dados_planos,
    normalizar_dados_curriculo,
    obter_dados_curriculo_com_cache,
)

RESPOSTA_IA_PADRAO = """{
  "nome_completo": "Ana Silva",
  "titulo_profissional": "Desenvolvedora Backend",
  "contato": {"email": "ana@email.com", "telefone": "", "linkedin": "linkedin.com/in/ana", "cidade": "Brasília"},
  "resumo_profissional": "Resumo.",
  "experiencias": [
    {"cargo": "Dev", "empresa": "Empresa X", "periodo_inicio": "2021", "periodo_fim": "atual",
     "descricao_bullets": ["Construiu APIs em FastAPI", "Reduziu custo de infra em 30%"]}
  ],
  "formacao": [{"curso": "Engenharia", "instituicao": "UnB", "periodo": "2016-2020"}],
  "habilidades_tecnicas": ["Python", "SQL"],
  "idiomas": [{"idioma": "Inglês", "nivel": "Avançado"}],
  "certificacoes": ["AWS Cloud Practitioner"],
  "secoes_adicionais": [{"titulo": "Projetos", "itens": ["Projeto A", "Projeto B"]}]
}"""

# Formato antigo (7 campos planos), ainda presente em linhas antigas do banco.
RESPOSTA_IA_LEGADA = (
    '{"nome": "Ana Silva", "email": "ana@email.com", "telefone": "", '
    '"resumo": "Resumo.", "formacao": "Engenharia — UnB", '
    '"experiencia_profissional": "Dev — Empresa X\\nEstagiária — Empresa Y", "habilidades": "Python, SQL"}'
)


def test_extrair_dados_com_texto_vazio_retorna_dados_vazios():
    ai_adapter = MagicMock()
    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "   ")

    assert resultado == dados_curriculo_vazios("   ")
    ai_adapter.extrair_dados_estruturados.assert_not_called()


def test_extrair_dados_com_sucesso_preserva_todas_as_secoes():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = RESPOSTA_IA_PADRAO

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome_completo"] == "Ana Silva"
    assert resultado["contato"]["linkedin"] == "linkedin.com/in/ana"
    assert resultado["experiencias"][0]["descricao_bullets"] == [
        "Construiu APIs em FastAPI",
        "Reduziu custo de infra em 30%",
    ]
    assert resultado["idiomas"] == [{"idioma": "Inglês", "nivel": "Avançado"}]
    assert resultado["certificacoes"] == ["AWS Cloud Practitioner"]
    assert resultado["secoes_adicionais"] == [{"titulo": "Projetos", "itens": ["Projeto A", "Projeto B"]}]
    assert resultado["texto_bruto"] == "texto bruto"


def test_extrair_dados_remove_cercas_markdown_da_resposta():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = f"```json\n{RESPOSTA_IA_PADRAO}\n```"

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome_completo"] == "Ana Silva"


def test_extrair_dados_aceita_resposta_no_formato_plano_antigo():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = RESPOSTA_IA_LEGADA

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome_completo"] == "Ana Silva"
    assert [e["cargo"] for e in resultado["experiencias"]] == ["Dev — Empresa X", "Estagiária — Empresa Y"]
    assert resultado["habilidades_tecnicas"] == ["Python", "SQL"]


def test_extrair_dados_coage_listas_que_a_ia_devolveu_como_texto():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = (
        '{"nome_completo": "Ana", "habilidades_tecnicas": "Python, SQL", '
        '"experiencias": ["Dev — Empresa X"], "idiomas": "Inglês — Avançado", '
        '"secoes_adicionais": [{"titulo": "Projetos", "itens": "Projeto A\\nProjeto B"}]}'
    )

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["habilidades_tecnicas"] == ["Python", "SQL"]
    assert resultado["experiencias"][0]["cargo"] == "Dev — Empresa X"
    assert resultado["idiomas"][0]["idioma"] == "Inglês — Avançado"
    assert resultado["secoes_adicionais"][0]["itens"] == ["Projeto A", "Projeto B"]


def test_extrair_dados_com_ia_indisponivel_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.side_effect = IAIndisponivelError("timeout")

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome_completo"] == ""
    assert resultado["texto_bruto"] == "texto bruto"


def test_extrair_dados_sem_configuracao_de_ia_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.side_effect = IAConfiguracaoAusenteError("sem chave")

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado["nome_completo"] == ""


def test_extrair_dados_com_resposta_nao_json_cai_para_vazio():
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = "não é json"

    resultado = extrair_dados_estruturados_curriculo(ai_adapter, "texto bruto")

    assert resultado == dados_curriculo_vazios("texto bruto")


def test_normalizar_dados_curriculo_preenche_campos_ausentes():
    resultado = normalizar_dados_curriculo({"nome_completo": "Ana"}, texto_bruto="texto original")

    assert resultado["nome_completo"] == "Ana"
    for campo in CAMPOS_ESTRUTURADOS:
        assert campo in resultado
    assert resultado["contato"] == {"email": "", "telefone": "", "linkedin": "", "cidade": ""}
    assert resultado["texto_bruto"] == "texto original"


def test_normalizar_dados_curriculo_preserva_texto_bruto_proprio():
    resultado = normalizar_dados_curriculo({"nome_completo": "Ana", "texto_bruto": "texto editado"}, "fallback")

    assert resultado["texto_bruto"] == "texto editado"


def test_normalizar_dados_curriculo_converte_linha_antiga_no_formato_plano():
    linha_antiga = {
        "nome": "Ana",
        "email": "ana@email.com",
        "telefone": "61 9",
        "resumo": "Resumo.",
        "formacao": "Engenharia — UnB\nTécnico — IFB",
        "experiencia_profissional": "Dev — X",
        "habilidades": "Python, SQL",
        "texto_bruto": "bruto",
    }

    resultado = normalizar_dados_curriculo(linha_antiga)

    assert eh_formato_plano(linha_antiga)
    assert resultado["nome_completo"] == "Ana"
    assert resultado["contato"]["email"] == "ana@email.com"
    assert resultado["resumo_profissional"] == "Resumo."
    assert [f["curso"] for f in resultado["formacao"]] == ["Engenharia — UnB", "Técnico — IFB"]
    assert resultado["habilidades_tecnicas"] == ["Python", "SQL"]
    assert resultado["texto_bruto"] == "bruto"


def test_dados_planos_de_projeta_para_as_colunas_da_tabela_candidato():
    estruturado = normalizar_dados_curriculo(
        {
            "nome_completo": "Ana",
            "contato": {"email": "ana@email.com", "telefone": "61 9"},
            "resumo_profissional": "Resumo.",
            "experiencias": [
                {"cargo": "Dev", "empresa": "X", "periodo_inicio": "2021", "periodo_fim": "atual", "descricao_bullets": ["Fez A"]}
            ],
            "formacao": [{"curso": "Engenharia", "instituicao": "UnB", "periodo": "2016-2020"}],
            "habilidades_tecnicas": ["Python", "SQL"],
        }
    )

    planos = dados_planos_de(estruturado)

    assert set(planos) == set(CAMPOS_CURRICULO)
    assert planos["nome"] == "Ana"
    assert planos["experiencia_profissional"] == "Dev — X (2021 - atual)\n  - Fez A"
    assert planos["formacao"] == "Engenharia — UnB (2016-2020)"
    assert planos["habilidades"] == "Python, SQL"


def test_estruturar_e_projetar_sao_inversos_para_dados_planos():
    planos = {
        "nome": "Ana",
        "email": "ana@email.com",
        "telefone": "",
        "resumo": "Resumo.",
        "formacao": "Engenharia — UnB",
        "experiencia_profissional": "Dev — X\nEstagiária — Y",
        "habilidades": "Python, SQL",
    }

    assert dados_planos_de(estruturar_dados_planos(planos)) == planos


def test_mesclar_dados_planos_so_substitui_campos_alterados_e_preserva_o_resto():
    estruturado = normalizar_dados_curriculo(
        {
            "nome_completo": "Ana",
            "resumo_profissional": "Resumo antigo",
            "experiencias": [{"cargo": "Dev", "empresa": "X", "descricao_bullets": ["Fez A", "Fez B"]}],
            "idiomas": [{"idioma": "Inglês", "nivel": "C1"}],
            "secoes_adicionais": [{"titulo": "Projetos", "itens": ["Projeto A"]}],
        }
    )
    projecao = dados_planos_de(estruturado)

    resultado = mesclar_dados_planos(
        estruturado,
        {"nome": "Ana Silva", "resumo": "Resumo novo", "experiencia_profissional": projecao["experiencia_profissional"]},
        texto_bruto="bruto",
    )

    assert resultado["nome_completo"] == "Ana Silva"
    assert resultado["resumo_profissional"] == "Resumo novo"
    # Experiência não mudou na projeção → bullets preservados; idiomas e seções extras intactos.
    assert resultado["experiencias"][0]["descricao_bullets"] == ["Fez A", "Fez B"]
    assert resultado["idiomas"] == [{"idioma": "Inglês", "nivel": "C1"}]
    assert resultado["secoes_adicionais"] == [{"titulo": "Projetos", "itens": ["Projeto A"]}]
    assert resultado["texto_bruto"] == "bruto"


def test_mesclar_dados_planos_substitui_experiencias_quando_o_texto_plano_muda():
    estruturado = normalizar_dados_curriculo(
        {"experiencias": [{"cargo": "Dev", "empresa": "X", "descricao_bullets": ["Fez A"]}]}
    )

    resultado = mesclar_dados_planos(estruturado, {"experiencia_profissional": "Gerente — Z"})

    assert [e["cargo"] for e in resultado["experiencias"]] == ["Gerente — Z"]


def test_dados_tem_conteudo_detecta_qualquer_secao_preenchida():
    assert dados_tem_conteudo(dados_curriculo_vazios("texto")) is False
    assert dados_tem_conteudo(normalizar_dados_curriculo({"certificacoes": ["AWS"]})) is True
    assert dados_tem_conteudo(normalizar_dados_curriculo({"contato": {"email": "a@b.c"}})) is True


def _curriculo(**overrides) -> Curriculo:
    base = {
        "nome_arquivo": "curriculo.pdf",
        "texto_extraido": "texto bruto do currículo",
        "dados_editados": None,
        "dados_extraidos": None,
    }
    base.update(overrides)
    return Curriculo(**base)


class RepositorioFalso:
    def __init__(self):
        self.chamadas_salvar_dados_extraidos: list[dict] = []

    def salvar_dados_extraidos(self, curriculo: Curriculo, dados_extraidos: dict) -> Curriculo:
        curriculo.dados_extraidos = dados_extraidos
        self.chamadas_salvar_dados_extraidos.append(dados_extraidos)
        return curriculo


def test_obter_dados_curriculo_com_cache_usa_dados_editados_sem_chamar_ia():
    curriculo = _curriculo(dados_editados={"nome_completo": "Ana Editada"})
    ai_adapter = MagicMock()
    repositorio = RepositorioFalso()

    dados = obter_dados_curriculo_com_cache(curriculo, ai_adapter, repositorio)

    assert dados["nome_completo"] == "Ana Editada"
    ai_adapter.extrair_dados_estruturados.assert_not_called()
    assert repositorio.chamadas_salvar_dados_extraidos == []


def test_obter_dados_curriculo_com_cache_reaproveita_dados_extraidos_sem_chamar_ia():
    curriculo = _curriculo(dados_extraidos={"nome_completo": "Ana Cacheada"})
    ai_adapter = MagicMock()
    repositorio = RepositorioFalso()

    dados = obter_dados_curriculo_com_cache(curriculo, ai_adapter, repositorio)

    assert dados["nome_completo"] == "Ana Cacheada"
    ai_adapter.extrair_dados_estruturados.assert_not_called()


def test_obter_dados_curriculo_com_cache_converte_linha_antiga_no_formato_plano():
    curriculo = _curriculo(dados_extraidos={"nome": "Ana Antiga", "habilidades": "Python"})
    ai_adapter = MagicMock()

    dados = obter_dados_curriculo_com_cache(curriculo, ai_adapter, RepositorioFalso())

    assert dados["nome_completo"] == "Ana Antiga"
    assert dados["habilidades_tecnicas"] == ["Python"]
    ai_adapter.extrair_dados_estruturados.assert_not_called()


def test_obter_dados_curriculo_com_cache_extrai_e_salva_na_primeira_vez():
    curriculo = _curriculo()
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.return_value = RESPOSTA_IA_PADRAO
    repositorio = RepositorioFalso()

    dados = obter_dados_curriculo_com_cache(curriculo, ai_adapter, repositorio)

    assert dados["nome_completo"] == "Ana Silva"
    ai_adapter.extrair_dados_estruturados.assert_called_once()
    assert len(repositorio.chamadas_salvar_dados_extraidos) == 1
    assert curriculo.dados_extraidos["nome_completo"] == "Ana Silva"
    assert curriculo.dados_extraidos["secoes_adicionais"][0]["titulo"] == "Projetos"


def test_obter_dados_curriculo_com_cache_nao_salva_extracao_vazia():
    curriculo = _curriculo()
    ai_adapter = MagicMock()
    ai_adapter.extrair_dados_estruturados.side_effect = IAIndisponivelError("timeout")
    repositorio = RepositorioFalso()

    dados = obter_dados_curriculo_com_cache(curriculo, ai_adapter, repositorio)

    assert dados["nome_completo"] == ""
    assert repositorio.chamadas_salvar_dados_extraidos == []
