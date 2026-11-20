"""Newsletter and coupon business logic.

Owner: Ali
"""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
