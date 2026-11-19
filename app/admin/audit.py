
"""Secure audit logging service."""

import ipaddress
import json
import re
from datetime import datetime, timezone

from flask import has_request_context, request
from sqlalchemy import insert

from app.extensions import db
from app.models.audit_log import AuditLog


MAX_DETAILS_BYTES = 2048

SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "token",
    "nonce",
    "secret",
    "cookie",
    "authorization",
    "csrf",
    "payment",
    "card",
    "cvv",
    "cvc",
    "iban",
    "bankaccount",
)


def _contains_sensitive_key(value):
    """Check nested dictionaries for sensitive field names."""

    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(
                r"[^a-z0-9]",
                "",
                str(key).lower()
            )

            if any(
                sensitive in normalized
                for sensitive in SENSITIVE_KEY_PARTS
            ):
                return True

            if _contains_sensitive_key(item):
                return True

    elif isinstance(value, list):
        return any(
            _contains_sensitive_key(item)
            for item in value
        )

    return False


def _get_ip_address():
    """Get and validate the direct client IP address."""

    if not has_request_context():
        return None

    address = request.remote_addr

    if not address:
        return None

    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return None


def log_event(
    event_type,
    user_id=None,
    details=None,
    *,
    actor_id=None
):
    """
    Record a security event using an independent transaction.

    Never commits or modifies db.session.
    """

    if not isinstance(event_type, str):
        raise ValueError("Invalid event type.")

    event_type = event_type.strip()

    if not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", event_type):
        raise ValueError("Invalid event type.")

    for field_name, value in (
        ("user_id", user_id),
        ("actor_id", actor_id),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(f"Invalid {field_name}.")

    details_json = None

    if details is not None:
        if not isinstance(details, dict):
            raise ValueError("Details must be a dictionary.")

        if _contains_sensitive_key(details):
            raise ValueError(
                "Sensitive information cannot be logged."
            )

        try:
            details_json = json.dumps(
                details,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False
            )
        except (TypeError, ValueError):
            raise ValueError("Details must contain valid JSON data.")

        if len(details_json.encode("utf-8")) > MAX_DETAILS_BYTES:
            raise ValueError("Audit details exceed 2 KB.")

    values = {
        "created_at": datetime.now(timezone.utc),
        "event_type": event_type,
        "user_id": user_id,
        "actor_id": actor_id,
        "ip_address": _get_ip_address(),
        "details": details_json,
    }

    # Independent transaction.
    # Never use db.session.commit() here.
    with db.engine.begin() as conn:
        result = conn.execute(
            insert(AuditLog.__table__).values(**values)
        )

        return result.inserted_primary_key[0]
