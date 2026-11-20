
"""
Database constraint tests for SecureShop Promotions.

Owner: Ali
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from app.promotions.service import create_newsletter_subscription

from app.extensions import db
from app.models.promotion import Coupon, NewsletterSubscriber, CouponRedemption
from app.models.user import User
from app.models.order import Order


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
def test_redemption_rejects_nonexistent_user(app):
    """A coupon redemption must reference an existing user."""

    with app.app_context():

        # Create a valid user, coupon, and order.
        with db.engine.begin() as conn:
            valid_user_id = conn.execute(
                User.__table__.insert().values(
                    name="Valid FK Test User",
                    email="fk-user@example.com",
                    password_hash="test-only-unused-hash",
                )
            ).inserted_primary_key[0]

            coupon_id = conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data("FKUSER10")
                )
            ).inserted_primary_key[0]

            order_id = conn.execute(
                Order.__table__.insert().values(
                    user_id=valid_user_id,
                    idempotency_key="fk-user-test-order",
                )
            ).inserted_primary_key[0]

        # The coupon and order exist, but this user does not.
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(
                    CouponRedemption.__table__.insert().values(
                        coupon_id=coupon_id,
                        user_id=999999,
                        order_id=order_id,
                    )
                )
def test_redemption_rejects_nonexistent_coupon(app):
    """A redemption must reference an existing coupon."""

    with app.app_context():

        # Create a valid user and order.
        with db.engine.begin() as conn:
            user_id = conn.execute(
                User.__table__.insert().values(
                    name="Coupon FK Test User",
                    email="fk-coupon@example.com",
                    password_hash="test-only-unused-hash",
                )
            ).inserted_primary_key[0]

            order_id = conn.execute(
                Order.__table__.insert().values(
                    user_id=user_id,
                    idempotency_key="fk-coupon-test-order",
                )
            ).inserted_primary_key[0]

        # The user and order exist, but the coupon does not.
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(
                    CouponRedemption.__table__.insert().values(
                        coupon_id=999999,
                        user_id=user_id,
                        order_id=order_id,
                    )
                )

def test_redemption_rejects_multiple_coupons_per_order(app):
    """An order must not have more than one coupon redemption."""

    with app.app_context():

        # Create one user, one order, and two valid coupons.
        with db.engine.begin() as conn:
            user_id = conn.execute(
                User.__table__.insert().values(
                    name="Single Coupon Test User",
                    email="single-coupon@example.com",
                    password_hash="test-only-unused-hash",
                )
            ).inserted_primary_key[0]

            order_id = conn.execute(
                Order.__table__.insert().values(
                    user_id=user_id,
                    idempotency_key="single-coupon-test-order",
                )
            ).inserted_primary_key[0]

            first_coupon_id = conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data("SINGLE10")
                )
            ).inserted_primary_key[0]

            second_coupon_id = conn.execute(
                Coupon.__table__.insert().values(
                    **coupon_data("SECOND10")
                )
            ).inserted_primary_key[0]

            # First coupon redemption is valid.
            conn.execute(
                CouponRedemption.__table__.insert().values(
                    coupon_id=first_coupon_id,
                    user_id=user_id,
                    order_id=order_id,
                )
            )

        # A second coupon redemption for the same order
        # must be rejected by the unique constraint.
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(
                    CouponRedemption.__table__.insert().values(
                        coupon_id=second_coupon_id,
                        user_id=user_id,
                        order_id=order_id,
                    )
                )
def test_newsletter_duplicate_normalized_email_issues_one_coupon(app):
    """Repeated signups must not create additional welcome coupons."""

    with app.app_context():
        coupons_before = db.session.scalar(
            select(func.count()).select_from(Coupon)
        )
        subscribers_before = db.session.scalar(
            select(func.count()).select_from(NewsletterSubscriber)
        )

        first = create_newsletter_subscription(
            "  NEWSLETTER-TEST@Example.COM  "
        )

        duplicate = create_newsletter_subscription(
            "newsletter-test@example.com"
        )

        coupons_after = db.session.scalar(
            select(func.count()).select_from(Coupon)
        )
        subscribers_after = db.session.scalar(
            select(func.count()).select_from(NewsletterSubscriber)
        )

        assert first is not None
        assert first.assigned_email == "newsletter-test@example.com"
        assert duplicate is None
        assert coupons_after == coupons_before + 1
        assert subscribers_after == subscribers_before + 1
