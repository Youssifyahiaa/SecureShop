"""Newsletter and coupon business logic.

Owner: Ali
"""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.promotion import Coupon
from .forms import normalize_email

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.promotion import NewsletterSubscriber



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
