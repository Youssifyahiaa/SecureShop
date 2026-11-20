"""Isolated demonstration of naive vs secure admin access."""

from datetime import datetime, timezone

from flask import session
from flask_login import login_user

from app.extensions import db
from app.models.user import User


def register_demo_routes(app):
    """Add vulnerable demonstration routes to the test app only."""

    if "demo_naive_admin" not in app.view_functions:

        def naive_admin():
            # INTENTIONALLY VULNERABLE:
            # No login or administrator role check.
            total_users = User.query.count()

            return f"Admin statistics: {total_users} users", 200

        app.add_url_rule(
            "/_demo/naive-admin",
            endpoint="demo_naive_admin",
            view_func=naive_admin,
            methods=["GET"]
        )

    if "demo_customer_login" not in app.view_functions:

        def customer_login(user_id):
            user = db.session.get(User, user_id)

            if user is None:
                return "Not found", 404

            login_user(user)
            session.permanent = True

            return "", 204

        app.add_url_rule(
            "/_demo/customer-login/<int:user_id>",
            endpoint="demo_customer_login",
            view_func=customer_login,
            methods=["POST"]
        )


def create_customer():

    customer = User(
        name="Demo Customer",
        email="demo-customer@example.test",
        password_hash="test-only-placeholder",
        confirmed_at=datetime.now(timezone.utc),
        role="customer"
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def test_anonymous_access_naive_vs_secure(app, client):

    register_demo_routes(app)

    # Naive endpoint: unauthorized access succeeds.
    naive_response = client.get("/_demo/naive-admin")

    assert naive_response.status_code == 200
    assert b"Admin statistics" in naive_response.data

    # Real SecureShop: visitor must log in.
    secure_response = client.get("/admin/")

    assert secure_response.status_code == 302


def test_customer_access_naive_vs_secure(app, client):

    register_demo_routes(app)

    customer = create_customer()

    login_response = client.post(
        f"/_demo/customer-login/{customer.id}"
    )

    assert login_response.status_code == 204

    # Naive endpoint: customer sees administrator information.
    naive_response = client.get("/_demo/naive-admin")

    assert naive_response.status_code == 200
    assert b"Admin statistics" in naive_response.data

    # Real SecureShop: customer is denied.
    secure_response = client.get("/admin/")

    assert secure_response.status_code == 403