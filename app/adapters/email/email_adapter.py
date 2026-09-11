import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Isola o envio de e-mail transacional. Provedor (SendGrid/Resend/SMTP) ainda não foi
    definido pelo time (ver Plano de Ação, Seção 4 "Próximos Passos") — por enquanto, na
    ausência de SMTP_HOST configurado, o e-mail é registrado em log para permitir
    desenvolvimento e testes locais sem depender de um provedor externo.
    """

    def __init__(self):
        self.settings = get_settings()

    def enviar_confirmacao_cadastro(self, destinatario: str, nome: str) -> None:
        assunto = "Confirme seu cadastro — Analisador de Currículos"
        corpo = (
            f"Olá, {nome}!\n\n"
            "Seu cadastro no Analisador de Currículos foi realizado com sucesso.\n"
            f"Você já pode fazer login em {self.settings.frontend_login_url}.\n"
        )
        self._enviar(destinatario, assunto, corpo)

    def _enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        if not self.settings.smtp_host:
            logger.info("E-mail (modo dev, sem SMTP configurado) para %s | Assunto: %s\n%s", destinatario, assunto, corpo)
            return

        mensagem = EmailMessage()
        mensagem["Subject"] = assunto
        mensagem["From"] = self.settings.smtp_from
        mensagem["To"] = destinatario
        mensagem.set_content(corpo)

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                if self.settings.smtp_use_tls:
                    smtp.starttls()
                if self.settings.smtp_user:
                    smtp.login(self.settings.smtp_user, self.settings.smtp_password)
                smtp.send_message(mensagem)
        except (OSError, smtplib.SMTPException):
            logger.exception("Falha ao enviar e-mail para %s", destinatario)
