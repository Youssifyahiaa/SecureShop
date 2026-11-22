"""Minimal mail helper.

Without MAIL_SERVER, messages go to a private development outbox instead of SMTP:
an in-memory list (app.extensions["dev_outbox"]) under TESTING, otherwise one .txt
file per message in instance/dev_mail/. The log only says that a message was saved,
never its body, link or code.
"""
import os
import secrets
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from flask import current_app


def _mask_email(address):
    """'jane@example.com' -> 'j***@example.com' (safe to put in a log line)."""
    local, sep, domain = (address or "").partition("@")
    if not sep:
        return "***"
    return f"{local[:1]}***@{domain}"


def _save_dev_mail(to, subject, body):
    app = current_app._get_current_object()
    if app.config.get("TESTING"):
        app.extensions.setdefault("dev_outbox", []).append(
            {"to": to, "subject": subject, "body": body}
        )
        return
    folder = os.path.join(app.instance_path, "dev_mail")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = os.path.join(folder, f"{stamp}-{secrets.token_hex(4)}.txt")
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(f"To: {to}\nSubject: {subject}\n\n{body}\n")


def send_email(to, subject, body):
    """Return True only if a message was really handed to an SMTP server."""
    cfg = current_app.config
    if cfg.get("MAIL_DEV_LOG_ONLY") or not cfg.get("MAIL_SERVER"):
        _save_dev_mail(to, subject, body)
        current_app.logger.info("[DEV MAIL] saved for %s", _mask_email(to))
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


def send_password_reset_email(user, link):
    return send_email(
        user.email,
        "Reset your SecureShop password",
        f"Hello {user.name},\n\nReset your password (link valid for 30 minutes, single use): {link}\n\n"
        "If you did not ask for this, ignore this email; your password will not change.",
    )
