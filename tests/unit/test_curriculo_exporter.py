import io

import docx
import pytest

from app.adapters.curriculo_exporter.curriculo_exporter import (
    CurriculoExporter,
    TemplateNaoSuportadoError,
)

DADOS_ESTRUTURADOS = {
    "nome_completo": "Ana Silva",
    "titulo_profissional": "Desenvolvedora Backend",
    "contato": {"email": "ana@email.com", "telefone": "(61) 99999-0000", "linkedin": "linkedin.com/in/ana", "cidade": "Brasília"},
    "resumo_profissional": "Resumo profissional de duas frases sobre a candidata.",
    "experiencias": [
        {
            "cargo": "Analista",
            "empresa": "Empresa X",
            "periodo_inicio": "2024",
            "periodo_fim": "atual",
            "descricao_bullets": ["Construiu APIs em FastAPI", "Reduziu custo de infra em 30%"],
        },
        {"cargo": "Estagiária", "empresa": "Empresa Y", "periodo_inicio": "2023", "periodo_fim": "2024", "descricao_bullets": []},
    ],
    "formacao": [
        {"curso": "Ciência da Computação", "instituicao": "UCB", "periodo": "cursando"},
        {"curso": "Técnico em Informática", "instituicao": "IFB", "periodo": "concluído"},
    ],
    "habilidades_tecnicas": ["Python", "FastAPI", "React", "SQL"],
    "idiomas": [{"idioma": "Inglês", "nivel": "Avançado"}],
    "certificacoes": ["AWS Cloud Practitioner"],
    "secoes_adicionais": [{"titulo": "Projetos", "itens": ["Projeto A — app de finanças", "Projeto B"]}],
    "texto_bruto": "texto bruto",
}

DADOS_FALLBACK = {
    "nome_completo": "",
    "texto_bruto": "Currículo em texto corrido, com “aspas curvas”, travessão — e reticências…",
}


@pytest.fixture
def exporter() -> CurriculoExporter:
    return CurriculoExporter()


def _texto_docx(conteudo: bytes) -> str:
    documento = docx.Document(io.BytesIO(conteudo))
    return "\n".join(paragrafo.text for paragrafo in documento.paragraphs)


@pytest.mark.parametrize("id_template", sorted(CurriculoExporter.TEMPLATES_SUPORTADOS))
@pytest.mark.parametrize("dados", [DADOS_ESTRUTURADOS, DADOS_FALLBACK], ids=["estruturado", "fallback"])
def test_gerar_pdf_produz_pdf_valido_para_todo_template(exporter, dados, id_template):
    conteudo = exporter.gerar_pdf(dados, id_template)

    assert conteudo.startswith(b"%PDF")
    assert len(conteudo) > 500


@pytest.mark.parametrize("id_template", sorted(CurriculoExporter.TEMPLATES_SUPORTADOS))
@pytest.mark.parametrize("dados", [DADOS_ESTRUTURADOS, DADOS_FALLBACK], ids=["estruturado", "fallback"])
def test_gerar_docx_produz_docx_valido_para_todo_template(exporter, dados, id_template):
    conteudo = exporter.gerar_docx(dados, id_template)

    assert conteudo[:2] == b"PK"
    texto_completo = _texto_docx(conteudo)
    if dados.get("nome_completo"):
        assert dados["nome_completo"] in texto_completo
    else:
        assert dados["texto_bruto"] in texto_completo


def test_gerar_docx_preserva_todas_as_secoes_e_itens_do_curriculo(exporter):
    texto = _texto_docx(exporter.gerar_docx(DADOS_ESTRUTURADOS, "generico"))

    for titulo in ("RESUMO", "EXPERIÊNCIA PROFISSIONAL", "FORMAÇÃO", "HABILIDADES", "IDIOMAS", "CERTIFICAÇÕES", "PROJETOS"):
        assert titulo in texto
    assert "Desenvolvedora Backend" in texto
    assert "linkedin.com/in/ana" in texto and "Brasília" in texto
    assert "Analista — Empresa X" in texto and "2024 - atual" in texto
    assert "Construiu APIs em FastAPI" in texto and "Reduziu custo de infra em 30%" in texto
    assert "Estagiária — Empresa Y" in texto
    assert "Ciência da Computação — UCB (cursando)" in texto
    assert "Inglês — Avançado" in texto
    assert "AWS Cloud Practitioner" in texto
    assert "Projeto A — app de finanças" in texto and "Projeto B" in texto


def test_secoes_omitem_o_que_estiver_vazio_e_mantem_ordem_ats(exporter):
    dados = exporter._preparar_dados(
        {"nome_completo": "Ana", "resumo_profissional": "R", "certificacoes": ["AWS"], "secoes_adicionais": [{"titulo": "", "itens": ["x"]}]}
    )

    titulos = [titulo for titulo, _, _ in exporter._secoes(dados)]

    assert titulos == ["Resumo", "Certificações", CurriculoExporter.TITULO_SECAO_ADICIONAL_PADRAO]


def test_secoes_sem_dados_estruturados_cai_para_texto_bruto(exporter):
    dados = exporter._preparar_dados(DADOS_FALLBACK)

    assert exporter._secoes(dados) == [("Currículo", "paragrafo", DADOS_FALLBACK["texto_bruto"])]


def test_preparar_dados_ignora_chaves_desconhecidas_e_completa_ausentes(exporter):
    dados = exporter._preparar_dados({"nome_completo": "Ana", "campo_estranho": 1})

    assert dados["nome_completo"] == "Ana"
    assert dados["experiencias"] == []
    assert dados["contato"]["email"] == ""
    assert "campo_estranho" not in dados


@pytest.mark.parametrize("id_template", sorted(CurriculoExporter.TEMPLATES_SUPORTADOS))
def test_gerar_docx_usa_marcadores_reais_para_experiencia_e_formacao(exporter, id_template):
    conteudo = exporter.gerar_docx(DADOS_ESTRUTURADOS, id_template)

    documento = docx.Document(io.BytesIO(conteudo))
    estilos_usados = {paragrafo.style.name for paragrafo in documento.paragraphs}
    assert "List Bullet" in estilos_usados


def test_gerar_pdf_com_template_inexistente_lanca_erro(exporter):
    with pytest.raises(TemplateNaoSuportadoError):
        exporter.gerar_pdf(DADOS_ESTRUTURADOS, "inexistente")


def test_gerar_docx_com_template_inexistente_lanca_erro(exporter):
    with pytest.raises(TemplateNaoSuportadoError):
        exporter.gerar_docx(DADOS_ESTRUTURADOS, "inexistente")


def test_gerar_pdf_nao_quebra_com_lista_longa_de_habilidades(exporter):
    dados = dict(DADOS_ESTRUTURADOS)
    dados["habilidades_tecnicas"] = [f"HabilidadeComNomeBemLongoNumero{i}" for i in range(30)]

    for id_template in CurriculoExporter.TEMPLATES_SUPORTADOS:
        conteudo = exporter.gerar_pdf(dados, id_template)
        assert conteudo.startswith(b"%PDF")


def test_gerar_pdf_nao_quebra_com_curriculo_longo_de_varias_paginas(exporter):
    dados = dict(DADOS_ESTRUTURADOS)
    dados["experiencias"] = [
        {
            "cargo": f"Cargo {i}",
            "empresa": f"Empresa {i}",
            "periodo_inicio": "2010",
            "periodo_fim": "2012",
            "descricao_bullets": [f"Responsabilidade {j} descrita com algum detalhe para ocupar espaço." for j in range(6)],
        }
        for i in range(12)
    ]

    conteudo = exporter.gerar_pdf(dados, "generico")

    assert conteudo.startswith(b"%PDF")
    assert conteudo.count(b"/Type /Page\n") >= 2 or conteudo.count(b"/Type /Page") >= 3


def test_sanitizar_texto_pdf_remove_emoji_em_vez_de_substituir_por_interrogacao(exporter):
    texto = "🖥️ Linguagens de Programação: C, Python, Java"

    resultado = exporter._sanitizar_texto_pdf(texto)

    assert "?" not in resultado
    assert resultado == "Linguagens de Programação: C, Python, Java"


def test_gerar_pdf_com_emojis_e_travessoes_no_conteudo_nao_quebra(exporter):
    dados = dict(DADOS_ESTRUTURADOS)
    dados["habilidades_tecnicas"] = ["💻 Linguagens de Programação: C, Python", "🌐 Desenvolvimento Web — HTML, CSS"]
    dados["experiencias"] = [{"cargo": "Dev — Pleno", "empresa": "Empresa “X”", "descricao_bullets": ["Entregou… 🚀"]}]

    for id_template in CurriculoExporter.TEMPLATES_SUPORTADOS:
        conteudo = exporter.gerar_pdf(dados, id_template)
        assert conteudo.startswith(b"%PDF")
