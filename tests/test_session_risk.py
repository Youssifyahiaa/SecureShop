"""Tests for SecureShop session risk scoring."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace

import pytest

from app.admin.session_risk import (
    assess_session_risk,
    score_session_risk,
)


NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


class TestUser:
    """A simple authenticated user for risk testing."""

    __test__ = False

    is_authenticated = True
    role = "admin"

    def get_id(self):
        return "7:0"


def make_request(
    user_agent="TestBrowser/1.0",
    ip="192.0.2.10"
):
    """Create request information for testing."""

    return SimpleNamespace(
        user_agent=SimpleNamespace(string=user_agent),
        remote_addr=ip
    )


def make_session(**changes):
    """Create a valid session with login baseline information."""

    ua_hash = sha256(
        b"TestBrowser/1.0"
    ).hexdigest()

    data = {
        "_user_id": "7:0",
        "_fresh": True,
        "_permanent": True,
        "login_ua_hash": ua_hash,
        "login_ip": "192.0.2.10",
        "login_role": "admin",
        "login_at": NOW.isoformat(),
    }

    data.update(changes)

    return data


def calculate(
    user=None,
    request=None,
    session_data=None,
    request_timestamps=()
):
    """Run the risk assessment with standard test values."""

    return assess_session_risk(
        user if user is not None else TestUser(),
        request if request is not None else make_request(),
        session_data if session_data is not None else make_session(),
        now=NOW,
        request_timestamps=request_timestamps
    )


# -------------------------------------------------
# 1. Normal session
# -------------------------------------------------

def test_normal_session_has_zero_risk():

    result = calculate()

    assert result.score == 0
    assert result.level == "low"
    assert result.signals == ()


# -------------------------------------------------
# 2. Invalid sessions
# -------------------------------------------------

def test_unauthenticated_user_has_maximum_risk():

    user = TestUser()
    user.is_authenticated = False

    result = assess_session_risk(
        user,
        make_request(),
        make_session(),
        now=NOW
    )

    assert result.score == 100
    assert result.level == "critical"


def test_mismatched_session_user_has_maximum_risk():

    result = calculate(
        session_data=make_session(
            _user_id="999:0"
        )
    )

    assert result.score == 100
    assert "invalid_session_binding" in result.signals


def test_missing_request_has_maximum_risk():

    result = assess_session_risk(
        TestUser(),
        None,
        make_session(),
        now=NOW
    )

    assert result.score == 100


def test_missing_session_has_maximum_risk():

    result = assess_session_risk(
        TestUser(),
        make_request(),
        None,
        now=NOW
    )

    assert result.score == 100


# -------------------------------------------------
# 3. Session freshness
# -------------------------------------------------

def test_non_fresh_session_adds_10_points():

    result = calculate(
        session_data=make_session(_fresh=False)
    )

    assert result.score == 10
    assert "non_fresh_session" in result.signals


def test_non_permanent_session_adds_10_points():

    result = calculate(
        session_data=make_session(_permanent=False)
    )

    assert result.score == 10
    assert "non_permanent_session" in result.signals


# -------------------------------------------------
# 4. Browser information
# -------------------------------------------------

def test_missing_user_agent_adds_10_points():

    result = calculate(
        request=make_request(user_agent="")
    )

    assert result.score == 10
    assert "missing_user_agent" in result.signals


def test_changed_user_agent_adds_30_points():

    result = calculate(
        request=make_request(
            user_agent="DifferentBrowser/2.0"
        )
    )

    assert result.score == 30
    assert result.level == "medium"
    assert "user_agent_changed" in result.signals


# -------------------------------------------------
# 5. IP address
# -------------------------------------------------

def test_missing_ip_adds_10_points():

    result = calculate(
        request=make_request(ip="")
    )

    assert result.score == 10
    assert "missing_ip_address" in result.signals


def test_changed_ip_adds_15_points():

    result = calculate(
        request=make_request(
            ip="198.51.100.25"
        )
    )

    assert result.score == 15
    assert result.level == "low"
    assert "ip_address_changed" in result.signals


# -------------------------------------------------
# 6. Account role changes
# -------------------------------------------------

def test_changed_role_adds_50_points():

    result = calculate(
        session_data=make_session(
            login_role="customer"
        )
    )

    assert result.score == 50
    assert result.level == "medium"
    assert "role_changed" in result.signals


# -------------------------------------------------
# 7. Request burst detection
# -------------------------------------------------

def test_30_requests_do_not_trigger_burst():

    timestamps = [
        NOW - timedelta(seconds=5)
        for _ in range(30)
    ]

    result = calculate(
        request_timestamps=timestamps
    )

    assert result.score == 0


def test_31_requests_trigger_burst():

    timestamps = [
        NOW - timedelta(seconds=5)
        for _ in range(31)
    ]

    result = calculate(
        request_timestamps=timestamps
    )

    assert result.score == 30
    assert result.level == "medium"
    assert "request_burst" in result.signals


def test_old_requests_are_ignored():

    timestamps = [
        NOW - timedelta(minutes=5)
        for _ in range(40)
    ]

    result = calculate(
        request_timestamps=timestamps
    )

    assert result.score == 0


def test_future_requests_are_ignored():

    timestamps = [
        NOW + timedelta(seconds=5)
        for _ in range(40)
    ]

    result = calculate(
        request_timestamps=timestamps
    )

    assert result.score == 0


def test_iso_timestamps_are_supported():

    timestamps = [
        (NOW - timedelta(seconds=5)).isoformat()
        for _ in range(31)
    ]

    result = calculate(
        request_timestamps=timestamps
    )

    assert result.score == 30
    assert result.level == "medium"
    assert "request_burst" in result.signals


# -------------------------------------------------
# 8. Combined risks and maximum score
# -------------------------------------------------

def test_combined_risks_produce_high_level():

    result = calculate(
        request=make_request(
            user_agent="DifferentBrowser/2.0"
        ),
        session_data=make_session(
            login_role="customer"
        )
    )

    assert result.score == 80
    assert result.level == "high"


def test_score_never_exceeds_100():

    timestamps = [
        NOW - timedelta(seconds=5)
        for _ in range(31)
    ]

    result = calculate(
        request=make_request(
            user_agent="DifferentBrowser/2.0",
            ip="198.51.100.25"
        ),
        session_data=make_session(
            login_role="customer"
        ),
        request_timestamps=timestamps
    )

    assert result.score == 100
    assert result.level == "critical"


# -------------------------------------------------
# 9. Numeric scoring interface
# -------------------------------------------------

def test_score_function_returns_integer():

    score = score_session_risk(
        TestUser(),
        make_request(
            user_agent="DifferentBrowser/2.0"
        ),
        make_session(),
        now=NOW
    )

    assert score == 30
    assert isinstance(score, int)


# -------------------------------------------------
# 10. Pure function behavior
# -------------------------------------------------

def test_risk_assessment_does_not_modify_session():

    session_data = make_session()

    original = session_data.copy()

    calculate(session_data=session_data)

    assert session_data == original


def test_invalid_now_is_rejected():

    with pytest.raises(ValueError):

        assess_session_risk(
            TestUser(),
            make_request(),
            make_session(),
            now=datetime(2026, 11, 20)
        )