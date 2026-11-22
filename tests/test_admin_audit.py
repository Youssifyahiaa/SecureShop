
from datetime import datetime, timedelta, timezone

from flask import abort
from flask_login import login_user

from app.extensions import db
from app.models.user import User
from app.models.audit_log import AuditLog


def create_user(name, email, role="customer"):

    user = User(
        name=name,
        email=email.lower(),
        password_hash="test-only-password-hash",
        role=role,
        confirmed_at=datetime.now(timezone.utc)
    )

    db.session.add(user)
    db.session.commit()

    return user


def register_login_route(app):

    def test_login(user_id):

        user = db.session.get(User, user_id)

        if user is None:
            abort(404)

        login_user(user)

        return "", 204

    if "test_audit_login" not in app.view_functions:
        app.add_url_rule(
            "/_test/audit-login/<int:user_id>",
            endpoint="test_audit_login",
            view_func=test_login,
            methods=["POST"]
        )


def login_as(client, user):

    response = client.post(
        f"/_test/audit-login/{user.id}"
    )

    assert response.status_code == 204


def create_audit_log(
    event_type,
    ip_address="127.0.0.1",
    details=None,
    minutes_ago=0
):

    log = AuditLog(
        created_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=minutes_ago)
        ),
        event_type=event_type,
        ip_address=ip_address,
        details=details
    )

    db.session.add(log)
    db.session.commit()

    return log


def test_visitor_cannot_view_audit_logs(app, client):

    register_login_route(app)

    response = client.get("/admin/audit-logs")

    assert response.status_code == 302


def test_customer_cannot_view_audit_logs(app, client):

    register_login_route(app)

    customer = create_user(
        "Customer",
        "audit-customer@test.com"
    )

    login_as(client, customer)

    response = client.get("/admin/audit-logs")

    assert response.status_code == 403


def test_admin_can_view_audit_logs(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "audit-admin@test.com",
        role="admin"
    )

    create_audit_log(
        "login_failed",
        "192.0.2.10",
        '{"reason":"invalid_credentials"}'
    )

    login_as(client, admin)

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200
    assert b"Security Audit History" in response.data
    assert b"login_failed" in response.data
    assert b"192.0.2.10" in response.data


def test_empty_audit_logs_message(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "empty-audit@test.com",
        role="admin"
    )

    login_as(client, admin)

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200
    assert b"No audit records found." in response.data


def test_search_audit_logs_by_event_type(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "search-event@test.com",
        role="admin"
    )

    create_audit_log("password_reset")
    create_audit_log("login_failed")

    login_as(client, admin)

    response = client.get(
        "/admin/audit-logs?q=password_reset"
    )

    assert response.status_code == 200
    assert b"password_reset" in response.data
    assert b"login_failed" not in response.data


def test_search_audit_logs_by_ip(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "search-ip@test.com",
        role="admin"
    )

    create_audit_log(
        "login_failed",
        "192.0.2.20"
    )

    create_audit_log(
        "account_locked",
        "192.0.2.30"
    )

    login_as(client, admin)

    response = client.get(
        "/admin/audit-logs?q=192.0.2.20"
    )

    assert response.status_code == 200
    assert b"192.0.2.20" in response.data
    assert b"192.0.2.30" not in response.data


def test_audit_logs_pagination_and_order(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "pagination-audit@test.com",
        role="admin"
    )

    for i in range(26):

        create_audit_log(
            event_type=f"event_{i}",
            minutes_ago=i
        )

    login_as(client, admin)

    # First page: newest 25 records.
    response = client.get("/admin/audit-logs?page=1")

    assert response.status_code == 200
    assert b"Page 1 of 2" in response.data
    assert b"event_0" in response.data
    assert b"event_24" in response.data
    assert b"event_25" not in response.data

    # Verify newest events appear before older events.
    assert (
        response.data.index(b"event_0")
        < response.data.index(b"event_1")
    )

    # Second page: remaining record.
    response = client.get("/admin/audit-logs?page=2")

    assert response.status_code == 200
    assert b"Page 2 of 2" in response.data
    assert b"event_25" in response.data
    assert b"event_0" not in response.data

def test_audit_log_details_escape_xss(app, client):
    register_login_route(app)

    admin = create_user(
        "Audit Admin",
        "xss-audit@test.com",
        role="admin"
    )

    malicious_details = "<script>alert(1)</script>"

    create_audit_log(
        event_type="security_test",
        details=malicious_details
    )

    login_as(client, admin)

    response = client.get("/admin/audit-logs")

    assert response.status_code == 200

    # Audit details must be rendered as harmless text.
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data

    # No raw executable script should be present.
    assert b"<script>alert(1)</script>" not in response.data
