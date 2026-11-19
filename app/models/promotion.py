
"""Database models for SecureShop promotions.

Owner: Ali
"""

from app.extensions import db
from datetime import datetime, timezone



class Coupon(db.Model):
    """A discount coupon with usage restrictions."""

    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    kind = db.Column(
        db.String(10),
        nullable=False,
    )

    amount = db.Column(
        db.Numeric(10, 2, asdecimal=True),
        nullable=False,
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    max_uses = db.Column(
        db.Integer,
        nullable=True,
    )

    per_user_limit = db.Column(
        db.Integer,
        nullable=True,
    )

    used_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    __table_args__ = (
        db.CheckConstraint(
            "length(trim(code)) > 0",
            name="ck_coupons_code_not_blank",
        ),
        db.CheckConstraint(
            "kind IN ('percent', 'fixed')",
            name="ck_coupons_kind",
        ),
        db.CheckConstraint(
            "(kind = 'percent' AND amount > 0 AND amount <= 100) "
            "OR (kind = 'fixed' AND amount >= 0)",
            name="ck_coupons_amount",
        ),
        db.CheckConstraint(
            "used_count >= 0",
            name="ck_coupons_used_count",
        ),
        db.CheckConstraint(
            "max_uses IS NULL OR max_uses > 0",
            name="ck_coupons_max_uses",
        ),
        db.CheckConstraint(
            "per_user_limit IS NULL OR per_user_limit > 0",
            name="ck_coupons_per_user_limit",
        ),
        db.CheckConstraint(
            "max_uses IS NULL OR used_count <= max_uses",
            name="ck_coupons_usage_cap",
        ),
    )

class NewsletterSubscriber(db.Model):
    """A newsletter subscriber linked to an issued coupon."""

    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    subscribed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    coupon_id = db.Column(
        db.Integer,
        db.ForeignKey("coupons.id"),
        unique=True,
        nullable=False,
    )

    coupon = db.relationship(
        "Coupon",
        backref="newsletter_subscriber",
    )

    __table_args__ = (
        db.CheckConstraint(
            "length(trim(email)) > 0",
            name="ck_newsletter_email_not_blank",
        ),
    )


class CouponRedemption(db.Model):
    """Records a successful coupon redemption on an order."""

    __tablename__ = "coupon_redemptions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    coupon_id = db.Column(
        db.Integer,
        db.ForeignKey("coupons.id"),
        nullable=False,
        index=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id"),
        nullable=False,
    )

    coupon = db.relationship(
        "Coupon",
        backref="redemptions",
    )

    user = db.relationship(
        "User",
        backref="coupon_redemptions",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "order_id",
            name="uq_coupon_redemptions_order_id",
        ),
    )