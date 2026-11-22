import json
from app.models.audit_log import AuditLog
from flask import abort
from flask_login import login_user
from app.extensions import db
from app.models.user import User


def create_user(name, email, role="customer", confirmed=True):

    from datetime import datetime, timezone

    user = User(
        name=name,
        email=email,
        password_hash="test-only-secret-hash",
        role=role,
        confirmed_at=(
            datetime.now(timezone.utc)
            if confirmed else None
        )
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

    if "test_admin_users_login" not in app.view_functions:
        app.add_url_rule(
            "/_test/admin-users-login/<int:user_id>",
            endpoint="test_admin_users_login",
            view_func=test_login,
            methods=["POST"]
        )


def login_as(client, user):

    response = client.post(
        f"/_test/admin-users-login/{user.id}"
    )

    assert response.status_code == 204


def test_visitor_cannot_view_users(app, client):

    register_login_route(app)

    response = client.get("/admin/users")

    assert response.status_code == 302


def test_customer_cannot_view_users(app, client):

    register_login_route(app)

    customer = create_user(
        "Customer",
        "customer-users@test.com"
    )

    login_as(client, customer)

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_admin_can_view_users(app, client):

    register_login_route(app)

    admin = create_user(
        "Admin",
        "admin-users@test.com",
        role="admin"
    )

    customer = create_user(
        "Customer",
        "customer-list@test.com"
    )

    login_as(client, admin)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"User Management" in response.data
    assert b"Customer" in response.data
    assert b"customer-list@test.com" in response.data


def test_user_search_by_name(app, client):

    register_login_route(app)

    admin = create_user(
        "Search Admin",
        "search-admin@test.com",
        role="admin"
    )

    create_user(
        "Alice Example",
        "alice@test.com"
    )

    create_user(
        "Bob Example",
        "bob@test.com"
    )

    login_as(client, admin)

    response = client.get(
        "/admin/users?q=Alice"
    )

    assert response.status_code == 200
    assert b"Alice Example" in response.data
    assert b"Bob Example" not in response.data


def test_user_search_by_email(app, client):

    register_login_route(app)

    admin = create_user(
        "Search Admin",
        "search-email-admin@test.com",
        role="admin"
    )

    create_user(
        "Alice",
        "alice-search@test.com"
    )

    create_user(
        "Bob",
        "bob-search@test.com"
    )

    login_as(client, admin)

    response = client.get(
        "/admin/users?q=alice-search"
    )

    assert response.status_code == 200
    assert b"alice-search@test.com" in response.data
    assert b"bob-search@test.com" not in response.data


def test_user_password_hash_is_not_displayed(app, client):

    register_login_route(app)

    admin = create_user(
        "Privacy Admin",
        "privacy-admin@test.com",
        role="admin"
    )

    create_user(
        "Private User",
        "private-user@test.com"
    )

    login_as(client, admin)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"test-only-secret-hash" not in response.data
    assert b"password_hash" not in response.data


def test_visitor_cannot_change_user_role(app, client):

    customer = create_user(
        "Target Customer",
        "target-visitor@test.com"
    )

    response = client.post(
        f"/admin/users/{customer.id}/role",
        data={"role": "admin"}
    )

    assert response.status_code == 302

    assert db.session.get(User, customer.id).role == "customer"


def test_customer_cannot_change_user_role(app, client):

    register_login_route(app)

    customer_admin = create_user(
        "Customer",
        "role-customer@test.com"
    )

    target = create_user(
        "Target",
        "role-target@test.com"
    )

    login_as(client, customer_admin)

    response = client.post(
        f"/admin/users/{target.id}/role",
        data={"role": "admin"}
    )

    assert response.status_code == 403

    assert db.session.get(User, target.id).role == "customer"


def test_admin_can_promote_user_and_audit_it(app, client):

    register_login_route(app)

    admin = create_user(
        "Administrator",
        "role-admin@test.com",
        role="admin"
    )

    customer = create_user(
        "Customer",
        "role-promotion@test.com"
    )

    login_as(client, admin)

    response = client.post(
        f"/admin/users/{customer.id}/role",
        data={"role": "admin"}
    )

    assert response.status_code == 302

    db.session.expire_all()

    updated_user = db.session.get(User, customer.id)

    assert updated_user.role == "admin"

    audit = AuditLog.query.filter_by(
        event_type="role_changed"
    ).one()

    assert audit.user_id == customer.id
    assert audit.actor_id == admin.id

    details = json.loads(audit.details)

    assert details["old_role"] == "customer"
    assert details["new_role"] == "admin"


def test_admin_can_demote_another_admin(app, client):

    register_login_route(app)

    admin = create_user(
        "Main Administrator",
        "main-role-admin@test.com",
        role="admin"
    )

    second_admin = create_user(
        "Second Administrator",
        "second-role-admin@test.com",
        role="admin"
    )

    login_as(client, admin)

    response = client.post(
        f"/admin/users/{second_admin.id}/role",
        data={"role": "customer"}
    )

    assert response.status_code == 302

    db.session.expire_all()

    updated_user = db.session.get(User, second_admin.id)

    assert updated_user.role == "customer"


def test_admin_cannot_demote_self(app, client):

    register_login_route(app)

    admin = create_user(
        "Administrator",
        "self-demotion@test.com",
        role="admin"
    )

    login_as(client, admin)

    response = client.post(
        f"/admin/users/{admin.id}/role",
        data={"role": "customer"}
    )

    assert response.status_code == 302

    db.session.expire_all()

    assert db.session.get(User, admin.id).role == "admin"


def test_invalid_role_is_rejected(app, client):

    register_login_route(app)

    admin = create_user(
        "Administrator",
        "invalid-role-admin@test.com",
        role="admin"
    )

    customer = create_user(
        "Customer",
        "invalid-role-target@test.com"
    )

    login_as(client, admin)

    response = client.post(
        f"/admin/users/{customer.id}/role",
        data={"role": "superadmin"}
    )

    assert response.status_code == 400

    assert db.session.get(User, customer.id).role == "customer"


def test_role_change_requires_csrf(app, client):

    register_login_route(app)

    admin = create_user(
        "Administrator",
        "csrf-role-admin@test.com",
        role="admin"
    )

    customer = create_user(
        "Customer",
        "csrf-role-target@test.com"
    )

    login_as(client, admin)

    # Enable CSRF after the test login has completed.
    app.config["WTF_CSRF_ENABLED"] = True

    response = client.post(
        f"/admin/users/{customer.id}/role",
        data={"role": "admin"}
    )

    assert response.status_code == 400

    assert db.session.get(User, customer.id).role == "customer"

def test_admin_user_search_escapes_xss(app, client):
    register_login_route(app)

    admin = create_user(
        "Security Admin",
        "xss-admin@test.com",
        role="admin"
    )

    login_as(client, admin)

    malicious_search = "<script>alert(1)</script>"

    response = client.get(
        "/admin/users",
        query_string={"q": malicious_search}
    )

    assert response.status_code == 200

    # Search input must display escaped text.
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data

    # Raw executable HTML must never appear.
    assert b"<script>alert(1)</script>" not in response.data