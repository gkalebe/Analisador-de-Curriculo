import httpx

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridError(Exception):
    pass


def enviar_email_sendgrid(destinatario: str, assunto: str, corpo: str, remetente: str, api_key: str) -> None:
    resposta = httpx.post(
        SENDGRID_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": destinatario}]}],
            "from": {"email": remetente},
            "subject": assunto,
            "content": [{"type": "text/plain", "value": corpo}],
        },
        timeout=10,
    )
    if resposta.status_code >= 400:
        raise SendGridError(f"SendGrid retornou {resposta.status_code}: {resposta.text}")
