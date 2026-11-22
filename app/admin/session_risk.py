"""Session risk scoring for SecureShop."""

import hashlib
import hmac

from dataclasses import dataclass
from datetime import datetime, timedelta


RISK_WEIGHTS = {
    "non_fresh_session": 10,
    "non_permanent_session": 10,
    "missing_user_agent": 10,
    "missing_ip_address": 10,
    "user_agent_changed": 30,
    "ip_address_changed": 15,
    "request_burst": 30,
    "role_changed": 50,
}


@dataclass(frozen=True)
class SessionRiskResult:
    score: int
    signals: tuple[str, ...]

    @property
    def level(self):
        if self.score == 100:
            return "critical"

        if self.score >= 60:
            return "high"

        if self.score >= 30:
            return "medium"

        return "low"


def _parse_timestamp(value):
    """Convert a timestamp into a timezone-aware datetime."""

    if isinstance(value, datetime):
        result = value

    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None

    else:
        return None

    if result.tzinfo is None:
        return None

    return result


def assess_session_risk(
    user,
    request,
    session_data,
    *,
    now,
    request_timestamps=()
):
    """
    Calculate session risk without changing application state.

    Inputs:
        user: Current database user.
        request: Current HTTP request.
        session_data: Snapshot of Flask session values.
        now: Current timezone-aware datetime.
        request_timestamps: Recent request times.

    Returns:
        SessionRiskResult containing score and triggered signals.

    This function does not:
        - Modify sessions
        - Log out users
        - Write audit records
        - Commit database transactions
        - Read the system clock
    """

    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError(
            "now must be a timezone-aware datetime."
        )

    # Invalid user or request.
    if user is None or request is None:
        return SessionRiskResult(
            100,
            ("invalid_session_binding",)
        )

    if not getattr(user, "is_authenticated", False):
        return SessionRiskResult(
            100,
            ("invalid_session_binding",)
        )

    if session_data is None:
        return SessionRiskResult(
            100,
            ("invalid_session_binding",)
        )

    get_id = getattr(user, "get_id", None)

    if not callable(get_id):
        return SessionRiskResult(
            100,
            ("invalid_session_binding",)
        )

    expected_id = get_id()
    stored_id = session_data.get("_user_id")

    if not expected_id or stored_id != expected_id:
        return SessionRiskResult(
            100,
            ("invalid_session_binding",)
        )

    score = 0
    signals = []

    def add_risk(signal):
        nonlocal score

        score += RISK_WEIGHTS[signal]
        signals.append(signal)

    # 1. Session freshness.
    if session_data.get("_fresh") is not True:
        add_risk("non_fresh_session")

    # 2. Session permanence.
    if session_data.get("_permanent") is not True:
        add_risk("non_permanent_session")

    # 3. User-Agent checks.
    current_ua = request.user_agent.string or ""

    if not current_ua.strip():
        add_risk("missing_user_agent")

    login_ua_hash = session_data.get("login_ua_hash")

    if login_ua_hash and current_ua.strip():

        current_ua_hash = hashlib.sha256(
            current_ua.encode("utf-8")
        ).hexdigest()

        if not hmac.compare_digest(
            current_ua_hash,
            login_ua_hash
        ):
            add_risk("user_agent_changed")

    # 4. IP address checks.
    current_ip = request.remote_addr

    if not current_ip:
        add_risk("missing_ip_address")

    login_ip = session_data.get("login_ip")

    if login_ip and current_ip and login_ip != current_ip:
        add_risk("ip_address_changed")

    # 5. Role changes.
    login_role = session_data.get("login_role")

    if (
        login_role is not None
        and login_role != getattr(user, "role", None)
    ):
        add_risk("role_changed")

    # 6. Request burst detection.
    window_start = now - timedelta(seconds=60)

    recent_requests = 0

    for value in request_timestamps:

        timestamp = _parse_timestamp(value)

        if timestamp is None:
            continue

        if window_start <= timestamp <= now:
            recent_requests += 1

    if recent_requests > 30:
        add_risk("request_burst")

    # 7. Cap risk score at 100.
    return SessionRiskResult(
        score=min(score, 100),
        signals=tuple(signals)
    )


def score_session_risk(
    user,
    request,
    session_data,
    *,
    now,
    request_timestamps=()
):
    """Return only the numeric risk score."""

    result = assess_session_risk(
        user,
        request,
        session_data,
        now=now,
        request_timestamps=request_timestamps
    )

    return result.score