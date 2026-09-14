import httpx
import pytest

from app.adapters.email.sendgrid_client import SendGridError, enviar_email_sendgrid


def test_enviar_email_sendgrid_chama_api_com_payload_correto(monkeypatch):
    capturado = {}

    def fake_post(url, headers, json, timeout):
        capturado["url"] = url
        capturado["headers"] = headers
        capturado["json"] = json
        capturado["timeout"] = timeout
        return httpx.Response(202, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.adapters.email.sendgrid_client.httpx.post", fake_post)

    enviar_email_sendgrid("destino@example.com", "Assunto", "Corpo", "remetente@example.com", "chave-api")

    assert capturado["url"] == "https://api.sendgrid.com/v3/mail/send"
    assert capturado["headers"]["Authorization"] == "Bearer chave-api"
    assert capturado["json"]["personalizations"] == [{"to": [{"email": "destino@example.com"}]}]
    assert capturado["json"]["from"] == {"email": "remetente@example.com"}
    assert capturado["json"]["subject"] == "Assunto"
    assert capturado["json"]["content"] == [{"type": "text/plain", "value": "Corpo"}]
    assert capturado["timeout"] == 10


def test_enviar_email_sendgrid_levanta_erro_em_resposta_de_falha(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return httpx.Response(401, text="chave invalida", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.adapters.email.sendgrid_client.httpx.post", fake_post)

    with pytest.raises(SendGridError):
        enviar_email_sendgrid("destino@example.com", "Assunto", "Corpo", "remetente@example.com", "chave-invalida")
