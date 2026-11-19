"""Order and store-credit ledger models. All money values are Decimal (Numeric(10, 2))."""
from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db

MONEY = db.Numeric(10, 2, asdecimal=True)
ZERO = Decimal("0.00")


def _utcnow():
    return datetime.now(timezone.utc)


class Order(db.Model):
    __tablename__ = "orders"
    __table_args__ = (
        db.CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_nonneg"),
        db.CheckConstraint("discount >= 0", name="ck_orders_discount_nonneg"),
        db.CheckConstraint("total >= 0", name="ck_orders_total_nonneg"),
        db.CheckConstraint("discount <= subtotal", name="ck_orders_discount_le_subtotal"),
        db.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    subtotal = db.Column(MONEY, nullable=False, default=ZERO)
    discount = db.Column(MONEY, nullable=False, default=ZERO)
    total = db.Column(MONEY, nullable=False, default=ZERO)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    idempotency_key = db.Column(db.String(64), nullable=False)

    user = db.relationship("User", backref=db.backref("orders", lazy=True))


class CreditLedger(db.Model):
    """Append-only record of store-credit changes. change < 0 is a debit."""

    __tablename__ = "credit_ledger"
    __table_args__ = (
        db.CheckConstraint("balance_after >= 0", name="ck_credit_ledger_balance_after_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)  # None for admin adjustments
    change = db.Column(MONEY, nullable=False)
    balance_after = db.Column(MONEY, nullable=False)
    reason = db.Column(db.String(50), nullable=False)  # "checkout", "admin_adjustment", "seed"
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # admin for manual adjustments
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("credit_entries", lazy=True))
    order = db.relationship("Order", backref=db.backref("credit_entries", lazy=True))
    created_by = db.relationship("User", foreign_keys=[created_by_id])
