
"""
Database constraint tests for SecureShop Promotions.

Owner: Ali
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.promotion import Coupon, NewsletterSubscriber


@pytest.fixture
def promotion_engine():
    """Create an isolated in-memory test database."""

    engine = create_engine("sqlite:///:memory:")

    db.metadata.create_all(
        bind=engine,
        tables=[
            Coupon.__table__,
            NewsletterSubscriber.__table__,
        ],
    )

    yield engine

    engine.dispose()


def coupon_data(code, amount=Decimal("10.00")):
    """Return valid test data for a coupon."""

    return {
        "code": code,
        "kind": "percent",
        "amount": amount,
        "expires_at": datetime(
            2030, 12, 31, tzinfo=timezone.utc
        ),
        "active": True,
        "max_uses": 10,
        "per_user_limit": 1,
        "used_count": 0,
    }


def test_duplicate_coupon_rejected(promotion_engine):
    """The database must reject duplicate coupon codes."""

    with promotion_engine.begin() as conn:
        conn.execute(
            Coupon.__table__.insert().values(
                **coupon_data("WELCOME10")
            )
        )

    with pytest.raises(IntegrityError):
        with promotion_engine.begin() as conn:
            conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data("WELCOME10")
                )
            )


def test_invalid_percentage_rejected(promotion_engine):
    """A percentage discount cannot exceed 100."""

    with pytest.raises(IntegrityError):
        with promotion_engine.begin() as conn:
            conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data(
                        "INVALID150",
                        Decimal("150.00"),
                    )
                )
            )


def test_duplicate_subscriber_rejected(promotion_engine):
    """One normalized email must not be registered twice."""

    with promotion_engine.begin() as conn:
        first_coupon = conn.execute(
            Coupon.__table__.insert().values(
                **coupon_data("WELCOME10")
            )
        ).inserted_primary_key[0]

        second_coupon = conn.execute(
            Coupon.__table__.insert().values(
                **coupon_data("WELCOME20")
            )
        ).inserted_primary_key[0]

        conn.execute(
            NewsletterSubscriber.__table__.insert().values(
                email="student@example.com",
                coupon_id=first_coupon,
            )
        )

    with pytest.raises(IntegrityError):
        with promotion_engine.begin() as conn:
            conn.execute(
                NewsletterSubscriber.__table__.insert().values(
                    email="student@example.com",
                    coupon_id=second_coupon,
                )
            )
