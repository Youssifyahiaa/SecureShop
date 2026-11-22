"""Integration tests for administrator session-risk protection."""

import json

from datetime import datetime, timezone
from hashlib import sha256

from flask import abort, session
from flask_login import login_user

from app.extensions import db
from app.models.user import User
from app.models.audit_log import AuditLog


TEST_USER_AGENT = "SecureShopTest/1.0"


def create_admin():

    admin = User(
        name="Risk Admin",
        email="risk-admin@example.com",
        password_hash="test-only-password-hash",
        confirmed_at=datetime.now(timezone.utc),
        role="admin"
    )

    db.session.add(admin)
    db.session.commit()

    return admin


def register_login_route(app):

    def test_login(user_id):

        user = db.session.get(User, user_id)

        if user is None:
            abort(404)

        login_user(user)
        session.permanent = True

        return "", 204

    if "test_risk_login" not in app.view_functions:
        app.add_url_rule(
            "/_test/risk-login/<int:user_id>",
            endpoint="test_risk_login",
            view_func=test_login,
            methods=["POST"]
        )


def login_as_admin(app, client):

    register_login_route(app)

    admin = create_admin()

    response = client.post(
        f"/_test/risk-login/{admin.id}",
        headers={"User-Agent": TEST_USER_AGENT}
    )

    assert response.status_code == 204

    return admin


def open_admin_dashboard(client):

    return client.get(
        "/admin/",
        headers={"User-Agent": TEST_USER_AGENT}
    )


def get_latest_audit():

    return db.session.execute(
        db.select(AuditLog).order_by(
            AuditLog.id.desc()
        )
    ).scalars().first()


# ---------------------------------------------
# Test 1: Normal administrator
# ---------------------------------------------

def test_normal_admin_session_is_allowed(app, client):

    login_as_admin(app, client)

    response = open_admin_dashboard(client)

    assert response.status_code == 200

    assert b"SecureShop Admin Dashboard" in response.data

    assert get_latest_audit() is None


# ---------------------------------------------
# Test 2: Medium-risk administrator
# ---------------------------------------------

def test_medium_risk_admin_is_denied_and_audited(app, client):

    login_as_admin(app, client)

    with client.session_transaction() as sess:
        sess["login_role"] = "customer"

    response = open_admin_dashboard(client)

    assert response.status_code == 403

    audit = get_latest_audit()

    assert audit is not None

    assert audit.event_type == (
        "session_risk_step_up_required"
    )

    details = json.loads(audit.details)

    assert details["score"] == 50
    assert "role_changed" in details["signals"]


# ---------------------------------------------
# Test 3: High-risk administrator
# ---------------------------------------------

def test_high_risk_admin_is_denied_and_audited(app, client):

    login_as_admin(app, client)

    different_ua_hash = sha256(
        b"DifferentBrowser/2.0"
    ).hexdigest()

    with client.session_transaction() as sess:
        sess["login_role"] = "customer"
        sess["login_ua_hash"] = different_ua_hash

    response = open_admin_dashboard(client)

    assert response.status_code == 403

    audit = get_latest_audit()

    assert audit is not None

    assert audit.event_type == (
        "session_risk_step_up_required"
    )

    details = json.loads(audit.details)

    assert details["score"] == 80

    assert "role_changed" in details["signals"]
    assert "user_agent_changed" in details["signals"]


# ---------------------------------------------
# Test 4: Critical-risk administrator
# ---------------------------------------------

def test_critical_risk_logs_out_admin(app, client):

    login_as_admin(app, client)

    different_ua_hash = sha256(
        b"DifferentBrowser/2.0"
    ).hexdigest()

    with client.session_transaction() as sess:
        sess["login_role"] = "customer"
        sess["login_ua_hash"] = different_ua_hash
        sess["login_ip"] = "198.51.100.25"
        sess["_fresh"] = False

    response = open_admin_dashboard(client)

    assert response.status_code == 403

    audit = get_latest_audit()

    assert audit is not None

    assert audit.event_type == "session_risk_logout"

    details = json.loads(audit.details)

    assert details["score"] == 100

    # Verify the administrator's session was terminated.
    with client.session_transaction() as sess:
        assert "_user_id" not in sess

    # The next request must require login again.
    response = open_admin_dashboard(client)

    assert response.status_code == 302


# ---------------------------------------------
# Test 5: Administrator request-burst detection
# ---------------------------------------------

def test_admin_request_burst_is_detected_by_decorator(app, client):

    login_as_admin(app, client)

    # First 30 requests should be allowed.
    for _ in range(30):
        response = open_admin_dashboard(client)
        assert response.status_code == 200

    # Introduce another risk signal before request 31.
    with client.session_transaction() as sess:
        sess["login_role"] = "customer"

    # Request 31 should detect both risk signals.
    response = open_admin_dashboard(client)

    assert response.status_code == 403

    audit = get_latest_audit()

    assert audit is not None
    assert audit.event_type == "session_risk_step_up_required"

    details = json.loads(audit.details)

    assert details["score"] == 80
    assert "request_burst" in details["signals"]
    assert "role_changed" in details["signals"]
# ---------------------------------------------
# Test 6: Request burst alone triggers step-up
# ---------------------------------------------

def test_admin_request_burst_alone_requires_step_up(app, client):

    login_as_admin(app, client)

    # First 30 requests should be allowed.
    for _ in range(30):
        response = open_admin_dashboard(client)
        assert response.status_code == 200

    # Request 31 should trigger additional verification.
    response = open_admin_dashboard(client)

    assert response.status_code == 403

    audit = get_latest_audit()

    assert audit is not None

    assert audit.event_type == (
        "session_risk_step_up_required"
    )

    details = json.loads(audit.details)

    assert details["score"] == 30
    assert "request_burst" in details["signals"]
    assert "role_changed" not in details["signals"]