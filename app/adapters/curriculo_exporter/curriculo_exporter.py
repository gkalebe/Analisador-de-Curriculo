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
    """Gera PDF/DOCX em 3 templates de currículo (moderno, classico, minimalista).

    Layout sempre em coluna única, com títulos de seção padrão ("Experiência
    Profissional", "Formação", "Habilidades") e listas com marcadores reais —
    é o formato que passa melhor por leitores de ATS (Applicant Tracking
    System): colunas múltiplas, tabelas e ícones decorativos costumam
    embaralhar a ordem de leitura do texto extraído pelo parser. Cor é usada
    com moderação (no máximo 1 cor de destaque por template, texto principal
    sempre em preto/cinza escuro).
    """

    TEMPLATES_SUPORTADOS = {"moderno", "classico", "minimalista", "executivo", "criativo"}

    def gerar_pdf(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        dados_seguros = self._sanitizar_dados_pdf(dados)
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(18, 16, 18)
        pdf.add_page()
        renderizadores_pdf = {
            "moderno": self._renderizar_pdf_moderno,
            "classico": self._renderizar_pdf_classico,
            "minimalista": self._renderizar_pdf_minimalista,
            "executivo": self._renderizar_pdf_executivo,
            "criativo": self._renderizar_pdf_criativo,
        }
        renderizadores_pdf[id_template](pdf, dados_seguros)
        return bytes(pdf.output())

    def gerar_docx(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        documento = docx.Document()
        renderizadores_docx = {
            "moderno": self._renderizar_docx_moderno,
            "classico": self._renderizar_docx_classico,
            "minimalista": self._renderizar_docx_minimalista,
            "executivo": self._renderizar_docx_executivo,
            "criativo": self._renderizar_docx_criativo,
        }
        renderizadores_docx[id_template](documento, dados)
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

    def _renderizar_lista_travessao_pdf(self, pdf: FPDF, itens: list[str], cor_texto: tuple[int, int, int]) -> None:
        recuo = 5.5
        largura_conteudo = pdf.w - pdf.r_margin - (pdf.l_margin + recuo)
        for item in itens:
            y = pdf.get_y()
            pdf.set_text_color(*cor_texto)
            pdf.set_xy(pdf.l_margin, y)
            pdf.cell(recuo, 5.6, "-")
            pdf.set_xy(pdf.l_margin + recuo, y)
            pdf.multi_cell(largura_conteudo, 5.6, item)
            pdf.set_x(pdf.l_margin)
        pdf.ln(1)

    def _renderizar_habilidades_pdf(self, pdf: FPDF, itens: list[str], cor_texto: tuple[int, int, int]) -> None:
        pdf.set_text_color(*cor_texto)
        pdf.multi_cell(0, 6, "   ·   ".join(itens))
        pdf.ln(1)

    def _titulo_secao_barra_pdf(self, pdf: FPDF, titulo: str, cor_fundo: tuple[int, int, int]) -> None:
        """Título de seção com fundo sólido (usado no template 'executivo')."""
        pdf.set_fill_color(*cor_fundo)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f"  {titulo.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)

    def _titulo_secao_tick_pdf(
        self, pdf: FPDF, titulo: str, cor_destaque: tuple[int, int, int], cor_texto: tuple[int, int, int]
    ) -> None:
        """Título de seção com marcador vertical colorido à esquerda (usado no template 'criativo')."""
        y = pdf.get_y()
        pdf.set_fill_color(*cor_destaque)
        pdf.rect(pdf.l_margin, y + 1, 2.2, 6, style="F")
        pdf.set_xy(pdf.l_margin + 5.5, y)
        pdf.set_text_color(*cor_texto)
        pdf.cell(0, 8, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(pdf.l_margin)

    def _renderizar_habilidades_pills_pdf(
        self, pdf: FPDF, itens: list[str], cor_fundo: tuple[int, int, int], cor_texto: tuple[int, int, int]
    ) -> None:
        """Habilidades como tags arredondadas (usado no template 'criativo')."""
        pdf.set_font_size(9.5)
        altura = 7.2
        espaco = 2.5
        x, y = pdf.l_margin, pdf.get_y()
        limite_direito = pdf.w - pdf.r_margin
        for item in itens:
            largura = pdf.get_string_width(item) + 6.5
            if x + largura > limite_direito and x > pdf.l_margin:
                x = pdf.l_margin
                y += altura + espaco
            pdf.set_fill_color(*cor_fundo)
            pdf.rect(x, y, largura, altura, style="F", round_corners=True, corner_radius=altura / 2)
            pdf.set_text_color(*cor_texto)
            pdf.set_xy(x, y + 1.4)
            pdf.cell(largura, altura - 2, item, align="C")
            x += largura + espaco
        pdf.set_xy(pdf.l_margin, y + altura + 3)

    # ---------- PDF: templates ----------

    def _renderizar_pdf_moderno(self, pdf: FPDF, dados: dict) -> None:
        cor_destaque = (27, 94, 73)
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

    def _renderizar_pdf_classico(self, pdf: FPDF, dados: dict) -> None:
        cor_texto = (15, 15, 15)

        pdf.set_font("Times", "B", 21)
        pdf.set_text_color(*cor_texto)
        pdf.cell(0, 10, dados.get("nome") or "Currículo", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Times", "I", 11)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 7, self._cabecalho_contato(dados), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2.5)
        pdf.set_draw_color(*cor_texto)
        pdf.set_line_width(0.7)
        self._linha_completa_pdf(pdf)
        pdf.ln(0.8)
        pdf.set_line_width(0.2)
        self._linha_completa_pdf(pdf)
        pdf.ln(7)

        for titulo, conteudo in self._secoes(dados):
            modo = MODOS_SECAO.get(titulo, "paragrafo")
            pdf.set_font("Times", "B", 13)
            pdf.set_text_color(*cor_texto)
            pdf.cell(0, 8, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*cor_texto)
            pdf.set_line_width(0.2)
            self._linha_completa_pdf(pdf)
            pdf.ln(3.5)
            pdf.set_font("Times", "", 11)
            if modo == "lista":
                self._renderizar_lista_travessao_pdf(pdf, self._dividir_itens(conteudo), cor_texto)
            elif modo == "habilidades":
                pdf.set_font("Times", "I", 11)
                self._renderizar_habilidades_pdf(pdf, self._dividir_habilidades(conteudo), cor_texto)
            else:
                pdf.set_text_color(*cor_texto)
                pdf.multi_cell(0, 6, conteudo)
            pdf.ln(4)

    def _renderizar_pdf_minimalista(self, pdf: FPDF, dados: dict) -> None:
        cor_texto = (25, 25, 25)
        cor_rotulo = (120, 120, 120)
        cor_linha = (215, 215, 215)

        pdf.set_font("Helvetica", "", 19)
        pdf.set_text_color(*cor_texto)
        pdf.cell(0, 9, dados.get("nome") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*cor_rotulo)
        pdf.cell(0, 6, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
        pdf.set_draw_color(*cor_linha)
        pdf.set_line_width(0.25)
        self._linha_completa_pdf(pdf)
        pdf.ln(6)

        for titulo, conteudo in self._secoes(dados):
            modo = MODOS_SECAO.get(titulo, "paragrafo")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*cor_rotulo)
            pdf.cell(0, 6, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2.5)
            pdf.set_font("Helvetica", "", 10.5)
            if modo == "lista":
                self._renderizar_lista_travessao_pdf(pdf, self._dividir_itens(conteudo), cor_texto)
            elif modo == "habilidades":
                self._renderizar_habilidades_pdf(pdf, self._dividir_habilidades(conteudo), cor_texto)
            else:
                pdf.set_text_color(*cor_texto)
                pdf.multi_cell(0, 5.5, conteudo)
            pdf.ln(4.5)

    def _renderizar_pdf_executivo(self, pdf: FPDF, dados: dict) -> None:
        cor_destaque = (30, 58, 95)
        cor_texto = (30, 30, 30)
        cor_secundaria = (90, 90, 90)

        pdf.set_font("Helvetica", "B", 23)
        pdf.set_text_color(*cor_destaque)
        pdf.cell(0, 10, (dados.get("nome") or "Currículo").upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(*cor_secundaria)
        pdf.cell(0, 6, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)

        for titulo, conteudo in self._secoes(dados):
            modo = MODOS_SECAO.get(titulo, "paragrafo")
            self._titulo_secao_barra_pdf(pdf, titulo, cor_destaque)
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

    def _renderizar_pdf_criativo(self, pdf: FPDF, dados: dict) -> None:
        cor_destaque = (196, 90, 60)
        cor_texto = (40, 40, 40)

        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*cor_texto)
        pdf.cell(0, 10, dados.get("nome") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(*cor_destaque)
        pdf.cell(0, 6, self._cabecalho_contato(dados), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        pdf.set_draw_color(*cor_destaque)
        pdf.set_line_width(1.1)
        self._linha_completa_pdf(pdf)
        pdf.ln(6)

        for titulo, conteudo in self._secoes(dados):
            modo = MODOS_SECAO.get(titulo, "paragrafo")
            self._titulo_secao_tick_pdf(pdf, titulo, cor_destaque, cor_texto)
            pdf.ln(2.5)
            pdf.set_font("Helvetica", "", 11)
            if modo == "lista":
                self._renderizar_lista_pdf(pdf, self._dividir_itens(conteudo), cor_texto, cor_destaque)
            elif modo == "habilidades":
                self._renderizar_habilidades_pills_pdf(
                    pdf, self._dividir_habilidades(conteudo), cor_destaque, (255, 255, 255)
                )
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

    def _adicionar_fundo_paragrafo_docx(self, paragrafo, cor_hex: str) -> None:
        """Preenche o fundo de um parágrafo inteiro (usado no título de seção do 'executivo')."""
        p_pr = paragrafo._p.get_or_add_pPr()
        fundo = OxmlElement("w:shd")
        fundo.set(qn("w:val"), "clear")
        fundo.set(qn("w:color"), "auto")
        fundo.set(qn("w:fill"), cor_hex)
        p_pr.append(fundo)

    def _adicionar_borda_lateral_docx(self, paragrafo, cor_hex: str, espessura: str = "18") -> None:
        """Borda vertical à esquerda de um parágrafo (usado no título de seção do 'criativo')."""
        p_pr = paragrafo._p.get_or_add_pPr()
        borda = OxmlElement("w:pBdr")
        esquerda = OxmlElement("w:left")
        esquerda.set(qn("w:val"), "single")
        esquerda.set(qn("w:sz"), espessura)
        esquerda.set(qn("w:space"), "4")
        esquerda.set(qn("w:color"), cor_hex)
        borda.append(esquerda)
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

    # ---------- DOCX: templates ----------

    def _renderizar_docx_moderno(self, documento: docx.Document, dados: dict) -> None:
        cor_destaque = RGBColor(0x1B, 0x5E, 0x49)
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_destaque
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(10)
        run_contato.font.color.rgb = RGBColor(0x5F, 0x5F, 0x5F)
        self._adicionar_borda_inferior_docx(paragrafo_contato, "1B5E49")
        for titulo_secao, conteudo in self._secoes(dados):
            self._adicionar_secao_docx(documento, titulo_secao, conteudo, cor_destaque, cor_destaque)

    def _renderizar_docx_classico(self, documento: docx.Document, dados: dict) -> None:
        cor_texto = RGBColor(0x0F, 0x0F, 0x0F)
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        titulo.alignment = 1
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_texto
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.italic = True
        paragrafo_contato.alignment = 1
        self._adicionar_borda_inferior_docx(paragrafo_contato, "0F0F0F", espessura="6")
        for titulo_secao, conteudo in self._secoes(dados):
            self._adicionar_secao_docx(documento, titulo_secao, conteudo, cor_texto, cor_texto, itálico_habilidades=True)

    def _renderizar_docx_minimalista(self, documento: docx.Document, dados: dict) -> None:
        cor_texto = RGBColor(0x19, 0x19, 0x19)
        cor_rotulo = RGBColor(0x78, 0x78, 0x78)
        paragrafo_nome = documento.add_paragraph()
        run_nome = paragrafo_nome.add_run(dados.get("nome") or "Currículo")
        run_nome.font.size = Pt(18)
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(9.5)
        run_contato.font.color.rgb = cor_rotulo
        self._adicionar_borda_inferior_docx(paragrafo_contato, "D7D7D7", espessura="4")
        for titulo_secao, conteudo in self._secoes(dados):
            paragrafo_titulo = documento.add_paragraph()
            run_titulo = paragrafo_titulo.add_run(titulo_secao.upper())
            run_titulo.font.size = Pt(10)
            run_titulo.bold = True
            run_titulo.font.color.rgb = cor_rotulo
            modo = MODOS_SECAO.get(titulo_secao, "paragrafo")
            if modo == "lista":
                self._adicionar_lista_docx(documento, self._dividir_itens(conteudo), cor_texto)
            elif modo == "habilidades":
                self._adicionar_habilidades_docx(documento, self._dividir_habilidades(conteudo), cor_texto)
            else:
                paragrafo_corpo = documento.add_paragraph(conteudo)
                for run in paragrafo_corpo.runs:
                    run.font.color.rgb = cor_texto

    def _renderizar_docx_executivo(self, documento: docx.Document, dados: dict) -> None:
        cor_destaque = RGBColor(0x1E, 0x3A, 0x5F)
        cor_texto = RGBColor(0x1E, 0x1E, 0x1E)
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_destaque
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(10)
        run_contato.font.color.rgb = RGBColor(0x5A, 0x5A, 0x5A)
        for titulo_secao, conteudo in self._secoes(dados):
            cabecalho = documento.add_paragraph()
            run_cabecalho = cabecalho.add_run(f" {titulo_secao.upper()} ")
            run_cabecalho.bold = True
            run_cabecalho.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            self._adicionar_fundo_paragrafo_docx(cabecalho, "1E3A5F")
            modo = MODOS_SECAO.get(titulo_secao, "paragrafo")
            if modo == "lista":
                self._adicionar_lista_docx(documento, self._dividir_itens(conteudo), cor_texto)
            elif modo == "habilidades":
                self._adicionar_habilidades_docx(documento, self._dividir_habilidades(conteudo), cor_texto)
            else:
                documento.add_paragraph(conteudo)

    def _renderizar_docx_criativo(self, documento: docx.Document, dados: dict) -> None:
        cor_destaque = RGBColor(0xC4, 0x5A, 0x3C)
        cor_texto = RGBColor(0x28, 0x28, 0x28)
        titulo = documento.add_heading(dados.get("nome") or "Currículo", level=0)
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_texto
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.bold = True
        run_contato.font.color.rgb = cor_destaque
        self._adicionar_borda_inferior_docx(paragrafo_contato, "C45A3C", espessura="14")
        for titulo_secao, conteudo in self._secoes(dados):
            cabecalho = documento.add_paragraph()
            run_cabecalho = cabecalho.add_run(titulo_secao.upper())
            run_cabecalho.bold = True
            run_cabecalho.font.color.rgb = cor_texto
            self._adicionar_borda_lateral_docx(cabecalho, "C45A3C")
            modo = MODOS_SECAO.get(titulo_secao, "paragrafo")
            if modo == "lista":
                self._adicionar_lista_docx(documento, self._dividir_itens(conteudo), cor_texto)
            elif modo == "habilidades":
                self._adicionar_habilidades_docx(documento, self._dividir_habilidades(conteudo), cor_destaque)
            else:
                documento.add_paragraph(conteudo)
