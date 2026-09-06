import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


def send_email(to_email: str, subject: str, body: str) -> None:
    """Kirim email plain text via SMTP.
    Kalau env SMTP belum diisi, fallback print ke console
    (biar project baru tetap bisa jalan dev tanpa nunggu setup SMTP)."""
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[EMAIL FALLBACK] To: {to_email}\nSubject: {subject}\n\n{body}")
        return

    message = MIMEMultipart()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, to_email, message.as_string())


def send_otp_email(to_email: str, otp_code: str) -> None:
    subject = "Your Password Reset Code"
    body = (
        f"You requested a password reset.\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {OTP_EXPIRE_MINUTES if False else os.getenv('OTP_EXPIRE_MINUTES', 10)} minutes.\n"
        f"If you didn't request this, you can ignore this email."
    )
    send_email(to_email, subject, body)