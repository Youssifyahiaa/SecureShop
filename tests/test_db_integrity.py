"""SQLite must enforce foreign keys on every connection the app opens."""
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import CreditLedger, Order, User

MISSING_ID = 999_999


def make_user(email="fk@example.com"):
    user = User(name="FK", email=email)
    user.set_password("correct horse battery staple")
    db.session.add(user)
    db.session.commit()
    return user


def assert_rejected(obj):
    db.session.add(obj)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_foreign_keys_pragma_is_on(app):
    assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_order_with_unknown_user_rejected(app):
    assert_rejected(Order(user_id=MISSING_ID, idempotency_key="ghost-user"))
    assert Order.query.count() == 0


def test_credit_ledger_with_unknown_order_rejected(app):
    user = make_user()
    assert_rejected(
        CreditLedger(
            user_id=user.id,
            order_id=MISSING_ID,
            change=Decimal("-1.00"),
            balance_after=Decimal("0.00"),
            reason="checkout",
        )
    )
    assert CreditLedger.query.count() == 0
