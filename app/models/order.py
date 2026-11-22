"""Order, order item and store-credit ledger models. All money values are Decimal (Numeric(10, 2))."""
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
    items = db.relationship("OrderItem", back_populates="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    """One line of an order. unit_price_snapshot is the DB price at checkout time, never client input."""

    __tablename__ = "order_items"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_order_items_quantity_pos"),
        db.CheckConstraint("unit_price_snapshot >= 0", name="ck_order_items_unit_price_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_snapshot = db.Column(MONEY, nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")


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
