import io

import docx
from docx.shared import Pt, RGBColor
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class TemplateNaoSuportadoError(Exception):
    pass


class CurriculoExporter:
    TEMPLATES_SUPORTADOS = {"moderno", "classico", "minimalista"}

    def gerar_pdf(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        dados_seguros = self._sanitizar_dados_pdf(dados)
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.add_page()
        if id_template == "moderno":
            self._renderizar_pdf_moderno(pdf, dados_seguros)
        elif id_template == "classico":
            self._renderizar_pdf_classico(pdf, dados_seguros)
        else:
            self._renderizar_pdf_minimalista(pdf, dados_seguros)
        return bytes(pdf.output())

    def gerar_docx(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        documento = docx.Document()
        if id_template == "moderno":
            self._renderizar_docx_moderno(documento, dados)
        elif id_template == "classico":
            self._renderizar_docx_classico(documento, dados)
        else:
            self._renderizar_docx_minimalista(documento, dados)
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
        return texto.encode("latin-1", errors="replace").decode("latin-1")

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
        return " · ".join(partes)

    def _renderizar_pdf_moderno(self, pdf: FPDF, dados: dict) -> None:
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(30, 94, 63)
        pdf.cell(0, 12, dados.get("nome") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 8, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        for titulo, conteudo in self._secoes(dados):
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(30, 94, 63)
            pdf.cell(0, 9, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(30, 94, 63)
            pdf.set_line_width(0.6)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
            pdf.ln(3)
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, conteudo)
            pdf.ln(3)

    def _renderizar_pdf_classico(self, pdf: FPDF, dados: dict) -> None:
        pdf.set_font("Times", "B", 20)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, dados.get("nome") or "Currículo", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Times", "", 11)
        pdf.cell(0, 7, self._cabecalho_contato(dados), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        pdf.set_draw_color(0, 0, 0)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)
        for titulo, conteudo in self._secoes(dados):
            pdf.set_font("Times", "B", 13)
            pdf.cell(0, 8, titulo, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Times", "", 11)
            pdf.multi_cell(0, 6, conteudo)
            pdf.ln(3)

    def _renderizar_pdf_minimalista(self, pdf: FPDF, dados: dict) -> None:
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 8, dados.get("nome") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 6, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        for titulo, conteudo in self._secoes(dados):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(110, 110, 110)
            pdf.cell(0, 6, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(20, 20, 20)
            pdf.multi_cell(0, 5, conteudo)
            pdf.ln(2)

    def _renderizar_docx_moderno(self, documento: docx.Document, dados: dict) -> None:
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        titulo.runs[0].font.color.rgb = RGBColor(0x1E, 0x5E, 0x3F)
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(10)
        for titulo_secao, conteudo in self._secoes(dados):
            cabecalho = documento.add_heading(titulo_secao.upper(), level=2)
            cabecalho.runs[0].font.color.rgb = RGBColor(0x1E, 0x5E, 0x3F)
            documento.add_paragraph(conteudo)

    def _renderizar_docx_classico(self, documento: docx.Document, dados: dict) -> None:
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        titulo.alignment = 1
        paragrafo_contato = documento.add_paragraph()
        paragrafo_contato.add_run(self._cabecalho_contato(dados))
        paragrafo_contato.alignment = 1
        for titulo_secao, conteudo in self._secoes(dados):
            documento.add_heading(titulo_secao, level=2)
            documento.add_paragraph(conteudo)

    def _renderizar_docx_minimalista(self, documento: docx.Document, dados: dict) -> None:
        paragrafo_nome = documento.add_paragraph()
        run_nome = paragrafo_nome.add_run(dados.get("nome") or "Currículo")
        run_nome.font.size = Pt(16)
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(9)
        for titulo_secao, conteudo in self._secoes(dados):
            paragrafo_titulo = documento.add_paragraph()
            run_titulo = paragrafo_titulo.add_run(titulo_secao.upper())
            run_titulo.font.size = Pt(10)
            run_titulo.bold = True
            documento.add_paragraph(conteudo)
