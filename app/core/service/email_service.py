import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


def enviar_email(destinatario: str, assunto: str, corpo: str, settings: Settings) -> None:
    if not settings.smtp_host:
        logger.info("E-mail (modo dev, não enviado): para=%s assunto=%s corpo=%s", destinatario, assunto, corpo)
        return

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = settings.smtp_from or settings.smtp_user
    mensagem["To"] = destinatario
    mensagem.set_content(corpo)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as servidor:
        if settings.smtp_use_tls:
            servidor.starttls()
        if settings.smtp_user:
            servidor.login(settings.smtp_user, settings.smtp_password)
        servidor.send_message(mensagem)


def enviar_email_recuperacao_senha(destinatario: str, token: str, settings: Settings) -> None:
    link = f"{settings.frontend_login_url}?token={token}"
    assunto = "Recuperação de senha - currículoIA"
    corpo = (
        "Você solicitou a recuperação de senha.\n\n"
        f"Acesse o link abaixo para definir uma nova senha (expira em {settings.password_reset_expire_minutes} minutos):\n"
        f"{link}\n\n"
        "Se você não solicitou isso, ignore este e-mail."
    )
    enviar_email(destinatario, assunto, corpo, settings)
