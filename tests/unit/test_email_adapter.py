import smtplib
from unittest.mock import MagicMock, patch

from app.adapters.email.email_adapter import EmailAdapter
from app.core.config import Settings


def _adapter(**overrides) -> EmailAdapter:
    base = {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "smtp_from": "no-reply@analisador-curriculos.com",
        "smtp_use_tls": True,
        "frontend_login_url": "http://localhost:8000/login",
    }
    base.update(overrides)
    adapter = EmailAdapter()
    adapter.settings = Settings(**base)
    return adapter


def test_enviar_confirmacao_cadastro_modo_dev_nao_chama_smtp():
    adapter = _adapter(smtp_host="")

    with patch("app.adapters.email.email_adapter.smtplib.SMTP") as mock_smtp:
        adapter.enviar_confirmacao_cadastro("destino@example.com", "Gabriel")

    mock_smtp.assert_not_called()


def test_enviar_confirmacao_cadastro_com_smtp_host_envia_via_smtplib():
    adapter = _adapter(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="remetente@example.com",
        smtp_password="senha-app",
        smtp_use_tls=True,
    )

    with patch("app.adapters.email.email_adapter.smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instancia

        adapter.enviar_confirmacao_cadastro("destino@example.com", "Gabriel")

        mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
        instancia.starttls.assert_called_once()
        instancia.login.assert_called_once_with("remetente@example.com", "senha-app")
        instancia.send_message.assert_called_once()


def test_enviar_confirmacao_cadastro_nao_propaga_erro_de_conexao():
    adapter = _adapter(smtp_host="smtp.gmail.com")

    with patch("app.adapters.email.email_adapter.smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = TimeoutError("conexao recusada")

        adapter.enviar_confirmacao_cadastro("destino@example.com", "Gabriel")


def test_enviar_confirmacao_cadastro_nao_propaga_erro_de_autenticacao():
    adapter = _adapter(smtp_host="smtp.gmail.com", smtp_user="remetente@example.com", smtp_password="senha-errada")

    with patch("app.adapters.email.email_adapter.smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        instancia.login.side_effect = smtplib.SMTPAuthenticationError(535, b"autenticacao invalida")
        mock_smtp.return_value.__enter__.return_value = instancia

        adapter.enviar_confirmacao_cadastro("destino@example.com", "Gabriel")
