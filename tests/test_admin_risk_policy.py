"""Tests for SecureShop administrator risk decisions."""

import pytest

from app.admin.risk_policy import decide_admin_risk
from app.admin.session_risk import SessionRiskResult


# ---------------------------------------------
# 1. Risk score boundaries
# ---------------------------------------------

@pytest.mark.parametrize(
    "score, expected_action, expected_event",
    [
        (0, "allow", None),
        (29, "allow", None),
        (30, "deny", "session_risk_step_up_required"),
        (59, "deny", "session_risk_step_up_required"),
        (60, "deny", "session_risk_step_up_required"),
        (99, "deny", "session_risk_step_up_required"),
        (100, "logout", "session_risk_logout"),
    ]
)
def test_admin_risk_decisions(
    score,
    expected_action,
    expected_event
):

    risk = SessionRiskResult(
        score=score,
        signals=()
    )

    decision = decide_admin_risk(risk)

    assert decision.action == expected_action
    assert decision.audit_event == expected_event


# ---------------------------------------------
# 2. Low risk
# ---------------------------------------------

def test_low_risk_does_not_require_audit():

    risk = SessionRiskResult(
        score=10,
        signals=("missing_user_agent",)
    )

    decision = decide_admin_risk(risk)

    assert decision.action == "allow"
    assert decision.audit_event is None
    assert decision.audit_details is None


# ---------------------------------------------
# 3. Medium and high risk
# ---------------------------------------------

def test_medium_risk_records_security_signals():

    risk = SessionRiskResult(
        score=50,
        signals=("role_changed",)
    )

    decision = decide_admin_risk(risk)

    assert decision.action == "deny"

    assert decision.audit_details == {
        "score": 50,
        "signals": ["role_changed"]
    }


def test_high_risk_requires_additional_verification():

    risk = SessionRiskResult(
        score=80,
        signals=(
            "role_changed",
            "user_agent_changed"
        )
    )

    decision = decide_admin_risk(risk)

    assert decision.action == "deny"

    assert decision.audit_event == (
        "session_risk_step_up_required"
    )

    assert decision.audit_details["score"] == 80

    assert "role_changed" in (
        decision.audit_details["signals"]
    )


# ---------------------------------------------
# 4. Critical risk
# ---------------------------------------------

def test_critical_risk_requires_logout():

    risk = SessionRiskResult(
        score=100,
        signals=("invalid_session_binding",)
    )

    decision = decide_admin_risk(risk)

    assert decision.action == "logout"
    assert decision.audit_event == "session_risk_logout"

    assert decision.audit_details == {
        "score": 100,
        "signals": ["invalid_session_binding"]
    }


# ---------------------------------------------
# 5. Invalid scores
# ---------------------------------------------

@pytest.mark.parametrize(
    "invalid_score",
    [-1, 101, True, 5.5]
)
def test_invalid_risk_scores_are_rejected(
    invalid_score
):

    risk = SessionRiskResult(
        score=invalid_score,
        signals=()
    )

    with pytest.raises(ValueError):
        decide_admin_risk(risk)


# ---------------------------------------------
# 6. Invalid inputs
# ---------------------------------------------

@pytest.mark.parametrize(
    "invalid_input",
    [None, 50, "high"]
)
def test_invalid_risk_objects_are_rejected(
    invalid_input
):

    with pytest.raises(TypeError):
        decide_admin_risk(invalid_input)


# ---------------------------------------------
# 7. Deterministic decisions
# ---------------------------------------------

def test_same_risk_produces_same_decision():

    risk = SessionRiskResult(
        score=45,
        signals=("user_agent_changed",)
    )

    first = decide_admin_risk(risk)
    second = decide_admin_risk(risk)

    assert first == second