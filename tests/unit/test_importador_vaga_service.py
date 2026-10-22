import io
import json

import pytest

from app.core.service import importador_vaga_service as importador


class RespostaHttpFalsa(io.BytesIO):
    headers = type("Headers", (), {"get_content_charset": lambda self: "utf-8"})()


class OpenerFalso:
    def __init__(self, html):
        self.html = html

    def open(self, requisicao, timeout):
        return RespostaHttpFalsa(self.html.encode())


def test_importar_vaga_extrai_campos_estruturados_sem_tags_html(monkeypatch):
    html = """
    <html><head><script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Engenheira de Software",
      "description": "<p>Desenvolver <strong>serviços</strong> de dados.</p>",
      "hiringOrganization": {"name": "Empresa Exemplo"},
      "jobLocation": {"address": {"addressLocality": "São Paulo", "addressRegion": "SP"}},
      "jobLocationType": "TELECOMMUTE",
      "employmentType": "FULL_TIME",
      "qualifications": "Experiência com Python",
      "skills": ["Python", "SQL"],
      "responsibilities": "<ul><li>Desenvolvimento de APIs</li></ul>",
      "baseSalary": {"currency": "BRL", "value": {"minValue": 8000, "maxValue": 12000, "unitText": "MONTH"}}
    }
    </script></head><body><p>Conteúdo da página</p></body></html>
    """
    monkeypatch.setattr(importador, "_validar_url_publica", lambda url: None)
    monkeypatch.setattr(importador, "build_opener", lambda *_: OpenerFalso(html))

    vaga = importador.importar_vaga("https://example.com/jobs/1", 20000)

    assert vaga["titulo"] == "Engenheira de Software"
    assert vaga["descricao"] == "Desenvolver serviços de dados."
    assert vaga["empresa"] == "Empresa Exemplo"
    assert vaga["localizacao"] == "São Paulo, SP"
    assert vaga["modalidade"] == "Remoto"
    assert vaga["tipo_contratacao"] == "FULL_TIME"
    assert vaga["requisitos_obrigatorios"] == "Experiência com Python"
    assert vaga["competencias"] == "Python, SQL"
    assert vaga["responsabilidades"] == "- Desenvolvimento de APIs"
    assert vaga["faixa_salarial"] == "BRL 8000–12000 MONTH"
    assert vaga["url_origem"] == "https://example.com/jobs/1"


def test_importar_vaga_recusa_descricao_acima_do_limite_sem_truncar(monkeypatch):
    html = '<meta property="og:description" content="Descrição com mais caracteres">'
    monkeypatch.setattr(importador, "_validar_url_publica", lambda url: None)
    monkeypatch.setattr(importador, "build_opener", lambda *_: OpenerFalso(html))

    with pytest.raises(importador.ImportacaoVagaError, match="excede o limite"):
        importador.importar_vaga("https://example.com/jobs/1", 10)


def test_importar_vaga_separa_secoes_de_descricao_embutida(monkeypatch):
    html = """
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Desenvolvedor Python",
      "description": "<p>Empresa de tecnologia com equipe global.</p><p>Desenvolvedor Python para atuar em P&amp;D.</p><p>O que você vai fazer:</p><ul><li>Criar sistemas de automação.</li><li>Manter a infraestrutura de dados.</li></ul><p>Esperamos que você tenha:</p><ul><li>4 anos com Python e Django.</li><li>Desejável experiência com programação orientada a objetos.</li><li>Inglês avançado.</li></ul><p>Como tornamos seu trabalho (e sua vida) mais fácil:</p><ul><li>Modalidade 100% remota.</li><li>Horários flexíveis.</li></ul>"
    }
    </script>
    """
    monkeypatch.setattr(importador, "_validar_url_publica", lambda url: None)
    monkeypatch.setattr(importador, "build_opener", lambda *_: OpenerFalso(html))

    vaga = importador.importar_vaga("https://example.com/jobs/1", 20000)

    assert vaga["descricao"] == "Empresa de tecnologia com equipe global.\nDesenvolvedor Python para atuar em P&D."
    assert vaga["responsabilidades"] == "- Criar sistemas de automação.\n- Manter a infraestrutura de dados."
    assert vaga["requisitos_obrigatorios"] == "4 anos com Python e Django.\nInglês avançado."
    assert vaga["requisitos_desejaveis"] == "Desejável experiência com programação orientada a objetos."
    assert vaga["beneficios"] == "- Modalidade 100% remota.\n- Horários flexíveis."


def test_importar_vaga_separa_texto_plano_com_bullets_na_mesma_linha(monkeypatch):
    descricao = (
        "Contexto da empresa. Desenvolvedor Python. O que você vai fazer: "
        "- Criar sistemas de automação. - Manter a infraestrutura de dados. "
        "Esperamos que você tenha: - 4 anos com Python e Django. "
        "- Desejável experiência com orientação a objetos. - Inglês avançado. "
        "Como tornamos seu trabalho (e sua vida) mais fácil: "
        "- Modalidade 100% remota. - Horários flexíveis."
    )
    dados_json_ld = json.dumps({"@type": "JobPosting", "title": "Dev Python", "description": descricao})
    html = f'<script type="application/ld+json">{dados_json_ld}</script>'
    monkeypatch.setattr(importador, "_validar_url_publica", lambda url: None)
    monkeypatch.setattr(importador, "build_opener", lambda *_: OpenerFalso(html))

    vaga = importador.importar_vaga("https://example.com/jobs/1", 20000)

    assert vaga["descricao"] == "Contexto da empresa. Desenvolvedor Python."
    assert "Criar sistemas de automação." in vaga["responsabilidades"]
    assert "Manter a infraestrutura de dados." in vaga["responsabilidades"]
    assert vaga["requisitos_obrigatorios"] == "4 anos com Python e Django.\nInglês avançado."
    assert vaga["requisitos_desejaveis"] == "Desejável experiência com orientação a objetos."
    assert "Horários flexíveis." in vaga["beneficios"]


def test_importar_vaga_prioriza_job_posting_sobre_website_ou_organization(monkeypatch):
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@type": "WebSite",
      "name": "Portal de Empregos",
      "description": "Encontre empregos em todo o Brasil."
    }
    </script>
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Analista de Dados",
      "description": "Atuar na modelagem e análise de dados analíticos."
    }
    </script>
    </head><body></body></html>
    """
    monkeypatch.setattr(importador, "_validar_url_publica", lambda url: None)
    monkeypatch.setattr(importador, "build_opener", lambda *_: OpenerFalso(html))

    vaga = importador.importar_vaga("https://example.com/jobs/99", 20000)

    assert vaga["titulo"] == "Analista de Dados"
    assert vaga["descricao"] == "Atuar na modelagem e análise de dados analíticos."
