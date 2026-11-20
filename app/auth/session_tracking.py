"""Per-session request window counter for authenticated users.

Stores exactly two session keys: req_window_start (Unix seconds) and req_count.
"""
import time

from flask import request, session
from flask_login import current_user

from . import bp

WINDOW_SECONDS = 60
MAX_COUNT = 10000
COUNTER_KEYS = ("req_window_start", "req_count")


def clear_request_counter():
    for key in COUNTER_KEYS:
        session.pop(key, None)


def _is_static(endpoint):
    return endpoint is not None and (endpoint == "static" or endpoint.endswith(".static"))


@bp.before_app_request
def track_request_window():
    if _is_static(request.endpoint):
        return
    if not current_user.is_authenticated:
        # Covers sessions logged out or invalidated by a password reset elsewhere.
        clear_request_counter()
        return
    now = int(time.time())
    if "req_window_start" not in session or now - session["req_window_start"] >= WINDOW_SECONDS:
        session["req_window_start"] = now
        session["req_count"] = 1
    else:
        session["req_count"] = min(session["req_count"] + 1, MAX_COUNT)
