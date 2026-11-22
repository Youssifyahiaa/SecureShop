
"""Signed, time-limited newsletter confirmation tokens.

Owner: Ali
"""

from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from .forms import normalize_email


NEWSLETTER_SALT = "newsletter-confirm-v1"
NEWSLETTER_PURPOSE = "newsletter_email_confirmation"
DEFAULT_MAX_AGE = 24 * 60 * 60  # 24 hours


def _serializer():
    """Use a separate signing namespace from account tokens."""
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt=NEWSLETTER_SALT,
    )


def make_newsletter_confirm_token(email: str) -> str:
    """Create a signed confirmation token for an email address."""
    normalized_email = normalize_email(email)

    return _serializer().dumps({
        "email": normalized_email,
        "purpose": NEWSLETTER_PURPOSE,
    })


def read_newsletter_confirm_token(token: str) -> str | None:
    """Return the confirmed email, or None for an invalid token."""
    try:
        data = _serializer().loads(
            token,
            max_age=current_app.config.get(
                "NEWSLETTER_CONFIRM_TOKEN_MAX_AGE",
                DEFAULT_MAX_AGE,
            ),
        )
    except BadData:
        return None

    if not isinstance(data, dict):
        return None

    if data.get("purpose") != NEWSLETTER_PURPOSE:
        return None

    email = data.get("email")

    if not isinstance(email, str):
        return None

    if (
        not email
        or len(email) > 255
        or normalize_email(email) != email
    ):
        return None

    return email
