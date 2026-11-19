
"""Tests for customer account management."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from flask import abort
from flask_login import login_user
from app.models.audit_log import AuditLog
from app.extensions import db
from app.models.user import User
from app.models.order import Order


def create_user(
    name,
    email,
    role="customer",
    confirmed=True,
    credit_balance=Decimal("0.00")
):
    user = User(
        name=name,
        email=email.lower(),
        password_hash="test-only-password-hash",
        role=role,
        confirmed_at=(
            datetime.now(timezone.utc)
            if confirmed else None
        ),
        credit_balance=credit_balance
    )

    db.session.add(user)
    db.session.commit()

    return user


def create_order(user, total, idempotency_key):
    order = Order(
        user_id=user.id,
        status="paid",
        subtotal=total,
        discount=Decimal("0.00"),
        total=total,
        idempotency_key=idempotency_key
    )

    db.session.add(order)
    db.session.commit()

    return order


def register_login_route(app):

    def test_login(user_id):
        user = db.session.get(User, user_id)

        if user is None:
            abort(404)

        login_user(user)

        return "", 204

    if "test_account_login" not in app.view_functions:
        app.add_url_rule(
            "/_test/account-login/<int:user_id>",
            endpoint="test_account_login",
            view_func=test_login,
            methods=["POST"]
        )


def login_as(client, user):
    response = client.post(
        f"/_test/account-login/{user.id}"
    )

    assert response.status_code == 204


def test_visitor_cannot_access_account_dashboard(app, client):
    register_login_route(app)

    response = client.get("/account/")

    assert response.status_code == 302


def test_visitor_cannot_access_profile(app, client):
    register_login_route(app)

    response = client.get("/account/profile")

    assert response.status_code == 302


def test_customer_can_view_dashboard(app, client):
    register_login_route(app)

    customer = create_user(
        "Alice",
        "alice-account@test.com",
        credit_balance=Decimal("50.00")
    )

    login_as(client, customer)

    response = client.get("/account/")

    assert response.status_code == 200
    assert b"Welcome back, Alice" in response.data
    assert b"alice-account@test.com" in response.data
    assert b"50.00" in response.data


def test_customer_only_sees_own_orders(app, client):
    register_login_route(app)

    customer_one = create_user(
        "Customer One",
        "one@test.com"
    )

    customer_two = create_user(
        "Customer Two",
        "two@test.com"
    )

    create_order(
        customer_one,
        Decimal("125.50"),
        "account-order-one"
    )

    create_order(
        customer_two,
        Decimal("987.65"),
        "account-order-two"
    )

    login_as(client, customer_one)

    response = client.get("/account/")

    assert response.status_code == 200
    assert b"125.50" in response.data
    assert b"987.65" not in response.data


def test_customer_can_view_own_profile(app, client):
    register_login_route(app)

    customer = create_user(
        "Alice",
        "alice-profile@test.com"
    )

    login_as(client, customer)

    response = client.get("/account/profile")

    assert response.status_code == 200
    assert b"Alice" in response.data
    assert b"alice-profile@test.com" in response.data


def test_customer_can_update_name(app, client):
    register_login_route(app)

    customer = create_user(
        "Old Name",
        "update-name@test.com"
    )

    login_as(client, customer)

    response = client.post(
        "/account/profile",
        data={"name": "New Name"},
        follow_redirects=True
    )

    assert response.status_code == 200

    updated_user = db.session.get(User, customer.id)

    assert updated_user.name == "New Name"
    assert b"updated successfully" in response.data


def test_customer_cannot_change_email_through_profile(app, client):
    register_login_route(app)

    customer = create_user(
        "Original Name",
        "original@test.com"
    )

    login_as(client, customer)

    client.post(
        "/account/profile",
        data={
            "name": "Updated Name",
            "email": "attacker@test.com"
        }
    )

    updated_user = db.session.get(User, customer.id)

    assert updated_user.email == "original@test.com"
    assert updated_user.name == "Updated Name"


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        " " * 5,
        "A" * 101
    ]
)
def test_profile_rejects_invalid_names(
    app,
    client,
    invalid_name
):
    register_login_route(app)

    customer = create_user(
        "Original Name",
        "invalid-name@test.com"
    )

    login_as(client, customer)

    response = client.post(
        "/account/profile",
        data={"name": invalid_name}
    )

    assert response.status_code == 200

    unchanged_user = db.session.get(User, customer.id)

    assert unchanged_user.name == "Original Name"


def test_admin_can_access_own_account(app, client):
    register_login_route(app)

    admin = create_user(
        "Administrator",
        "admin-account@test.com",
        role="admin"
    )

    login_as(client, admin)

    response = client.get("/account/")

    assert response.status_code == 200
    assert b"Administrator" in response.data
def test_profile_update_creates_audit_event(app, client):
    register_login_route(app)

    customer = create_user(
        "Original Name",
        "audit-profile@test.com"
    )

    login_as(client, customer)

    response = client.post(
        "/account/profile",
        data={"name": "Updated Name"},
        follow_redirects=True
    )

    assert response.status_code == 200

    event = AuditLog.query.filter_by(
        event_type="profile_updated",
        user_id=customer.id
    ).first()

    assert event is not None
    assert event.actor_id is None
    assert event.details == '{"changed_fields":["name"]}'