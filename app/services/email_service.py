import os
import smtplib
from email.message import EmailMessage
from app.utils.logger import logger

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
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
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
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


def get_fallback_email(full_name: str) -> str:
    return f"""Hi {full_name},

Thanks for your interest in going solar! We have received your inquiry and our team is currently reviewing your details. 

To help us prepare the best proposal for you, could you please let us know:
- Your approximate rooftop size
- Your average daytime electricity usage
- Your preferred installation timeline

We look forward to speaking with you soon and helping you save on your electricity bills.

Best regards,
The Solar Team"""
