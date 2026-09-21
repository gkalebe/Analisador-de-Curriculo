import io
import re

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from fpdf import FPDF
from fpdf.enums import XPos, YPos

MODOS_SECAO = {
    "Resumo": "paragrafo",
    "Currículo": "paragrafo",
    "Experiência Profissional": "lista",
    "Formação": "lista",
    "Habilidades": "habilidades",
}


class TemplateNaoSuportadoError(Exception):
    pass


class CurriculoExporter:
    """Gera PDF/DOCX em 5 templates de currículo voltados a triagem por ATS
    (generico, tecnologia, estagio, gestao, setor_publico).

    Layout sempre em coluna única, com títulos de seção padrão ("Experiência
    Profissional", "Formação", "Habilidades") e listas com marcadores reais —
    é o formato que passa melhor por leitores de ATS (Applicant Tracking
    System): colunas múltiplas, tabelas e ícones decorativos costumam
    embaralhar a ordem de leitura do texto extraído pelo parser. Contato
    sempre no corpo do documento, nunca em cabeçalho/rodapé (muitos parsers de
    ATS ignoram essas áreas). Fontes padrão (Helvetica/Times, sem ícones).

    Os 5 templates compartilham exatamente a mesma estrutura visual — só o
    "accent" (cor de destaque do nome, das bordas de seção e dos marcadores)
    muda por template, escolhido por área de atuação (`CORES_TEMPLATES`). Cor
    é usada só como formatação de fonte/borda, nunca como fundo de tabela ou
    texto de baixo contraste, para nunca arriscar ficar ilegível num
    conversor de ATS que ignore estilos.
    """

    CORES_TEMPLATES: dict[str, tuple[int, int, int]] = {
        "generico": (31, 56, 100),
        "tecnologia": (15, 118, 110),
        "estagio": (194, 65, 12),
        "gestao": (124, 45, 18),
        "setor_publico": (20, 83, 45),
    }

    TEMPLATES_SUPORTADOS = set(CORES_TEMPLATES)

    def gerar_pdf(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        dados_seguros = self._sanitizar_dados_pdf(dados)
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(18, 16, 18)
        pdf.add_page()
        self._renderizar_pdf_ats(pdf, dados_seguros, self.CORES_TEMPLATES[id_template])
        return bytes(pdf.output())

    def gerar_docx(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        documento = docx.Document()
        self._renderizar_docx_ats(documento, dados, self.CORES_TEMPLATES[id_template])
        buffer = io.BytesIO()
        documento.save(buffer)
        return buffer.getvalue()

    def _validar_template(self, id_template: str) -> None:
        if id_template not in self.TEMPLATES_SUPORTADOS:
            raise TemplateNaoSuportadoError(id_template)

    def _sanitizar_dados_pdf(self, dados: dict) -> dict:
        return {
            chave: self._sanitizar_texto_pdf(valor) if isinstance(valor, str) else valor
            for chave, valor in dados.items()
        }

    def _sanitizar_texto_pdf(self, texto: str) -> str:
        substituicoes = {
            "—": "-",
            "–": "-",
            "‘": "'",
            "’": "'",
            "“": '"',
            "”": '"',
            "…": "...",
            "•": "-",
            "\xa0": " ",
        }
        for original, novo in substituicoes.items():
            texto = texto.replace(original, novo)
        # A fonte padrão do PDF (Helvetica/Times) só desenha caracteres Latin-1. Em vez de
        # substituir cada caractere fora desse conjunto (ex.: emojis usados como marcador
        # decorativo) por "?" — o que aparecia no PDF exportado como um glifo quebrado —,
        # removemos esses caracteres e normalizamos os espaços que sobram no lugar deles.
        texto = "".join(caractere for caractere in texto if self._codificavel_latin1(caractere))
        texto = re.sub(r"[^\S\n]{2,}", " ", texto)
        texto = re.sub(r"(?m)^[ \t]+|[ \t]+$", "", texto)
        return texto.encode("latin-1", errors="replace").decode("latin-1")

    @staticmethod
    def _codificavel_latin1(caractere: str) -> bool:
        try:
            caractere.encode("latin-1")
            return True
        except UnicodeEncodeError:
            return False

    def _secoes(self, dados: dict) -> list[tuple[str, str]]:
        possui_dados_estruturados = any(
            (dados.get(campo) or "").strip() for campo in ("formacao", "experiencia_profissional", "habilidades")
        )
        if possui_dados_estruturados:
            secoes = [
                ("Resumo", dados.get("resumo", "")),
                ("Experiência Profissional", dados.get("experiencia_profissional", "")),
                ("Formação", dados.get("formacao", "")),
                ("Habilidades", dados.get("habilidades", "")),
            ]
        else:
            secoes = [("Currículo", dados.get("texto_bruto", ""))]
        return [(titulo, conteudo) for titulo, conteudo in secoes if (conteudo or "").strip()]

    def _cabecalho_contato(self, dados: dict) -> str:
        partes = [parte for parte in (dados.get("email"), dados.get("telefone")) if parte]
        return "   ·   ".join(partes)

    def _dividir_itens(self, texto: str) -> list[str]:
        itens = [linha.strip(" \t-•*") for linha in texto.split("\n")]
        return [item for item in itens if item]

    def _dividir_habilidades(self, texto: str) -> list[str]:
        itens = [item.strip(" \t-•*") for item in texto.split(",")]
        return [item for item in itens if item]

    # ---------- PDF: helpers de desenho compartilhados ----------

    def _linha_completa_pdf(self, pdf: FPDF) -> None:
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    def _renderizar_lista_pdf(
        self, pdf: FPDF, itens: list[str], cor_texto: tuple[int, int, int], cor_marcador: tuple[int, int, int]
    ) -> None:
        recuo = 5.5
        largura_conteudo = pdf.w - pdf.r_margin - (pdf.l_margin + recuo)
        for item in itens:
            y = pdf.get_y()
            pdf.set_fill_color(*cor_marcador)
            pdf.rect(pdf.l_margin, y + 2.3, 1.8, 1.8, style="F")
            pdf.set_xy(pdf.l_margin + recuo, y)
            pdf.set_text_color(*cor_texto)
            pdf.multi_cell(largura_conteudo, 5.6, item)
            pdf.set_x(pdf.l_margin)
        pdf.ln(1)

    def _renderizar_habilidades_pdf(self, pdf: FPDF, itens: list[str], cor_texto: tuple[int, int, int]) -> None:
        pdf.set_text_color(*cor_texto)
        pdf.multi_cell(0, 6, "   ·   ".join(itens))
        pdf.ln(1)

    # ---------- PDF: template ----------

    def _renderizar_pdf_ats(self, pdf: FPDF, dados: dict, cor_destaque: tuple[int, int, int]) -> None:
        cor_texto = (35, 35, 35)
        cor_secundaria = (95, 95, 95)

        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*cor_destaque)
        pdf.cell(0, 11, dados.get("nome") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*cor_secundaria)
        pdf.cell(0, 7, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.5)
        pdf.set_draw_color(*cor_destaque)
        pdf.set_line_width(0.8)
        self._linha_completa_pdf(pdf)
        pdf.ln(6)

        for titulo, conteudo in self._secoes(dados):
            modo = MODOS_SECAO.get(titulo, "paragrafo")
            pdf.set_font("Helvetica", "B", 12.5)
            pdf.set_text_color(*cor_destaque)
            pdf.cell(0, 8, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*cor_destaque)
            pdf.set_line_width(0.3)
            self._linha_completa_pdf(pdf)
            pdf.ln(3.5)
            pdf.set_font("Helvetica", "", 11)
            if modo == "lista":
                self._renderizar_lista_pdf(pdf, self._dividir_itens(conteudo), cor_texto, cor_destaque)
            elif modo == "habilidades":
                self._renderizar_habilidades_pdf(pdf, self._dividir_habilidades(conteudo), cor_texto)
            else:
                pdf.set_text_color(*cor_texto)
                pdf.multi_cell(0, 6, conteudo)
            pdf.ln(4)

    # ---------- DOCX: helpers compartilhados ----------

    def _adicionar_borda_inferior_docx(self, paragrafo, cor_hex: str, espessura: str = "10") -> None:
        p_pr = paragrafo._p.get_or_add_pPr()
        borda = OxmlElement("w:pBdr")
        inferior = OxmlElement("w:bottom")
        inferior.set(qn("w:val"), "single")
        inferior.set(qn("w:sz"), espessura)
        inferior.set(qn("w:space"), "6")
        inferior.set(qn("w:color"), cor_hex)
        borda.append(inferior)
        p_pr.append(borda)

    def _adicionar_lista_docx(self, documento: docx.Document, itens: list[str], cor: RGBColor | None = None) -> None:
        for item in itens:
            paragrafo = documento.add_paragraph(item, style="List Bullet")
            if cor is not None:
                for run in paragrafo.runs:
                    run.font.color.rgb = cor

    def _adicionar_habilidades_docx(
        self, documento: docx.Document, itens: list[str], cor: RGBColor | None = None, itálico: bool = False
    ) -> None:
        paragrafo = documento.add_paragraph()
        for indice, item in enumerate(itens):
            if indice > 0:
                run_separador = paragrafo.add_run("   ·   ")
                run_separador.font.color.rgb = RGBColor(0xA0, 0xA0, 0xA0)
            run = paragrafo.add_run(item)
            run.italic = itálico
            if cor is not None:
                run.font.color.rgb = cor

    def _adicionar_secao_docx(
        self,
        documento: docx.Document,
        titulo_secao: str,
        conteudo: str,
        cor_titulo: RGBColor | None,
        cor_corpo: RGBColor,
        itálico_habilidades: bool = False,
    ) -> None:
        cabecalho = documento.add_heading(titulo_secao.upper(), level=2)
        if cor_titulo is not None and cabecalho.runs:
            cabecalho.runs[0].font.color.rgb = cor_titulo
        modo = MODOS_SECAO.get(titulo_secao, "paragrafo")
        if modo == "lista":
            self._adicionar_lista_docx(documento, self._dividir_itens(conteudo), cor_corpo)
        elif modo == "habilidades":
            self._adicionar_habilidades_docx(
                documento, self._dividir_habilidades(conteudo), cor_corpo, itálico_habilidades
            )
        else:
            documento.add_paragraph(conteudo)

    # ---------- DOCX: template ----------

    def _renderizar_docx_ats(self, documento: docx.Document, dados: dict, cor_destaque_rgb: tuple[int, int, int]) -> None:
        cor_destaque = RGBColor(*cor_destaque_rgb)
        cor_hex = "%02X%02X%02X" % cor_destaque_rgb

        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_destaque
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(10)
        run_contato.font.color.rgb = RGBColor(0x5F, 0x5F, 0x5F)
        self._adicionar_borda_inferior_docx(paragrafo_contato, cor_hex)
        for titulo_secao, conteudo in self._secoes(dados):
            self._adicionar_secao_docx(documento, titulo_secao, conteudo, cor_destaque, cor_destaque)
