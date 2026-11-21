
"""
Database constraint tests for SecureShop Promotions.

Owner: Ali
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.promotions.service import CouponUnavailable, redeem_coupon
from sqlalchemy import create_engine
from app.promotions.service import validate_coupon
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func
from app.promotions.service import (
    create_newsletter_subscription,
    coupon_recipient_matches_user,
)

from app.extensions import db
from app.models.promotion import Coupon, NewsletterSubscriber, CouponRedemption
from app.models.user import User
from app.models.order import Order
from app.promotions.service import coupon_recipient_matches_user_id


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

def test_personal_coupon_recipient_binding():
    """Personal coupons require the matching, confirmed account."""

    coupon = Coupon(
        assigned_email="ali@example.com",
    )

    confirmed_owner = User(
        email="ali@example.com",
        confirmed_at=datetime.now(timezone.utc),
    )

    forwarded_recipient = User(
        email="ahmed@example.com",
        confirmed_at=datetime.now(timezone.utc),
    )

    unconfirmed_owner = User(
        email="ali@example.com",
        confirmed_at=None,
    )

    public_coupon = Coupon(
        assigned_email=None,
    )

    assert coupon_recipient_matches_user(
        coupon, confirmed_owner
    ) is True

    assert coupon_recipient_matches_user(
        coupon, forwarded_recipient
    ) is False

    assert coupon_recipient_matches_user(
        coupon, unconfirmed_owner
    ) is False

    assert coupon_recipient_matches_user(
        coupon, None
    ) is False

    assert coupon_recipient_matches_user(
        public_coupon, confirmed_owner
    ) is True


def test_coupon_recipient_verified_against_database_user(app):
    """A personal coupon must match the real confirmed database user."""

    with app.app_context():
        owner = User(
            name="Coupon Owner",
            email="owner@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=datetime.now(timezone.utc),
        )

        other_user = User(
            name="Other Customer",
            email="other@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=datetime.now(timezone.utc),
        )

        unconfirmed = User(
            name="Unconfirmed Owner",
            email="pending@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=None,
        )

        db.session.add_all([owner, other_user, unconfirmed])
        db.session.commit()

        coupon = Coupon(assigned_email="owner@example.com")
        pending_coupon = Coupon(assigned_email="pending@example.com")

        assert coupon_recipient_matches_user_id(
            coupon, owner.id
        ) is True

        assert coupon_recipient_matches_user_id(
            coupon, other_user.id
        ) is False

        assert coupon_recipient_matches_user_id(
            pending_coupon, unconfirmed.id
        ) is False

        assert coupon_recipient_matches_user_id(
            coupon, 999999
        ) is False

def test_validate_valid_public_percentage_coupon(app):
    """A valid public 10% coupon gives the correct discount."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Coupon Test Customer",
            email="valid-coupon@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="PUBLIC10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=1),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.commit()

        result = validate_coupon(
            user_id=user.id,
            code=" public10 ",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert result.valid is True
        assert result.discount == Decimal("20.00")
        assert result.coupon_id == coupon.id

def test_validate_personal_coupon_requires_confirmed_owner(app):
    """Only the matching confirmed account may validate a personal coupon."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        owner = User(
            name="Newsletter Owner",
            email="owner-newsletter@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=None,
        )

        other_user = User(
            name="Another Customer",
            email="other-newsletter@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="NL-PERSONAL-TEST",
            assigned_email="owner-newsletter@example.com",
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([owner, other_user, coupon])
        db.session.commit()

        # Scenario 1: Another confirmed user has the coupon code.
        forwarded = validate_coupon(
            user_id=other_user.id,
            code=coupon.code,
            subtotal=Decimal("100.00"),
            now=now,
        )

        assert forwarded.valid is False
        assert forwarded.discount == Decimal("0.00")
        assert forwarded.coupon_id is None

        # Scenario 2: Correct owner, but account is unconfirmed.
        unconfirmed = validate_coupon(
            user_id=owner.id,
            code=coupon.code,
            subtotal=Decimal("100.00"),
            now=now,
        )

        assert unconfirmed.valid is False

        # Scenario 3: Owner confirms their account.
        owner.confirmed_at = now
        db.session.commit()

        confirmed = validate_coupon(
            user_id=owner.id,
            code=coupon.code,
            subtotal=Decimal("100.00"),
            now=now,
        )

        assert confirmed.valid is True
        assert confirmed.discount == Decimal("10.00")
        assert confirmed.coupon_id == coupon.id

def test_validate_expired_coupon_rejected(app):
    """Expired coupons must never receive a discount."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Expiration Test Customer",
            email="expiration-test@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="EXPIRED10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now - timedelta(minutes=1),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.commit()

        # Scenario 1: Coupon expired one minute ago.
        expired = validate_coupon(
            user_id=user.id,
            code="EXPIRED10",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert expired.valid is False
        assert expired.discount == Decimal("0.00")
        assert expired.coupon_id is None

        # Scenario 2: Current time equals expiration time.
        coupon.expires_at = now
        db.session.commit()

        at_expiration = validate_coupon(
            user_id=user.id,
            code="EXPIRED10",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert at_expiration.valid is False
        assert at_expiration.discount == Decimal("0.00")
        assert at_expiration.coupon_id is None

def test_validate_inactive_coupon_rejected(app):
    """Inactive coupons must not provide a discount."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Inactive Coupon Test",
            email="inactive-test@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="INACTIVE10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=False,
            max_uses=10,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.commit()

        result = validate_coupon(
            user_id=user.id,
            code="INACTIVE10",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert result.valid is False
        assert result.discount == Decimal("0.00")
        assert result.coupon_id is None

def test_validate_coupon_global_limit_reached(app):
    """A coupon cannot exceed its global redemption limit."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Global Limit Test User",
            email="global-limit@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="LIMITREACHED10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=1,
        )

        db.session.add_all([user, coupon])
        db.session.commit()

        result = validate_coupon(
            user_id=user.id,
            code="LIMITREACHED10",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert result.valid is False
        assert result.discount == Decimal("0.00")
        assert result.coupon_id is None

        # Validation must not change the usage counter.
        db.session.refresh(coupon)
        assert coupon.used_count == 1

def test_validate_coupon_per_user_limit_reached(app):
    """Reject a coupon when this user reached their usage limit."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Per-User Limit Customer",
            email="per-user-limit@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="PERUSER10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=1,
        )

        db.session.add_all([user, coupon])
        db.session.flush()

        # Create a real previous order for this customer.
        order = Order(
            user_id=user.id,
            idempotency_key="per-user-limit-test-order",
        )

        db.session.add(order)
        db.session.flush()

        # Record one previous successful coupon redemption.
        redemption = CouponRedemption(
            coupon_id=coupon.id,
            user_id=user.id,
            order_id=order.id,
        )

        db.session.add(redemption)
        db.session.commit()

        # Customer tries to use the same coupon again.
        result = validate_coupon(
            user_id=user.id,
            code="PERUSER10",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert result.valid is False
        assert result.discount == Decimal("0.00")
        assert result.coupon_id is None

        # Validation must not consume another use.
        db.session.refresh(coupon)
        assert coupon.used_count == 1

def test_validate_fixed_coupon_capped_at_subtotal(app):
    """Fixed discounts must never exceed the order subtotal."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Fixed Discount Customer",
            email="fixed-discount@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="FIXED75",
            assigned_email=None,
            kind="fixed",
            amount=Decimal("75.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.commit()

        # Scenario 1: Subtotal is greater than the discount.
        normal = validate_coupon(
            user_id=user.id,
            code="FIXED75",
            subtotal=Decimal("200.00"),
            now=now,
        )

        assert normal.valid is True
        assert normal.discount == Decimal("75.00")
        assert normal.coupon_id == coupon.id

        # Scenario 2: Discount exceeds the subtotal.
        capped = validate_coupon(
            user_id=user.id,
            code="FIXED75",
            subtotal=Decimal("40.00"),
            now=now,
        )

        assert capped.valid is True
        assert capped.discount == Decimal("40.00")
        assert capped.coupon_id == coupon.id

        # Previewing must not consume the coupon.
        db.session.refresh(coupon)
        assert coupon.used_count == 0

def test_redeem_coupon_respects_checkout_transaction(app):
    """Redemption changes must roll back with checkout."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Redemption Test User",
            email="redemption@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="REDEEM10",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.flush()

        order = Order(
            user_id=user.id,
            idempotency_key="redemption-rollback-test",
            subtotal=Decimal("100.00"),
            discount=Decimal("10.00"),
            total=Decimal("90.00"),
        )

        db.session.add(order)
        db.session.commit()

        # Checkout begins redeeming the coupon.
        redeem_coupon(
            coupon_id=coupon.id,
            user_id=user.id,
            order_id=order.id,
        )

        db.session.flush()
        db.session.refresh(coupon)

        assert coupon.used_count == 1

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )
        assert redemption_count == 1

        # Simulate a checkout failure.
        db.session.rollback()
        db.session.refresh(coupon)

        assert coupon.used_count == 0

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )
        assert redemption_count == 0

def test_redeem_coupon_rejects_forwarded_code(app):
    """A personal coupon cannot be redeemed by another account."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        owner = User(
            name="Newsletter Coupon Owner",
            email="coupon-owner@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        attacker = User(
            name="Other Customer",
            email="other-customer@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="NL-FORWARDED-TEST",
            assigned_email="coupon-owner@example.com",
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([owner, attacker, coupon])
        db.session.flush()

        # The order belongs to the other customer.
        order = Order(
            user_id=attacker.id,
            idempotency_key="forwarded-coupon-order",
            subtotal=Decimal("100.00"),
            discount=Decimal("10.00"),
            total=Decimal("90.00"),
        )

        db.session.add(order)
        db.session.commit()

        # Even with a valid order, coupon ownership must be checked.
        with pytest.raises(CouponUnavailable):
            redeem_coupon(
                coupon_id=coupon.id,
                user_id=attacker.id,
                order_id=order.id,
            )

        db.session.rollback()
        db.session.refresh(coupon)

        # Rejection must not consume the coupon.
        assert coupon.used_count == 0

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )

        assert redemption_count == 0

def test_redeem_coupon_rejects_global_limit(app):
    """An exhausted coupon cannot be redeemed again."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        first_user = User(
            name="First Customer",
            email="first-limit@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        second_user = User(
            name="Second Customer",
            email="second-limit@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="GLOBALONCE",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=1,
        )

        db.session.add_all([first_user, second_user, coupon])
        db.session.flush()

        first_order = Order(
            user_id=first_user.id,
            idempotency_key="global-limit-first",
        )

        second_order = Order(
            user_id=second_user.id,
            idempotency_key="global-limit-second",
        )

        db.session.add_all([first_order, second_order])
        db.session.flush()

        # The first customer has already redeemed this coupon.
        db.session.add(
            CouponRedemption(
                coupon_id=coupon.id,
                user_id=first_user.id,
                order_id=first_order.id,
            )
        )

        db.session.commit()

        # A second customer attempts another redemption.
        with pytest.raises(CouponUnavailable):
            redeem_coupon(
                coupon_id=coupon.id,
                user_id=second_user.id,
                order_id=second_order.id,
            )

        # Checkout owns rollback after a rejected redemption.
        db.session.rollback()
        db.session.refresh(coupon)

        assert coupon.used_count == 1

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )

        assert redemption_count == 1

def test_redeem_coupon_rejects_per_user_limit(app):
    """A user cannot redeem a coupon beyond their personal limit."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Per-User Redemption Customer",
            email="redeem-per-user@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="REDEEMPERUSER",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=1,
        )

        db.session.add_all([user, coupon])
        db.session.flush()

        first_order = Order(
            user_id=user.id,
            idempotency_key="per-user-redeem-first",
        )

        second_order = Order(
            user_id=user.id,
            idempotency_key="per-user-redeem-second",
        )

        db.session.add_all([first_order, second_order])
        db.session.flush()

        # The customer has already used this coupon once.
        db.session.add(
            CouponRedemption(
                coupon_id=coupon.id,
                user_id=user.id,
                order_id=first_order.id,
            )
        )

        db.session.commit()

        # Attempt to redeem again on a different order.
        with pytest.raises(CouponUnavailable):
            redeem_coupon(
                coupon_id=coupon.id,
                user_id=user.id,
                order_id=second_order.id,
            )

        # Checkout must roll back the failed redemption.
        db.session.rollback()
        db.session.refresh(coupon)

        # The failed attempt must not consume another use.
        assert coupon.used_count == 1

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )

        assert redemption_count == 1

def test_redeem_coupon_rejects_expired_coupon(app):
    """Checkout must reject a coupon that has expired."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Expired Redemption User",
            email="expired-redeem@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="EXPIREDREDEEM",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now - timedelta(minutes=1),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, coupon])
        db.session.flush()

        order = Order(
            user_id=user.id,
            idempotency_key="expired-redemption-test",
        )

        db.session.add(order)
        db.session.commit()

        with pytest.raises(CouponUnavailable):
            redeem_coupon(coupon.id, user.id, order.id)

        db.session.rollback()
        db.session.refresh(coupon)

        assert coupon.used_count == 0
        assert db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        ) == 0


def test_redeem_coupon_rejects_another_users_order(app):
    """A user cannot redeem a coupon on another user's order."""

    with app.app_context():
        now = datetime.now(timezone.utc)

        user = User(
            name="Customer One",
            email="order-owner-one@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        other_user = User(
            name="Customer Two",
            email="order-owner-two@example.com",
            password_hash="test-only-unused-hash",
            confirmed_at=now,
        )

        coupon = Coupon(
            code="ORDEROWNERSHIP",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=10,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([user, other_user, coupon])
        db.session.flush()

        order = Order(
            user_id=other_user.id,
            idempotency_key="order-ownership-test",
        )

        db.session.add(order)
        db.session.commit()

        # User One tries to redeem on User Two's order.
        with pytest.raises(CouponUnavailable):
            redeem_coupon(coupon.id, user.id, order.id)

        db.session.rollback()
        db.session.refresh(coupon)

        assert coupon.used_count == 0
        assert db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        ) == 0

def test_concurrent_redemption_global_limit(tmp_path):
    """Two simultaneous attempts cannot redeem a single-use coupon twice."""

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app import create_app

    db_file = tmp_path / "concurrent_redemption.db"

    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "temporary-concurrency-test-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"timeout": 30}
        },
    })

    with test_app.app_context():
        db.create_all()

        now = datetime.now(timezone.utc)

        users = [
            User(
                name=f"Concurrent User {i}",
                email=f"concurrent-{i}@example.com",
                password_hash="test-only-unused-hash",
                confirmed_at=now,
            )
            for i in range(2)
        ]

        coupon = Coupon(
            code="CONCURRENTONCE",
            assigned_email=None,
            kind="percent",
            amount=Decimal("10.00"),
            expires_at=now + timedelta(days=7),
            active=True,
            max_uses=1,
            per_user_limit=1,
            used_count=0,
        )

        db.session.add_all([*users, coupon])
        db.session.flush()

        orders = [
            Order(
                user_id=user.id,
                idempotency_key=f"concurrent-order-{i}",
            )
            for i, user in enumerate(users)
        ]

        db.session.add_all(orders)
        db.session.flush()

        coupon_id = coupon.id
        attempts = [
            (user.id, order.id)
            for user, order in zip(users, orders)
        ]

        db.session.commit()
        db.session.remove()

    barrier = Barrier(2)

    def attempt_redemption(user_id, order_id):
        with test_app.app_context():
            try:
                # Both workers begin their attempts together.
                barrier.wait(timeout=10)

                redeem_coupon(coupon_id, user_id, order_id)
                db.session.commit()
                return "success"

            except CouponUnavailable:
                db.session.rollback()
                return "unavailable"

            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda pair: attempt_redemption(*pair),
                attempts,
            )
        )

    assert results.count("success") == 1
    assert results.count("unavailable") == 1

    with test_app.app_context():
        saved_coupon = db.session.get(Coupon, coupon_id)

        redemption_count = db.session.scalar(
            select(func.count()).select_from(CouponRedemption)
        )

        assert saved_coupon.used_count == 1
        assert redemption_count == 1
