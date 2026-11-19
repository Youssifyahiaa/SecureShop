
"""Session risk scoring for SecureShop."""

from flask import has_request_context, session as flask_session


# Proposed risk weights.
RISK_WEIGHTS = {
    "non_fresh_session": 40,
    "non_permanent_session": 15,
    "missing_user_agent": 10,
    "missing_ip_address": 10,
}


def score_session_risk(user, request) -> int:
    """
    Calculate a session risk score between 0 and 100.

    This function is read-only. It does not modify sessions,
    invalidate accounts, or block requests.

    A score of 0 means no configured risk indicators were found.
    A score of 100 indicates an invalid or unbound session.
    """

    # A valid request context is required.
    if not has_request_context() or request is None:
        return 100

    # An unauthenticated user cannot have a trusted session.
    if user is None or not getattr(user, "is_authenticated", False):
        return 100

    # Verify that the current Flask-Login session belongs
    # to the supplied user, including their session version.
    expected_user_id = user.get_id()
    stored_user_id = flask_session.get("_user_id")

    if not expected_user_id or stored_user_id != expected_user_id:
        return 100

    risk_score = 0

    # Flask-Login can mark a session as non-fresh when
    # session protection detects a suspicious change.
    if flask_session.get("_fresh") is not True:
        risk_score += RISK_WEIGHTS["non_fresh_session"]

    # SecureShop makes authenticated sessions permanent.
    if not flask_session.permanent:
        risk_score += RISK_WEIGHTS["non_permanent_session"]

    # Missing browser information is a weak risk indicator.
    user_agent = request.user_agent.string or ""

    if not user_agent.strip():
        risk_score += RISK_WEIGHTS["missing_user_agent"]

    # Missing client address is another weak indicator.
    if not request.remote_addr:
        risk_score += RISK_WEIGHTS["missing_ip_address"]

    # Always keep the result between 0 and 100.
    return max(0, min(risk_score, 100))
