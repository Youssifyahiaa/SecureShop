"""Isolated demonstration of an insecure order lookup."""

from datetime import datetime, timezone
from decimal import Decimal

from flask import jsonify, request
from flask_login import login_user

from app.extensions import db
from app.models.user import User
from app.models.order import Order


def register_demo_routes(app):

    if "demo_naive_order_lookup" not in app.view_functions:

        def naive_order_lookup():
            # INTENTIONALLY VULNERABLE:
            # Trusts a user_id supplied by the requester.
            # No check that the orders belong to the current user.

            requested_user_id = request.args.get(
                "user_id",
                type=int
            )

            orders = db.session.execute(
                db.select(Order).where(
                    Order.user_id == requested_user_id
                )
            ).scalars().all()

            return jsonify({
                "order_ids": [order.id for order in orders]
            })

        app.add_url_rule(
            "/_demo/naive-order-history",
            endpoint="demo_naive_order_lookup",
            view_func=naive_order_lookup,
            methods=["GET"]
        )

    if "demo_idor_login" not in app.view_functions:

        def demo_login(user_id):

            user = db.session.get(User, user_id)

            if user is None:
                return "Not found", 404

            login_user(user)

            return "", 204

        app.add_url_rule(
            "/_demo/idor-login/<int:user_id>",
            endpoint="demo_idor_login",
            view_func=demo_login,
            methods=["POST"]
        )


def create_customer(name, email):

    customer = User(
        name=name,
        email=email,
        password_hash="test-only-placeholder",
        confirmed_at=datetime.now(timezone.utc),
        role="customer"
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def test_naive_order_lookup_exposes_another_users_order(
    app,
    client
):

    register_demo_routes(app)

    # Create two different customers.
    attacker = create_customer(
        "Customer A",
        "attacker-idor@example.test"
    )

    victim = create_customer(
        "Customer B",
        "victim-idor@example.test"
    )

    # Create an order belonging only to Customer B.
    victim_order = Order(
        user_id=victim.id,
        status="pending",
        subtotal=Decimal("45.00"),
        discount=Decimal("0.00"),
        total=Decimal("45.00"),
        idempotency_key="idor-demo-victim-order"
    )

    db.session.add(victim_order)
    db.session.commit()

    # Log in as Customer A.
    login_response = client.post(
        f"/_demo/idor-login/{attacker.id}"
    )

    assert login_response.status_code == 204

    # Customer A requests Customer B's order history.
    response = client.get(
        f"/_demo/naive-order-history?user_id={victim.id}"
    )

    # The vulnerable endpoint exposes the victim's order ID.
    assert response.status_code == 200

    assert victim_order.id in response.get_json()["order_ids"]