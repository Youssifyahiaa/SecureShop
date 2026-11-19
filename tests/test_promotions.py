
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
from app.models.promotion import Coupon, NewsletterSubscriber, CouponRedemption
from app.models.user import User


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

def test_newsletter_rejects_nonexistent_coupon(app):
    """A subscriber cannot reference a coupon that does not exist."""

    with app.app_context():

        # Confirm SQLite foreign-key enforcement is enabled.
        with db.engine.connect() as conn:
            fk_enabled = conn.exec_driver_sql(
                "PRAGMA foreign_keys"
            ).scalar()

            assert fk_enabled == 1

        # Try inserting a subscriber with an invalid coupon ID.
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(
                    NewsletterSubscriber.__table__.insert().values(
                        email="orphan@example.com",
                        coupon_id=999999,
                        subscribed_at=datetime.now(timezone.utc),
                    )
                )
def test_redemption_rejects_nonexistent_order(app):
    """A coupon redemption must reference an existing order."""

    with app.app_context():

        # Create a valid user and coupon for this test.
        with db.engine.begin() as conn:
            user_id = conn.execute(
                User.__table__.insert().values(
                    name="FK Test User",
                    email="fk-order@example.com",
                    password_hash="test-only-unused-hash",
                )
            ).inserted_primary_key[0]

            coupon_id = conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data("FKORDER10")
                )
            ).inserted_primary_key[0]

        # Attempt to redeem the coupon for a nonexistent order.
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(
                    CouponRedemption.__table__.insert().values(
                        coupon_id=coupon_id,
                        user_id=user_id,
                        order_id=999999,
                    )
                )