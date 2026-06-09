import os
import smtplib
from email.message import EmailMessage
from app.utils.logger import logger

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_USER") or os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_email_sync(to_email: str, subject: str, content: str) -> bool:
    """Synchronous email sending via smtplib. Called by Celery workers."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.error("SMTP credentials missing. Cannot send email.")
        return False

    message = EmailMessage()
    message["From"] = SMTP_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(content)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(message)
        logger.info(f"Successfully sent email to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}. Error: {e}")
        return False


async def send_email_async(to_email: str, subject: str, content: str) -> bool:
    return send_email_sync(to_email, subject, content)


def get_fallback_email(full_name: str) -> str:
    return f"""Hi {full_name},

Thanks for your inquiry. We have received your details and our team is currently reviewing them.

Someone will follow up soon with the next practical step.

We look forward to speaking with you soon.

Best regards,
The Team"""
