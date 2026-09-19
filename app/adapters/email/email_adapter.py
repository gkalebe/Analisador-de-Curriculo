import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.adapters.email.sendgrid_client import SendGridError, enviar_email_sendgrid
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Isola o envio de e-mail transacional, com 3 níveis de fallback, nesta ordem:

    1. SendGrid (API HTTPS, `sendgrid_client.py`), se `SENDGRID_API_KEY` estiver configurada.
       Preferido em produção (ex.: Render): é uma requisição HTTPS simples, sem handshake SMTP
       (que muitos provedores de nuvem bloqueiam/atrasam em portas 25/465/587) e sem depender
       de credenciais de um provedor de e-mail pessoal (Gmail, etc.).
    2. SMTP puro (`smtplib`), se `SMTP_HOST` estiver configurado e o SendGrid não estiver
       (ou falhar). Mantido para desenvolvimento/homologação sem conta SendGrid.
    3. Log local, se nenhum dos dois estiver configurado — permite rodar localmente sem
       depender de um provedor externo.

    Falha de envio (em qualquer nível) nunca propaga para o chamador — só é logada — porque
    o cadastro/recuperação de senha não deve falhar por causa de um problema no provedor de
    e-mail; ver `background_tasks.add_task(auth_service.email_adapter.enviar_confirmacao_cadastro, ...)`
    em `auth_router.py`, que já agenda esse envio fora do caminho síncrono da resposta HTTP.
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
        if self.settings.sendgrid_api_key:
            try:
                enviar_email_sendgrid(
                    destinatario=destinatario,
                    assunto=assunto,
                    corpo=corpo,
                    remetente=self.settings.smtp_from or "no-reply@analisador-curriculos.com",
                    api_key=self.settings.sendgrid_api_key,
                )
                return
            except (httpx.HTTPError, SendGridError):
                logger.exception("Falha ao enviar e-mail para %s via SendGrid; tentando SMTP.", destinatario)

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
