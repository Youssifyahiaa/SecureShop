"""Product model (shared by Catalog, Cart, Admin and Checkout).

All money values are Decimal (Numeric(10, 2)). Never use float for prices.
"""
from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db

MONEY = db.Numeric(10, 2, asdecimal=True)
ZERO = Decimal("0.00")


def _utcnow():
    return datetime.now(timezone.utc)


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        db.CheckConstraint("stock >= 0", name="ck_products_stock_nonneg"),
    )

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    price = db.Column(MONEY, nullable=False, default=ZERO)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    def __repr__(self):
        return f"<Product {self.id} {self.sku}>"