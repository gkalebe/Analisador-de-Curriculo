import ipaddress
import json
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ImportacaoVagaError(Exception):
    pass


class _RedirecionamentoSeguro(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, new):
        _validar_url_publica(new)
        return super().redirect_request(req, fp, code, msg, headers, new)


class _PaginaVagaParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo = ""
        self.descricao_meta = ""
        self.json_ld = []
        self._titulo_atual = False
        self._meta = {}
        self._script_json_ld = False
        self._script_conteudo = []
        self._texto = []

    def handle_starttag(self, tag, attrs):
        atributos = dict(attrs)
        if tag == "title":
            self._titulo_atual = True
        elif tag == "meta":
            chave = (atributos.get("name") or atributos.get("property") or "").lower()
            conteudo = atributos.get("content", "").strip()
            if chave and conteudo:
                self._meta[chave] = conteudo
        elif tag == "script" and atributos.get("type", "").lower() == "application/ld+json":
            self._script_json_ld = True
            self._script_conteudo = []

    def handle_endtag(self, tag):
        if tag == "title":
            self._titulo_atual = False
        elif tag == "script" and self._script_json_ld:
            try:
                self.json_ld.append(json.loads("".join(self._script_conteudo)))
            except (json.JSONDecodeError, TypeError):
                pass
            self._script_json_ld = False
            self._script_conteudo = []

    def handle_data(self, data):
        if self._titulo_atual:
            self.titulo += data
        if self._script_json_ld:
            self._script_conteudo.append(data)
        elif data.strip():
            self._texto.append(data.strip())

    def resultado(self):
        return {
            "titulo": self._meta.get("og:title") or self.titulo.strip(),
            "descricao": self._meta.get("og:description") or self._meta.get("description", ""),
            "texto": " ".join(self._texto),
            "json_ld": self.json_ld,
        }


def _validar_url_publica(url: str) -> None:
    partes = urlparse(url)
    if partes.scheme not in {"http", "https"} or not partes.hostname:
        raise ImportacaoVagaError("Informe uma URL pública iniciando com http:// ou https://.")

    try:
        enderecos = socket.getaddrinfo(partes.hostname, partes.port or (443 if partes.scheme == "https" else 80))
    except socket.gaierror as erro:
        raise ImportacaoVagaError("Não foi possível localizar o endereço da vaga.") from erro

    for endereco in {item[4][0] for item in enderecos}:
        ip = ipaddress.ip_address(endereco)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ImportacaoVagaError("Por segurança, a URL precisa apontar para um endereço público.")


def _primeiro_valor_json_ld(documentos, chaves):
    for documento in documentos:
        itens = documento if isinstance(documento, list) else [documento]
        for item in itens:
            if not isinstance(item, dict):
                continue
            if "@graph" in item:
                itens.extend(item["@graph"] if isinstance(item["@graph"], list) else [item["@graph"]])
            tipos = item.get("@type", [])
            tipos = tipos if isinstance(tipos, list) else [tipos]
            if "JobPosting" in tipos or any(chave in item for chave in chaves):
                for chave in chaves:
                    valor = item.get(chave)
                    if isinstance(valor, str) and valor.strip():
                        return valor.strip()
    return ""


def importar_vaga(url: str, limite_caracteres: int) -> dict[str, str]:
    _validar_url_publica(url)
    requisicao = Request(url, headers={"User-Agent": "AnalisadorDeCurriculos/1.0"})
    try:
        resposta = build_opener(_RedirecionamentoSeguro()).open(requisicao, timeout=10)
        conteudo = resposta.read(1_500_000)
        charset = resposta.headers.get_content_charset() or "utf-8"
        html = conteudo.decode(charset, errors="replace")
    except ImportacaoVagaError:
        raise
    except Exception as erro:
        raise ImportacaoVagaError("Não foi possível acessar a página da vaga.") from erro

    parser = _PaginaVagaParser()
    parser.feed(html)
    dados = parser.resultado()
    titulo = _primeiro_valor_json_ld(dados["json_ld"], ["title"]) or dados["titulo"]
    descricao = _primeiro_valor_json_ld(dados["json_ld"], ["description"]) or dados["descricao"]
    requisitos = _primeiro_valor_json_ld(dados["json_ld"], ["qualifications", "skills"])
    area = _primeiro_valor_json_ld(dados["json_ld"], ["occupationalCategory"])
    descricao = descricao or dados["texto"]
    descricao = " ".join(descricao.split())[:limite_caracteres]

    if not descricao:
        raise ImportacaoVagaError("Não encontramos uma descrição de vaga nessa página.")

    return {
        "titulo": " ".join((titulo or "Vaga importada").split())[:200],
        "descricao": descricao,
        "requisitos": " ".join((requisitos or "").split())[:5000],
        "area": " ".join((area or "").split())[:100],
        "url_origem": url,
    }