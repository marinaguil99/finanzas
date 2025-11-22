# scripts/send_email.py
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(subject, content, to_email=None):
    """
    Envía email usando SendGrid.
    Env vars requeridas:
      - SENDGRID_API_KEY
      - SENDGRID_SENDER (email verificado en SendGrid)
    to_email: si no se pasa, usa ALERT_EMAIL env var.
    """
    sg_key = os.environ.get("SENDGRID_API_KEY")
    sender = os.environ.get("SENDGRID_SENDER")
    recipient = to_email or os.environ.get("ALERT_EMAIL")

    if not sg_key or not sender or not recipient:
        raise RuntimeError("Faltan variables de entorno SENDGRID_API_KEY / SENDGRID_SENDER / ALERT_EMAIL")

    message = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=subject,
        html_content=f"<pre>{content}</pre>"
    )

    sg = SendGridAPIClient(sg_key)
    response = sg.send(message)
    return response.status_code, response.body
