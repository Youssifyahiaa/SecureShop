"""Order and CreditLedger model tests: Decimal money, uniqueness and CHECK constraints."""
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import CreditLedger, Order, User


def make_user(email="buyer@example.com"):
    user = User(name="Buyer", email=email)
    user.set_password("correct horse battery staple")
    db.session.add(user)
    db.session.commit()
    return user


def make_order(user, key="key-1", subtotal="20.00", discount="5.00", total="15.00"):
    return Order(
        user_id=user.id,
        idempotency_key=key,
        subtotal=Decimal(subtotal),
        discount=Decimal(discount),
        total=Decimal(total),
    )


def assert_rejected(obj):
    db.session.add(obj)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_order_saves_and_reloads_with_decimal_values(app):
    user = make_user()
    db.session.add(make_order(user, subtotal="19.99", discount="4.50", total="15.49"))
    db.session.commit()
    order_id = db.session.query(Order.id).scalar()
    db.session.expire_all()

    order = db.session.get(Order, order_id)
    assert order.user_id == user.id
    assert order.user.email == "buyer@example.com"
    assert order in user.orders
    assert order.status == "pending"
    assert order.created_at is not None
    for value, expected in ((order.subtotal, "19.99"), (order.discount, "4.50"), (order.total, "15.49")):
        assert isinstance(value, Decimal)
        assert value == Decimal(expected)
        assert value.as_tuple().exponent == -2


def test_order_money_defaults_to_zero(app):
    user = make_user()
    order = Order(user_id=user.id, idempotency_key="defaults")
    db.session.add(order)
    db.session.commit()
    assert order.subtotal == order.discount == order.total == Decimal("0.00")


def test_duplicate_idempotency_key_rejected(app):
    user = make_user()
    db.session.add(make_order(user, key="same-key"))
    db.session.commit()
    assert_rejected(make_order(user, key="same-key"))
    assert Order.query.count() == 1


def test_negative_total_rejected(app):
    user = make_user()
    assert_rejected(make_order(user, subtotal="10.00", discount="0.00", total="-1.00"))
    assert Order.query.count() == 0


def test_discount_greater_than_subtotal_rejected(app):
    user = make_user()
    assert_rejected(make_order(user, subtotal="10.00", discount="10.01", total="0.00"))
    assert Order.query.count() == 0


def test_order_requires_user_id(app):
    assert_rejected(Order(idempotency_key="no-user", subtotal=Decimal("1.00"), total=Decimal("1.00")))
    assert Order.query.count() == 0


def test_credit_ledger_links_to_user_and_order(app):
    user = make_user()
    admin = make_user("admin@example.com")
    order = make_order(user)
    db.session.add(order)
    db.session.commit()

    entry = CreditLedger(
        user_id=user.id,
        order_id=order.id,
        change=Decimal("-15.00"),
        balance_after=Decimal("35.00"),
        reason="checkout",
    )
    adjustment = CreditLedger(
        user_id=user.id,
        change=Decimal("50.00"),
        balance_after=Decimal("85.00"),
        reason="admin_adjustment",
        created_by_id=admin.id,
    )
    db.session.add_all([entry, adjustment])
    db.session.commit()
    db.session.expire_all()

    entry = db.session.get(CreditLedger, entry.id)
    assert entry.user.id == user.id
    assert entry.order.id == order.id
    assert entry.change == Decimal("-15.00") and isinstance(entry.change, Decimal)
    assert entry.balance_after == Decimal("35.00")
    assert entry.created_at is not None
    assert entry in order.credit_entries

    adjustment = db.session.get(CreditLedger, adjustment.id)
    assert adjustment.order is None
    assert adjustment.created_by.id == admin.id
    assert len(user.credit_entries) == 2


def test_credit_ledger_negative_balance_after_rejected(app):
    user = make_user()
    assert_rejected(
        CreditLedger(user_id=user.id, change=Decimal("-10.00"), balance_after=Decimal("-0.01"), reason="checkout")
    )
    assert CreditLedger.query.count() == 0
