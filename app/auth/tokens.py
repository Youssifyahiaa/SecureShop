"""Signed, time-limited email confirmation tokens."""
from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

SALT = "email-confirm"
PURPOSE = "confirm_email"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT)


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
