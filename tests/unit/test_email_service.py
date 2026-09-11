from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.core.service.email_service import enviar_email, enviar_email_recuperacao_senha


def _settings(**overrides) -> Settings:
    base = {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "smtp_from": "",
        "smtp_use_tls": True,
        "frontend_login_url": "http://localhost:8000/login",
        "password_reset_expire_minutes": 30,
    }
    base.update(overrides)
    return Settings(**base)


def test_enviar_email_modo_dev_nao_chama_smtp(caplog):
    settings = _settings(smtp_host="")

    with patch("app.core.service.email_service.smtplib.SMTP") as mock_smtp:
        enviar_email("destino@example.com", "Assunto", "Corpo", settings)

    mock_smtp.assert_not_called()


def test_enviar_email_com_smtp_host_envia_via_smtplib():
    settings = _settings(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="remetente@example.com",
        smtp_password="senha-app",
        smtp_from="remetente@example.com",
        smtp_use_tls=True,
    )

    with patch("app.core.service.email_service.smtplib.SMTP") as mock_smtp:
        instancia = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instancia

        enviar_email("destino@example.com", "Assunto", "Corpo", settings)

        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        instancia.starttls.assert_called_once()
        instancia.login.assert_called_once_with("remetente@example.com", "senha-app")
        instancia.send_message.assert_called_once()


def test_enviar_email_recuperacao_senha_monta_link_com_token():
    settings = _settings(smtp_host="")

    with patch("app.core.service.email_service.enviar_email") as mock_enviar:
        enviar_email_recuperacao_senha("destino@example.com", "token-123", settings)

        assert mock_enviar.call_count == 1
        destinatario, assunto, corpo, settings_recebido = mock_enviar.call_args[0]
        assert destinatario == "destino@example.com"
        assert "token-123" in corpo
        assert settings_recebido is settings
