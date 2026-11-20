"""Administrator authorization and session-risk protection."""

from datetime import datetime, timezone
from functools import wraps

from flask import (
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for,
)

from flask_login import current_user, logout_user

from app.admin.audit import log_event
from app.admin.risk_policy import decide_admin_risk
from app.admin.session_risk import assess_session_risk


def admin_required(view):
    """Allow administrators with an acceptable session-risk score."""

    @wraps(view)
    def wrapped(*args, **kwargs):

        # 1. Require authentication.
        if not current_user.is_authenticated:
            return redirect(
                url_for("auth.login", next=request.url)
            )

        # 2. Require the administrator role.
        if current_user.role != "admin":
            abort(403)

        # 3. Calculate session risk.
        risk = assess_session_risk(
            current_user,
            request,
            dict(session),
            now=datetime.now(timezone.utc),

            # Request-burst tracking will be integrated
            # after Youssef provides the tracking mechanism.
            request_timestamps=()
        )

        # 4. Decide how to handle the request.
        decision = decide_admin_risk(risk)

        # 5. Allow low-risk sessions.
        if decision.action == "allow":
            return view(*args, **kwargs)

        # 6. Audit suspicious decisions.
        try:
            log_event(
                decision.audit_event,
                user_id=current_user.id,
                actor_id=current_user.id,
                details=decision.audit_details
            )

        except Exception:
            # Never permit a risky request simply because
            # writing its audit record failed.
            current_app.logger.exception(
                "Failed to record admin session-risk event"
            )

        # 7. Terminate critical-risk sessions.
        if decision.action == "logout":
            logout_user()
            session.clear()

        # 8. Deny access when additional verification is required.
        abort(403)

    return wrapped