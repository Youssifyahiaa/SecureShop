"""Security risk decisions for SecureShop administrators."""

from dataclasses import dataclass

from app.admin.session_risk import SessionRiskResult


@dataclass(frozen=True)
class AdminRiskDecision:
    """Result of an administrator security decision."""

    action: str
    audit_event: str | None
    audit_details: dict | None


def decide_admin_risk(
    risk: SessionRiskResult
) -> AdminRiskDecision:
    """
    Decide how an administrator request should be handled.

    Actions:
        allow  - Continue normally.
        deny   - Require additional authentication.
        logout - Terminate the suspicious session.

    This function does not modify the session or database.
    """

    if not isinstance(risk, SessionRiskResult):
        raise TypeError("Expected SessionRiskResult.")

    score = risk.score

    if (
        isinstance(score, bool)
        or not isinstance(score, int)
        or not 0 <= score <= 100
    ):
        raise ValueError("Risk score must be between 0 and 100.")

    # Critical risk: session termination required.
    if score == 100:

        return AdminRiskDecision(
            action="logout",
            audit_event="session_risk_logout",
            audit_details={
                "score": score,
                "signals": list(risk.signals),
            }
        )

    # Medium/high risk: deny until step-up auth is available.
    if score >= 30:

        return AdminRiskDecision(
            action="deny",
            audit_event="session_risk_step_up_required",
            audit_details={
                "score": score,
                "signals": list(risk.signals),
            }
        )

    # Low risk: allow the request.
    return AdminRiskDecision(
        action="allow",
        audit_event=None,
        audit_details=None
    )