"""Signed, time-limited tokens for email confirmation and password reset."""
from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

SALT = "email-confirm"
PURPOSE = "confirm_email"

RESET_SALT = "password-reset"
RESET_PURPOSE = "reset_password"


def _serializer(salt=SALT):
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def make_confirm_token(user_id):
    return _serializer().dumps({"uid": user_id, "purpose": PURPOSE})


def read_confirm_token(token):
    """Return the user id, or None if the token is invalid, expired or for another purpose."""
    try:
        data = _serializer().loads(token, max_age=current_app.config["CONFIRM_TOKEN_MAX_AGE"])
    except BadData:  # bad signature, expired, malformed
        return None
    if not isinstance(data, dict) or data.get("purpose") != PURPOSE:
        return None
    uid = data.get("uid")
    return uid if isinstance(uid, int) else None


def make_reset_token(user_id, nonce):
    return _serializer(RESET_SALT).dumps({"uid": user_id, "nonce": nonce, "purpose": RESET_PURPOSE})


def read_reset_token(token):
    """Return (user id, nonce), or None if the token is invalid, expired or for another purpose.

    The caller must still compare the nonce with the user's current reset_nonce.
    """
    try:
        data = _serializer(RESET_SALT).loads(token, max_age=current_app.config["RESET_TOKEN_MAX_AGE"])
    except BadData:  # bad signature (incl. other salt), expired, malformed
        return None
    if not isinstance(data, dict) or data.get("purpose") != RESET_PURPOSE:
        return None
    uid, nonce = data.get("uid"), data.get("nonce")
    if not isinstance(uid, int) or isinstance(uid, bool) or not isinstance(nonce, str) or not nonce:
        return None
    return uid, nonce
