class FormatoNaoSuportadoError(Exception):
    pass


class CurriculoParser:
    FORMATOS_SUPORTADOS = {"pdf", "docx"}

    def extrair_texto(self, conteudo: bytes, extensao: str) -> str:
        extensao_normalizada = extensao.lower().lstrip(".")
        if extensao_normalizada not in self.FORMATOS_SUPORTADOS:
            raise FormatoNaoSuportadoError(extensao_normalizada)
        if extensao_normalizada == "pdf":
            return self._extrair_texto_pdf(conteudo)
        return self._extrair_texto_docx(conteudo)

    def _extrair_texto_pdf(self, conteudo: bytes) -> str:
        raise NotImplementedError

    def _extrair_texto_docx(self, conteudo: bytes) -> str:
        raise NotImplementedError
