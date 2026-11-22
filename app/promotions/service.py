"""Newsletter and coupon business logic.

Owner: Ali
"""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from decimal import ROUND_HALF_UP
from sqlalchemy import func
from app.models.promotion import CouponRedemption
from sqlalchemy import update, or_
from app.models.order import Order

from app.models.promotion import Coupon
from .forms import normalize_email

from dataclasses import dataclass

from app.models.user import User

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.promotion import NewsletterSubscriber



@dataclass(frozen=True)
class CouponResult:
    """Safe result returned by coupon validation."""

    valid: bool
    discount: Decimal
    reason: str
    coupon_id: int | None
class CouponUnavailable(Exception):
    """Raised when a coupon cannot be redeemed safely."""

    pass



def coupon_recipient_matches_user(coupon: Coupon, user: User | None) -> bool:
    """Check whether a user may use a recipient-restricted coupon."""

    # Public coupons have no recipient restriction.
    if coupon.assigned_email is None:
        return True

    # Personal coupons require a real, confirmed account.
    if user is None or not user.is_confirmed:
        return False

    # The authenticated account must own the assigned email.
    return normalize_email(user.email) == coupon.assigned_email


def coupon_recipient_matches_user_id(
    coupon: Coupon,
    user_id: int,
) -> bool:
    """Verify coupon ownership using the real database account."""

    user = db.session.get(User, user_id)

    if user is None or not user.is_confirmed:
        return False

    return coupon_recipient_matches_user(coupon, user)


def generate_welcome_coupon_code():
    """Generate a cryptographically random coupon code."""
    return "NL-" + secrets.token_hex(16).upper()


def build_welcome_coupon(email):
    """Build a personal welcome coupon without saving it."""

    normalized_email = normalize_email(email)
    now = datetime.now(timezone.utc)

    return Coupon(
        code=generate_welcome_coupon_code(),
        assigned_email=normalized_email,
        kind="percent",
        amount=Decimal("10.00"),
        expires_at=now + timedelta(days=7),
        active=True,
        max_uses=1,
        per_user_limit=1,
        used_count=0,
    )

def create_newsletter_subscription(email):
    """Create one subscriber and welcome coupon atomically.

    Returns the new Coupon object, or None if already subscribed.
    This function does not send email or expose coupon codes.
    """

    normalized_email = normalize_email(email)

    # Avoid issuing another coupon for an existing subscriber.
    existing = db.session.scalar(
        select(NewsletterSubscriber.id).where(
            NewsletterSubscriber.email == normalized_email
        )
    )

    if existing is not None:
        return None

    coupon = build_welcome_coupon(normalized_email)

    subscriber = NewsletterSubscriber(
        email=normalized_email,
        coupon=coupon,
    )

    db.session.add(subscriber)

    try:
        # One transaction saves both records.
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        # Handles a duplicate email submitted concurrently.
        existing = db.session.scalar(
            select(NewsletterSubscriber.id).where(
                NewsletterSubscriber.email == normalized_email
            )
        )

        if existing is not None:
            return None

        # Other database errors must not be mistaken for duplicates.
        raise

    return coupon

def validate_coupon(user_id, code, subtotal, now) -> CouponResult:
    """Validate a coupon without changing database records.

    This initial implementation fails closed until all
    eligibility and discount checks are implemented.
    """

    invalid = CouponResult(
        valid=False,
        discount=Decimal("0.00"),
        reason="This coupon cannot be applied.",
        coupon_id=None,
    )

    # Reject malformed or excessively long input.
    if not isinstance(code, str):
        return invalid

    normalized_code = code.strip().upper()

    if not normalized_code or len(normalized_code) > 64:
        return invalid

    # Look up the coupon using the database.
    coupon = db.session.scalar(
        select(Coupon).where(Coupon.code == normalized_code)
    )

    # Reject unknown or inactive coupons.
    if coupon is None or not coupon.active:
        return invalid
    # Require a valid, nonnegative monetary subtotal.
    if (
        not isinstance(subtotal, Decimal)
        or not subtotal.is_finite()
        or subtotal < 0
    ):
        return invalid

    # The trusted caller must supply a timezone-aware time.
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        return invalid

    # SQLite may return timezone-naive timestamps.
    # Coupon expiration values are stored by our policy in UTC.
    expires_at = coupon.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now >= expires_at:
        return invalid

    # Verify the actual confirmed database user.
    # Personal coupons also require a matching email.
    if not coupon_recipient_matches_user_id(coupon, user_id):
        return invalid

    # Check the global usage limit.
    if (
        coupon.max_uses is not None
        and coupon.used_count >= coupon.max_uses
    ):
        return invalid

    # Check this customer's previous redemptions.
    if coupon.per_user_limit is not None:
        previous_uses = db.session.scalar(
            select(func.count(CouponRedemption.id)).where(
                CouponRedemption.coupon_id == coupon.id,
                CouponRedemption.user_id == user_id,
            )
        )

        if previous_uses >= coupon.per_user_limit:
            return invalid

    # Calculate the discount using Decimal arithmetic.
    if coupon.kind == "percent":
        discount = (
            subtotal * coupon.amount / Decimal("100")
        )
    elif coupon.kind == "fixed":
        discount = coupon.amount
    else:
        return invalid

    # A discount must never exceed the order subtotal.
    discount = min(subtotal, discount).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    return CouponResult(
        valid=True,
        discount=discount,
        reason="Coupon applied.",
        coupon_id=coupon.id,
    )

def redeem_coupon(coupon_id, user_id, order_id) -> None:
    """Redeem a coupon within checkout's existing transaction.

    The checkout service owns commit and rollback.
    """

    error_message = "This coupon cannot be redeemed."

    coupon = db.session.get(Coupon, coupon_id)
    order = db.session.get(Order, order_id)

    # The coupon and order must exist and be eligible.
    if coupon is None or order is None or not coupon.active:
        raise CouponUnavailable(error_message)

    # Prevent redeeming against somebody else's order.
    if order.user_id != user_id:
        raise CouponUnavailable(error_message)

    # Require a real, confirmed account and enforce email binding.
    if not coupon_recipient_matches_user_id(coupon, user_id):
        raise CouponUnavailable(error_message)

    # Convert SQLite's timezone-naive UTC values for comparison.
    expires_at = coupon.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expires_at:
        raise CouponUnavailable(error_message)

    # An order may contain only one coupon redemption.
    existing_order_redemption = db.session.scalar(
        select(CouponRedemption.id).where(
            CouponRedemption.order_id == order_id
        )
    )

    if existing_order_redemption is not None:
        raise CouponUnavailable(error_message)

    # Increment atomically, but only if the coupon is still
    # active, unexpired, and below its global usage limit.
    result = db.session.execute(
        update(Coupon)
        .where(
            Coupon.id == coupon_id,
            Coupon.active.is_(True),
            Coupon.expires_at > datetime.now(timezone.utc),
            or_(
                Coupon.max_uses.is_(None),
                Coupon.used_count < Coupon.max_uses,
            ),
        )
        .values(
            used_count=Coupon.used_count + 1
        )
        .execution_options(synchronize_session=False)
    )

    if result.rowcount != 1:
        raise CouponUnavailable(error_message)

    # Check the per-user limit after obtaining the write lock
    # through the conditional UPDATE.
    if coupon.per_user_limit is not None:
        previous_uses = db.session.scalar(
            select(func.count(CouponRedemption.id)).where(
                CouponRedemption.coupon_id == coupon_id,
                CouponRedemption.user_id == user_id,
            )
        )

        if previous_uses >= coupon.per_user_limit:
            raise CouponUnavailable(error_message)

    # Record the redemption in the same transaction.
    db.session.add(
        CouponRedemption(
            coupon_id=coupon_id,
            user_id=user_id,
            order_id=order_id,
        )
    )

    # Execute the INSERT without committing.
    db.session.flush()
