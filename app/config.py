"""Application configuration.

All secrets come from environment variables (loaded from a local .env file
that is NEVER committed). See .env.example for the variable names.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # --- Core secrets ------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY")  # required; create_app refuses to start without it

    # --- Database ----------------------------------------------------------
    # Relative SQLite paths are created inside the instance/ folder (ignored by Git).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///secureshop.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Session & cookies -------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)  # set True when served over HTTPS
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.environ.get("SESSION_MINUTES", "30")))

    # --- CSRF --------------------------------------------------------------
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # --- Rate limiting -----------------------------------------------------
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # --- Request size (blocks oversized form/JSON bodies) -------------------
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB

    # --- Email (used for confirmation / reset links in Task 3) ---------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@secureshop.local")
    # When no mail server is configured, links go to the development log only.
    MAIL_DEV_LOG_ONLY = not MAIL_SERVER


# Settings used by the automated tests (in-memory DB, no CSRF/rate limits).
TEST_CONFIG = {
    "TESTING": True,
    "SECRET_KEY": "test-only-key-not-for-real-use",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "WTF_CSRF_ENABLED": False,
    "RATELIMIT_ENABLED": False,
}
