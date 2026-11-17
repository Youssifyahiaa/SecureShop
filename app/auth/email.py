"""Minimal mail helper. Without MAIL_SERVER, links go to the server log only."""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to, subject, body):
    """Return True only if a message was really handed to an SMTP server."""
    cfg = current_app.config
    if cfg.get("MAIL_DEV_LOG_ONLY") or not cfg.get("MAIL_SERVER"):
        current_app.logger.info("[DEV MAIL] to=%s subject=%s\n%s", to, subject, body)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = cfg["MAIL_DEFAULT_SENDER"], to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=10) as smtp:
            if cfg.get("MAIL_USE_TLS"):
                smtp.starttls()
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            smtp.send_message(msg)
    except Exception:
        current_app.logger.exception("Failed to send email")
        return False
    return True


def send_confirmation_email(user, link):
    return send_email(
        user.email,
        "Confirm your SecureShop account",
        f"Hello {user.name},\n\nConfirm your account: {link}\n\nIf you did not register, ignore this email.",
    )
