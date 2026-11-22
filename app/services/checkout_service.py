"""Server-owned cart totals and checkout preview.

Security rules
--------------
* The session cart holds only {"<product id>": quantity}. Prices, totals, discounts,
  user ids, roles and credit balances are NEVER read from the request or session;
  prices come only from Product.price and credit only from the users table.
* All money is Decimal, quantized to 0.01 with ROUND_HALF_UP.
* Error messages are safe to show to the user (no internal details).

Planned atomic payment transaction (Task 6; NOT implemented here)
-----------------------------------------------------------------
Inside ONE database transaction:

1. Revalidate: rebuild the preview from the DB (calculate_cart + coupon) and refuse
   if there are errors, the cart is empty, or the total changed.
2. Debit credit with a conditional UPDATE:
       UPDATE users SET credit_balance = credit_balance - :total
       WHERE id = :uid AND credit_balance >= :total
   and require rowcount == 1 (otherwise: insufficient credit, roll back).
3. Insert the Order and its OrderItems (unit_price_snapshot = Product.price now).
4. flush() so the order has an id.
5. redeem_coupon(...) for the order (promotions), if a coupon was applied.
6. Decrement stock with a conditional UPDATE per line:
       UPDATE products SET stock = stock - :qty WHERE id = :pid AND stock >= :qty
   and require rowcount == 1 for each line.
7. Append a CreditLedger row (change = -total, balance_after, reason="checkout").
8. ONE commit. Any error at any step -> rollback, nothing is persisted.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.extensions import db
from app.models.product import Product
from app.models.user import User
from app.services import coupon_gateway
from app.services.cart_session import sanitize_cart

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    """Convert to Decimal with exactly two decimal places (ROUND_HALF_UP)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CartLine:
    product_id: int
    name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


@dataclass
class CartResult:
    lines: list = field(default_factory=list)
    subtotal: Decimal = ZERO
    errors: list = field(default_factory=list)

    @property
    def is_empty(self):
        return not self.lines


@dataclass
class CheckoutPreview:
    cart: CartResult
    discount: Decimal
    total: Decimal
    credit_balance: Decimal
    coupon_reason: str
    can_pay: bool


def calculate_cart(user, session_cart):
    """Price the session cart from the database. `user` is accepted for future per-user rules."""
    result = CartResult()
    subtotal = ZERO
    for key, quantity in sanitize_cart(session_cart).items():
        product = db.session.get(Product, int(key))
        if product is None:
            result.errors.append("An item in your cart is no longer available and was removed.")
            continue
        if not product.active:
            result.errors.append(f"{product.name} is no longer available.")
        elif quantity > product.stock:
            result.errors.append(f"Only {product.stock} left of {product.name}")
        unit_price = money(product.price)
        line_total = money(unit_price * quantity)
        result.lines.append(CartLine(product.id, product.name, unit_price, quantity, line_total))
        subtotal += line_total
    result.subtotal = money(subtotal)
    return result


def build_checkout_preview(user, session_cart, coupon_code=None, now=None):
    """Server-computed totals for the checkout page; nothing here is taken from the client.

    Read-only: runs with autoflush off so an unsaved in-memory change (e.g. to the user's
    credit_balance) is never written by the queries here and never affects the result.
    """
    with db.session.no_autoflush:
        return _build_preview(user, session_cart, coupon_code, now)


def _build_preview(user, session_cart, coupon_code, now):
    cart = calculate_cart(user, session_cart)

    discount = ZERO
    coupon_reason = ""
    code = coupon_code.strip() if isinstance(coupon_code, str) else ""
    if code:
        outcome = coupon_gateway.validate_coupon(user.id, code, cart.subtotal, now)
        coupon_reason = outcome.reason or ""
        if outcome.valid:
            discount = min(max(money(outcome.discount), ZERO), cart.subtotal)

    total = max(money(cart.subtotal - discount), ZERO)

    # Stored balance straight from the users table, never the in-memory attribute.
    stored = db.session.execute(select(User.credit_balance).where(User.id == user.id)).scalar_one_or_none()
    credit_balance = money(stored if stored is not None else ZERO)

    can_pay = (not cart.is_empty) and not cart.errors and total <= credit_balance
    return CheckoutPreview(cart, discount, total, credit_balance, coupon_reason, can_pay)
