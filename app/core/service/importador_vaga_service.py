import ipaddress
import json
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse
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
    for item in _itens_json_ld(documentos):
        for chave in chaves:
            valor = item.get(chave)
            if isinstance(valor, str) and valor.strip():
                return valor.strip()
            if isinstance(valor, list):
                valores = [str(parte).strip() for parte in valor if isinstance(parte, str) and parte.strip()]
                if valores:
                    return ", ".join(valores)
    return ""


def _itens_json_ld(documentos):
    itens = []
    pendentes = list(documentos)
    while pendentes:
        item = pendentes.pop(0)
        if isinstance(item, list):
            pendentes.extend(item)
        elif isinstance(item, dict):
            itens.append(item)
            grafo = item.get("@graph", [])
            pendentes.extend(grafo if isinstance(grafo, list) else [grafo])
    return itens


def _texto_html(valor):
    class _TextoParser(HTMLParser):
        _TAGS_BLOCO = {"address", "article", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "section", "ul"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.partes = []

        def handle_starttag(self, tag, _attrs):
            if tag == "br" or tag in self._TAGS_BLOCO:
                self.partes.append("\n")
            if tag == "li":
                self.partes.append("- ")

        def handle_endtag(self, tag):
            if tag in self._TAGS_BLOCO:
                self.partes.append("\n")

        def handle_data(self, data):
            self.partes.append(data)

    parser = _TextoParser()
    parser.feed(unescape(valor))
    return _normalizar_texto("".join(parser.partes))


def _normalizar_texto(valor):
    valor = re.sub(r":\s*[-•]\s+", ":\n- ", valor)
    valor = re.sub(r"(?<=[.!?])\s+[-•]\s+", "\n- ", valor)
    linhas = [" ".join(linha.split()) for linha in valor.splitlines()]
    return "\n".join(linha for linha in linhas if linha)


_PADROES_SECOES_VAGA = (
    (
        "responsabilidades",
        re.compile(
            r"(?i)(?:o que voc[eê] vai fazer|responsabilidades|what you(?:'|’)ll do|"
            r"what you will do|responsibilities|your role)\s*:"
        ),
    ),
    (
        "requisitos_desejaveis",
        re.compile(
            r"(?i)(?:requisitos? desej[aá]veis|qualifica[cç][oõ]es preferenciais|"
            r"diferenciais|ser[aá] um diferencial|nice to have|preferred qualifications)\s*:"
        ),
    ),
    (
        "requisitos_obrigatorios",
        re.compile(
            r"(?i)(?:esperamos que voc[eê] tenha|requisitos? obrigat[oó]rios|"
            r"requisitos?|qualifica[cç][oõ]es|o que esperamos|what we(?:'|’)re looking for|"
            r"what you bring|requirements|qualifications|must have)\s*:"
        ),
    ),
    (
        "beneficios",
        re.compile(
            r"(?i)(?:como tornamos seu trabalho.*?mais f[aá]cil|benef[ií]cios|"
            r"o que oferecemos|what we offer|perks and benefits)\s*:"
        ),
    ),
)


def _separar_requisitos_por_preferencia(texto):
    obrigatorios = []
    desejaveis = []
    for linha in texto.splitlines():
        conteudo = re.sub(r"^\s*[-*•]\s*", "", linha).strip()
        if not conteudo:
            continue
        if re.match(r"(?i)^(?:desej[aá]vel|ser[aá] um diferencial|diferencial|nice to have)\b", conteudo):
            desejaveis.append(conteudo)
        else:
            obrigatorios.append(conteudo)
    return "\n".join(obrigatorios), "\n".join(desejaveis)


def _separar_secoes_vaga(texto):
    ocorrencias = []
    for nome, padrao in _PADROES_SECOES_VAGA:
        ocorrencias.extend((match.start(), match.end(), nome) for match in padrao.finditer(texto))
    ocorrencias.sort()
    if not ocorrencias:
        return {"descricao": texto}

    campos = {"responsabilidades": [], "requisitos_obrigatorios": [], "requisitos_desejaveis": [], "beneficios": []}
    descricao = [texto[:ocorrencias[0][0]].strip()]
    for indice, (_, inicio_conteudo, campo) in enumerate(ocorrencias):
        fim = ocorrencias[indice + 1][0] if indice + 1 < len(ocorrencias) else len(texto)
        conteudo = texto[inicio_conteudo:fim].strip()
        if campo == "requisitos_obrigatorios":
            obrigatorios, desejaveis = _separar_requisitos_por_preferencia(conteudo)
            if obrigatorios:
                campos["requisitos_obrigatorios"].append(obrigatorios)
            if desejaveis:
                campos["requisitos_desejaveis"].append(desejaveis)
        else:
            campos[campo].append(conteudo)

    resultado = {"descricao": "\n\n".join(parte for parte in descricao if parte)}
    resultado.update({campo: "\n".join(valores) for campo, valores in campos.items()})
    return resultado


def _valor_aninhado(documentos, chave_pai, chave_filha):
    for item in _itens_json_ld(documentos):
        pai = item.get(chave_pai)
        valores = pai if isinstance(pai, list) else [pai]
        for valor in valores:
            if isinstance(valor, dict):
                texto = valor.get(chave_filha)
                if isinstance(texto, str) and texto.strip():
                    return texto.strip()
    return ""


def _localizacao_json_ld(documentos):
    for item in _itens_json_ld(documentos):
        localizacoes = item.get("jobLocation", [])
        localizacoes = localizacoes if isinstance(localizacoes, list) else [localizacoes]
        for localizacao in localizacoes:
            if not isinstance(localizacao, dict):
                continue
            endereco = localizacao.get("address", {})
            if not isinstance(endereco, dict):
                continue
            partes = [
                endereco.get("addressLocality"),
                endereco.get("addressRegion"),
                endereco.get("addressCountry"),
            ]
            resultado = ", ".join(parte.strip() for parte in partes if isinstance(parte, str) and parte.strip())
            if resultado:
                return resultado
    return ""


def _salario_json_ld(documentos):
    for item in _itens_json_ld(documentos):
        salario = item.get("baseSalary")
        if not isinstance(salario, dict):
            continue
        valor = salario.get("value")
        if isinstance(valor, dict):
            minimo = valor.get("minValue")
            maximo = valor.get("maxValue")
            quantidade = str(minimo or "")
            if maximo and maximo != minimo:
                quantidade = f"{quantidade}–{maximo}" if quantidade else str(maximo)
            unidade = valor.get("unitText")
            moeda = salario.get("currency")
            if quantidade:
                return " ".join(str(parte) for parte in (moeda, quantidade, unidade) if parte)
        elif valor:
            return " ".join(str(parte) for parte in (salario.get("currency"), valor) if parte)
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
    requisitos = _primeiro_valor_json_ld(
        dados["json_ld"], ["qualifications", "experienceRequirements"]
    )
    competencias = _primeiro_valor_json_ld(dados["json_ld"], ["skills"])
    area = _primeiro_valor_json_ld(dados["json_ld"], ["occupationalCategory"])
    descricao = _texto_html(descricao) if descricao else _normalizar_texto(dados["texto"])
    secoes = _separar_secoes_vaga(descricao)
    titulo_normalizado = " ".join((titulo or "Vaga importada").split())[:200]
    descricao = secoes["descricao"] or (titulo_normalizado if "responsabilidades" in secoes else descricao)

    if not descricao:
        raise ImportacaoVagaError("Não encontramos uma descrição de vaga nessa página.")
    if len(descricao) > limite_caracteres:
        raise ImportacaoVagaError(
            f"A descrição excede o limite de {limite_caracteres} caracteres. "
            "Cole manualmente a parte relevante da vaga."
        )

    organizacao = _valor_aninhado(dados["json_ld"], "hiringOrganization", "name")
    modalidade = _primeiro_valor_json_ld(dados["json_ld"], ["jobLocationType"])
    if modalidade.upper() == "TELECOMMUTE":
        modalidade = "Remoto"
    responsabilidades = _texto_html(
        _primeiro_valor_json_ld(dados["json_ld"], ["responsibilities"])
    ) or secoes.get("responsabilidades", "")
    requisitos_obrigatorios, requisitos_desejaveis = _separar_requisitos_por_preferencia(
        _texto_html(requisitos) if requisitos else ""
    )
    requisitos_obrigatorios = "\n".join(
        parte for parte in (requisitos_obrigatorios, secoes.get("requisitos_obrigatorios", "")) if parte
    )
    requisitos_desejaveis = "\n".join(
        parte for parte in (requisitos_desejaveis, secoes.get("requisitos_desejaveis", "")) if parte
    )
    beneficios = _texto_html(_primeiro_valor_json_ld(dados["json_ld"], ["benefits"]))
    beneficios = beneficios or secoes.get("beneficios", "")

    return {
        "titulo": " ".join((titulo or "Vaga importada").split())[:200],
        "descricao": descricao,
        "requisitos": "",
        "area": " ".join((area or "").split())[:100],
        "empresa": organizacao[:200],
        "localizacao": _localizacao_json_ld(dados["json_ld"])[:200],
        "modalidade": modalidade[:100],
        "senioridade": "",
        "tipo_contratacao": _primeiro_valor_json_ld(dados["json_ld"], ["employmentType"])[:100],
        "faixa_salarial": _salario_json_ld(dados["json_ld"])[:200],
        "responsabilidades": responsabilidades[:10000],
        "requisitos_obrigatorios": requisitos_obrigatorios[:10000],
        "requisitos_desejaveis": requisitos_desejaveis[:10000],
        "competencias": " ".join((competencias or "").split())[:5000],
        "idiomas": "",
        "beneficios": beneficios[:5000],
        "url_origem": url,
    }