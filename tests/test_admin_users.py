
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
