"""Gera os arquivos .docx de template usados pela Etapa 3 (montagem, sem IA).

Um .docx é um arquivo binário (zip), então não faz sentido versionar um script
que "escreve XML na mão" nem editar os templates com um editor de texto. Este
gerador serve como a fonte legível/versionável da estrutura de cada template:
sempre que `curriculo_moderno.docx` ou `curriculo_classico.docx` precisarem
mudar de layout, edite este arquivo e rode `python gerar_templates.py`
novamente para regravar os .docx a partir daqui.

Cada tag Jinja2 (variáveis `{{ }}` e blocos `{% %}`) é escrita em uma única
chamada de `add_run()`/`add_paragraph()` para garantir que o Word não a separe
em múltiplos "runs" internos — se isso acontecer, o docxtpl não reconhece a
tag. Nunca edite os .docx gerados diretamente no Word: qualquer clique dentro
de uma tag pode quebrá-la em runs.
"""

from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

DIRETORIO_ATUAL = Path(__file__).parent

VERDE_MODERNO = RGBColor(0x1E, 0x5E, 0x3F)


def _paragrafo_tag(documento: docx.Document, tag: str) -> None:
    """Adiciona um parágrafo cujo texto INTEIRO é uma tag Jinja2 de controle
    (`{% for %}`, `{% endfor %}`, `{% if %}`, `{% endif %}`). Precisa estar
    sozinha no parágrafo: é assim que o docxtpl identifica blocos a repetir
    ou ocultar."""
    documento.add_paragraph(tag)


def _gerar_moderno() -> None:
    documento = docx.Document()

    titulo = documento.add_heading("{{ nome_completo }}", level=0)
    titulo.runs[0].font.color.rgb = VERDE_MODERNO

    subtitulo = documento.add_paragraph()
    run_subtitulo = subtitulo.add_run("{{ titulo_profissional }}")
    run_subtitulo.font.size = Pt(13)
    run_subtitulo.font.color.rgb = VERDE_MODERNO

    contato = documento.add_paragraph()
    run_contato = contato.add_run(
        "{{ contato.email }} · {{ contato.telefone }} · {{ contato.linkedin }} · {{ contato.cidade }}"
    )
    run_contato.font.size = Pt(10)

    _paragrafo_tag(documento, "{% if resumo_profissional %}")
    cabecalho = documento.add_heading("RESUMO PROFISSIONAL", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    documento.add_paragraph("{{ resumo_profissional }}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if experiencias %}")
    cabecalho = documento.add_heading("EXPERIÊNCIA PROFISSIONAL", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    _paragrafo_tag(documento, "{% for exp in experiencias %}")
    linha_cargo = documento.add_paragraph()
    run_cargo = linha_cargo.add_run("{{ exp.cargo }} — {{ exp.empresa }} ({{ exp.periodo_inicio }} a {{ exp.periodo_fim }})")
    run_cargo.bold = True
    _paragrafo_tag(documento, "{% for bullet in exp.descricao_bullets %}")
    documento.add_paragraph("{{ bullet }}", style="List Bullet")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if formacao %}")
    cabecalho = documento.add_heading("FORMAÇÃO", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    _paragrafo_tag(documento, "{% for item in formacao %}")
    documento.add_paragraph("{{ item.curso }} — {{ item.instituicao }} ({{ item.periodo }})")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if habilidades_tecnicas %}")
    cabecalho = documento.add_heading("HABILIDADES TÉCNICAS", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    documento.add_paragraph("{{ habilidades_tecnicas | join(', ') }}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if idiomas %}")
    cabecalho = documento.add_heading("IDIOMAS", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    _paragrafo_tag(documento, "{% for idm in idiomas %}")
    documento.add_paragraph("{{ idm.idioma }} — {{ idm.nivel }}")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if certificacoes %}")
    cabecalho = documento.add_heading("CERTIFICAÇÕES", level=2)
    cabecalho.runs[0].font.color.rgb = VERDE_MODERNO
    _paragrafo_tag(documento, "{% for cert in certificacoes %}")
    documento.add_paragraph("{{ cert }}", style="List Bullet")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    documento.save(str(DIRETORIO_ATUAL / "curriculo_moderno.docx"))


def _gerar_classico() -> None:
    documento = docx.Document()

    titulo = documento.add_heading("{{ nome_completo }}", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitulo = documento.add_paragraph()
    subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitulo.add_run("{{ titulo_profissional }}").italic = True

    contato = documento.add_paragraph()
    contato.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_contato = contato.add_run(
        "{{ contato.email }} · {{ contato.telefone }} · {{ contato.linkedin }} · {{ contato.cidade }}"
    )
    run_contato.font.size = Pt(10)

    _paragrafo_tag(documento, "{% if resumo_profissional %}")
    documento.add_heading("Resumo Profissional", level=2)
    documento.add_paragraph("{{ resumo_profissional }}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if experiencias %}")
    documento.add_heading("Experiência Profissional", level=2)
    _paragrafo_tag(documento, "{% for exp in experiencias %}")
    linha_cargo = documento.add_paragraph()
    linha_cargo.add_run("{{ exp.cargo }} — {{ exp.empresa }} ({{ exp.periodo_inicio }} a {{ exp.periodo_fim }})").bold = True
    _paragrafo_tag(documento, "{% for bullet in exp.descricao_bullets %}")
    documento.add_paragraph("{{ bullet }}", style="List Bullet")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if formacao %}")
    documento.add_heading("Formação", level=2)
    _paragrafo_tag(documento, "{% for item in formacao %}")
    documento.add_paragraph("{{ item.curso }} — {{ item.instituicao }} ({{ item.periodo }})")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if habilidades_tecnicas %}")
    documento.add_heading("Habilidades", level=2)
    documento.add_paragraph("{{ habilidades_tecnicas | join(', ') }}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if idiomas %}")
    documento.add_heading("Idiomas", level=2)
    _paragrafo_tag(documento, "{% for idm in idiomas %}")
    documento.add_paragraph("{{ idm.idioma }} — {{ idm.nivel }}")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    _paragrafo_tag(documento, "{% if certificacoes %}")
    documento.add_heading("Certificações", level=2)
    _paragrafo_tag(documento, "{% for cert in certificacoes %}")
    documento.add_paragraph("{{ cert }}", style="List Bullet")
    _paragrafo_tag(documento, "{% endfor %}")
    _paragrafo_tag(documento, "{% endif %}")

    documento.save(str(DIRETORIO_ATUAL / "curriculo_classico.docx"))


if __name__ == "__main__":
    _gerar_moderno()
    _gerar_classico()
    print("Templates gerados:")
    print(" -", DIRETORIO_ATUAL / "curriculo_moderno.docx")
    print(" -", DIRETORIO_ATUAL / "curriculo_classico.docx")
