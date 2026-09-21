import pytest

from app.adapters.ai_service.ai_service_adapter import IAIndisponivelError
from app.core.service.curriculo_validador import CurriculoInvalidoError, ValidadorCurriculoEstruturado

DADOS_COMPLETOS = {
    "nome_completo": "Ana Beatriz Souza",
    "titulo_profissional": "Desenvolvedora Backend Pleno",
    "contato": {"email": "ana@email.com", "telefone": "", "linkedin": "", "cidade": ""},
    "resumo_profissional": "4 anos de experiência em Python.",
    "experiencias": [],
    "formacao": [],
    "habilidades_tecnicas": [],
    "idiomas": [],
    "certificacoes": [],
}


class GeradorFalso:
    def __init__(self, valores_por_campo: dict[str, str] | None = None, erro: Exception | None = None):
        self.valores_por_campo = valores_por_campo or {}
        self.erro = erro
        self.campos_chamados: list[str] = []

    def regenerar_campo(self, informacoes_brutas: str, nome_campo: str) -> str:
        self.campos_chamados.append(nome_campo)
        if self.erro:
            raise self.erro
        return self.valores_por_campo.get(nome_campo, "")


def test_validar_sem_campos_vazios_nao_precisa_de_retry():
    validador = ValidadorCurriculoEstruturado()

    dados, campos_vazios = validador.validar(DADOS_COMPLETOS)

    assert dados is not None
    assert campos_vazios == []


def test_validar_com_json_fora_do_schema_retorna_none_e_todos_campos_obrigatorios():
    validador = ValidadorCurriculoEstruturado()

    dados, campos_vazios = validador.validar({"nome_completo": 123})

    assert dados is None
    assert "nome_completo" in campos_vazios


def test_validar_com_campo_obrigatorio_vazio_reporta_o_campo():
    dados_incompletos = {**DADOS_COMPLETOS, "titulo_profissional": ""}
    validador = ValidadorCurriculoEstruturado()

    dados, campos_vazios = validador.validar(dados_incompletos)

    assert dados is not None
    assert campos_vazios == ["titulo_profissional"]


def test_validar_e_reparar_faz_retry_cirurgico_so_do_campo_vazio():
    dados_incompletos = {**DADOS_COMPLETOS, "titulo_profissional": ""}
    gerador_falso = GeradorFalso(valores_por_campo={"titulo_profissional": "Desenvolvedora Backend Pleno"})
    validador = ValidadorCurriculoEstruturado(gerador=gerador_falso)

    dados, campos_com_retry = validador.validar_e_reparar(dados_incompletos, "informações brutas")

    assert dados.titulo_profissional == "Desenvolvedora Backend Pleno"
    assert campos_com_retry == ["titulo_profissional"]
    assert gerador_falso.campos_chamados == ["titulo_profissional"]


def test_validar_e_reparar_nao_mexe_em_campos_ja_preenchidos():
    gerador_falso = GeradorFalso()
    validador = ValidadorCurriculoEstruturado(gerador=gerador_falso)

    dados, campos_com_retry = validador.validar_e_reparar(DADOS_COMPLETOS, "informações brutas")

    assert dados.nome_completo == "Ana Beatriz Souza"
    assert campos_com_retry == []
    assert gerador_falso.campos_chamados == []


def test_validar_e_reparar_sem_gerador_reporta_campo_mas_nao_repara():
    dados_incompletos = {**DADOS_COMPLETOS, "resumo_profissional": ""}
    validador = ValidadorCurriculoEstruturado(gerador=None)

    dados, campos_com_retry = validador.validar_e_reparar(dados_incompletos, "informações brutas")

    assert dados.resumo_profissional == ""
    assert campos_com_retry == ["resumo_profissional"]


def test_validar_e_reparar_com_falha_na_ia_mantem_campo_vazio_mas_reporta_tentativa():
    dados_incompletos = {**DADOS_COMPLETOS, "resumo_profissional": ""}
    gerador_falso = GeradorFalso(erro=IAIndisponivelError("timeout"))
    validador = ValidadorCurriculoEstruturado(gerador=gerador_falso)

    dados, campos_com_retry = validador.validar_e_reparar(dados_incompletos, "informações brutas")

    assert dados.resumo_profissional == ""
    assert campos_com_retry == ["resumo_profissional"]


def test_validar_e_reparar_com_schema_invalido_lanca_erro():
    gerador_falso = GeradorFalso()
    validador = ValidadorCurriculoEstruturado(gerador=gerador_falso)

    with pytest.raises(CurriculoInvalidoError):
        validador.validar_e_reparar({"nome_completo": 123}, "informações brutas")
