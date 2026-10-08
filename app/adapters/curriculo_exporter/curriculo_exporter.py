import io
import re

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.adapters.ai_service.curriculo_schema import DadosCurriculoEstruturado


class TemplateNaoSuportadoError(Exception):
    pass


class CurriculoExporter:
    """Gera PDF/DOCX em 5 templates de currículo voltados a triagem por ATS
    (generico, tecnologia, estagio, gestao, setor_publico).

    A entrada é o currículo estruturado (`DadosCurriculoEstruturado` serializado em
    dict, opcionalmente com `texto_bruto`): contato, resumo, experiências com seus
    bullets, formação, habilidades, idiomas, certificações e `secoes_adicionais`
    (qualquer outra seção do currículo original). O exportador NUNCA resume nem
    descarta nada — renderiza todas as seções que vierem preenchidas, na ordem
    padrão de ATS, e só omite seções vazias. Se não houver nenhum dado estruturado
    (IA indisponível), cai para uma seção única "Currículo" com o texto bruto.

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

    TITULO_SECAO_ADICIONAL_PADRAO = "Informações Adicionais"

    def gerar_pdf(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        dados_seguros = self._sanitizar_pdf(self._preparar_dados(dados))
        pdf = FPDF(format="A4")
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(18, 16, 18)
        pdf.add_page()
        self._renderizar_pdf_ats(pdf, dados_seguros, self.CORES_TEMPLATES[id_template])
        return bytes(pdf.output())

    def gerar_docx(self, dados: dict, id_template: str) -> bytes:
        self._validar_template(id_template)
        documento = docx.Document()
        self._renderizar_docx_ats(documento, self._preparar_dados(dados), self.CORES_TEMPLATES[id_template])
        buffer = io.BytesIO()
        documento.save(buffer)
        return buffer.getvalue()

    def _validar_template(self, id_template: str) -> None:
        if id_template not in self.TEMPLATES_SUPORTADOS:
            raise TemplateNaoSuportadoError(id_template)

    # ---------- Dados ----------

    def _preparar_dados(self, dados: dict) -> dict:
        """Garante o shape do schema (campos ausentes viram vazios, extras são ignorados)
        e preserva `texto_bruto` para o fallback sem dados estruturados."""
        dados = dados or {}
        estruturado = DadosCurriculoEstruturado.model_validate(
            {chave: valor for chave, valor in dados.items() if chave in DadosCurriculoEstruturado.model_fields}
        ).model_dump()
        return estruturado | {"texto_bruto": dados.get("texto_bruto") or ""}

    def _sanitizar_pdf(self, valor):
        if isinstance(valor, str):
            return self._sanitizar_texto_pdf(valor)
        if isinstance(valor, dict):
            return {chave: self._sanitizar_pdf(item) for chave, item in valor.items()}
        if isinstance(valor, (list, tuple)):
            return type(valor)(self._sanitizar_pdf(item) for item in valor)
        return valor

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

    @staticmethod
    def _possui_dados_estruturados(dados: dict) -> bool:
        if any((dados.get(campo) or "").strip() for campo in ("resumo_profissional", "titulo_profissional")):
            return True
        return any(
            dados.get(campo)
            for campo in ("experiencias", "formacao", "habilidades_tecnicas", "idiomas", "certificacoes", "secoes_adicionais")
        )

    def _secoes(self, dados: dict) -> list[tuple[str, str, object]]:
        """Seções a renderizar, na ordem padrão de ATS: (título, modo, conteúdo).

        Modos: "paragrafo" (str), "experiencias" (lista de dicts de experiência),
        "lista" (lista de str com marcadores) e "habilidades" (lista de str em linha).
        Seções sem conteúdo são omitidas; as `secoes_adicionais` do currículo original
        entram no fim, com o título que tinham no currículo."""
        if not self._possui_dados_estruturados(dados):
            texto_bruto = (dados.get("texto_bruto") or "").strip()
            return [("Currículo", "paragrafo", texto_bruto)] if texto_bruto else []

        secoes: list[tuple[str, str, object]] = [
            ("Resumo", "paragrafo", (dados.get("resumo_profissional") or "").strip()),
            ("Experiência Profissional", "experiencias", self._experiencias_com_conteudo(dados.get("experiencias") or [])),
            ("Formação", "lista", [self._descrever_formacao(item) for item in dados.get("formacao") or []]),
            ("Habilidades", "habilidades", [item for item in dados.get("habilidades_tecnicas") or [] if item]),
            ("Idiomas", "lista", [self._descrever_idioma(item) for item in dados.get("idiomas") or []]),
            ("Certificações", "lista", [item for item in dados.get("certificacoes") or [] if item]),
        ]
        for secao in dados.get("secoes_adicionais") or []:
            itens = [item for item in secao.get("itens") or [] if item]
            titulo = (secao.get("titulo") or "").strip() or self.TITULO_SECAO_ADICIONAL_PADRAO
            secoes.append((titulo, "lista", itens))

        return [
            (titulo, modo, conteudo)
            for titulo, modo, conteudo in secoes
            if (conteudo.strip() if isinstance(conteudo, str) else [item for item in conteudo if item])
        ]

    @staticmethod
    def _experiencias_com_conteudo(experiencias: list[dict]) -> list[dict]:
        return [
            experiencia
            for experiencia in experiencias
            if any(experiencia.get(campo) for campo in ("cargo", "empresa", "periodo_inicio", "periodo_fim", "descricao_bullets"))
        ]

    @staticmethod
    def _titulo_experiencia(experiencia: dict) -> str:
        return " — ".join(parte for parte in (experiencia.get("cargo"), experiencia.get("empresa")) if parte)

    @staticmethod
    def _periodo_experiencia(experiencia: dict) -> str:
        return " - ".join(parte for parte in (experiencia.get("periodo_inicio"), experiencia.get("periodo_fim")) if parte)

    @staticmethod
    def _descrever_formacao(formacao: dict) -> str:
        texto = " — ".join(parte for parte in (formacao.get("curso"), formacao.get("instituicao")) if parte)
        periodo = (formacao.get("periodo") or "").strip()
        if periodo:
            texto = f"{texto} ({periodo})" if texto else periodo
        return texto

    @staticmethod
    def _descrever_idioma(idioma: dict) -> str:
        return " — ".join(parte for parte in (idioma.get("idioma"), idioma.get("nivel")) if parte)

    def _cabecalho_contato(self, dados: dict) -> str:
        contato = dados.get("contato") or {}
        partes = [contato.get(chave) for chave in ("email", "telefone", "linkedin", "cidade")]
        return "   ·   ".join(parte for parte in partes if parte)

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

    def _renderizar_experiencias_pdf(
        self,
        pdf: FPDF,
        experiencias: list[dict],
        cor_texto: tuple[int, int, int],
        cor_secundaria: tuple[int, int, int],
        cor_marcador: tuple[int, int, int],
    ) -> None:
        for experiencia in experiencias:
            # Os separadores (" — ") são inseridos aqui, depois da sanitização dos dados,
            # então precisam passar pela mesma sanitização antes de ir para a fonte Latin-1.
            titulo = self._sanitizar_texto_pdf(self._titulo_experiencia(experiencia))
            periodo = self._sanitizar_texto_pdf(self._periodo_experiencia(experiencia))
            if titulo:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(*cor_texto)
                pdf.multi_cell(0, 6, titulo, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if periodo:
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(*cor_secundaria)
                pdf.multi_cell(0, 5.5, periodo, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 11)
            bullets = [bullet for bullet in experiencia.get("descricao_bullets") or [] if bullet]
            if bullets:
                self._renderizar_lista_pdf(pdf, bullets, cor_texto, cor_marcador)
            pdf.ln(1.5)

    # ---------- PDF: template ----------

    def _renderizar_pdf_ats(self, pdf: FPDF, dados: dict, cor_destaque: tuple[int, int, int]) -> None:
        cor_texto = (35, 35, 35)
        cor_secundaria = (95, 95, 95)

        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*cor_destaque)
        pdf.cell(0, 11, dados.get("nome_completo") or "Currículo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if dados.get("titulo_profissional"):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(*cor_secundaria)
            pdf.cell(0, 7, dados["titulo_profissional"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        contato = self._cabecalho_contato(dados)
        if contato:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*cor_secundaria)
            pdf.multi_cell(0, 7, contato, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.5)
        pdf.set_draw_color(*cor_destaque)
        pdf.set_line_width(0.8)
        self._linha_completa_pdf(pdf)
        pdf.ln(6)

        # `_secoes` monta descrições compostas ("Curso — Instituição (período)") depois da
        # sanitização inicial dos dados, por isso o resultado é sanitizado de novo.
        for titulo, modo, conteudo in self._sanitizar_pdf(self._secoes(dados)):
            pdf.set_font("Helvetica", "B", 12.5)
            pdf.set_text_color(*cor_destaque)
            pdf.cell(0, 8, titulo.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*cor_destaque)
            pdf.set_line_width(0.3)
            self._linha_completa_pdf(pdf)
            pdf.ln(3.5)
            pdf.set_font("Helvetica", "", 11)
            if modo == "experiencias":
                self._renderizar_experiencias_pdf(pdf, conteudo, cor_texto, cor_secundaria, cor_destaque)
            elif modo == "lista":
                self._renderizar_lista_pdf(pdf, conteudo, cor_texto, cor_destaque)
            elif modo == "habilidades":
                self._renderizar_habilidades_pdf(pdf, conteudo, cor_texto)
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

    def _adicionar_habilidades_docx(self, documento: docx.Document, itens: list[str], cor: RGBColor | None = None) -> None:
        paragrafo = documento.add_paragraph()
        for indice, item in enumerate(itens):
            if indice > 0:
                run_separador = paragrafo.add_run("   ·   ")
                run_separador.font.color.rgb = RGBColor(0xA0, 0xA0, 0xA0)
            run = paragrafo.add_run(item)
            if cor is not None:
                run.font.color.rgb = cor

    def _adicionar_experiencias_docx(self, documento: docx.Document, experiencias: list[dict], cor_corpo: RGBColor) -> None:
        for experiencia in experiencias:
            titulo = self._titulo_experiencia(experiencia)
            periodo = self._periodo_experiencia(experiencia)
            if titulo or periodo:
                paragrafo = documento.add_paragraph()
                if titulo:
                    run_titulo = paragrafo.add_run(titulo)
                    run_titulo.bold = True
                    run_titulo.font.color.rgb = cor_corpo
                if periodo:
                    run_periodo = paragrafo.add_run(f"   {periodo}" if titulo else periodo)
                    run_periodo.italic = True
                    run_periodo.font.size = Pt(10)
                    run_periodo.font.color.rgb = RGBColor(0x5F, 0x5F, 0x5F)
            bullets = [bullet for bullet in experiencia.get("descricao_bullets") or [] if bullet]
            self._adicionar_lista_docx(documento, bullets, cor_corpo)

    def _adicionar_secao_docx(
        self,
        documento: docx.Document,
        titulo_secao: str,
        modo: str,
        conteudo,
        cor_titulo: RGBColor | None,
        cor_corpo: RGBColor,
    ) -> None:
        cabecalho = documento.add_heading(titulo_secao.upper(), level=2)
        if cor_titulo is not None and cabecalho.runs:
            cabecalho.runs[0].font.color.rgb = cor_titulo
        if modo == "experiencias":
            self._adicionar_experiencias_docx(documento, conteudo, cor_corpo)
        elif modo == "lista":
            self._adicionar_lista_docx(documento, conteudo, cor_corpo)
        elif modo == "habilidades":
            self._adicionar_habilidades_docx(documento, conteudo, cor_corpo)
        else:
            documento.add_paragraph(conteudo)

    # ---------- DOCX: template ----------

    def _renderizar_docx_ats(self, documento: docx.Document, dados: dict, cor_destaque_rgb: tuple[int, int, int]) -> None:
        cor_destaque = RGBColor(*cor_destaque_rgb)
        cor_hex = "%02X%02X%02X" % cor_destaque_rgb

        titulo = documento.add_heading(dados.get("nome_completo") or "Currículo", level=0)
        if titulo.runs:
            titulo.runs[0].font.color.rgb = cor_destaque
        if dados.get("titulo_profissional"):
            paragrafo_titulo = documento.add_paragraph()
            run_titulo = paragrafo_titulo.add_run(dados["titulo_profissional"])
            run_titulo.bold = True
            run_titulo.font.color.rgb = RGBColor(0x5F, 0x5F, 0x5F)
        paragrafo_contato = documento.add_paragraph()
        run_contato = paragrafo_contato.add_run(self._cabecalho_contato(dados))
        run_contato.font.size = Pt(10)
        run_contato.font.color.rgb = RGBColor(0x5F, 0x5F, 0x5F)
        self._adicionar_borda_inferior_docx(paragrafo_contato, cor_hex)
        for titulo_secao, modo, conteudo in self._secoes(dados):
            self._adicionar_secao_docx(documento, titulo_secao, modo, conteudo, cor_destaque, cor_destaque)
