"""Task 5: server-owned cart totals and checkout preview."""
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Order, OrderItem, Product, User
from app.services import checkout_service, coupon_gateway
from app.services.checkout_service import build_checkout_preview, calculate_cart


def make_user(email="buyer@example.com", credit="100.00"):
    user = User(name="Buyer", email=email, credit_balance=Decimal(credit))
    user.set_password("correct horse battery staple")
    db.session.add(user)
    db.session.commit()
    return user


def make_product(sku="SKU-1", name="Mug", price="10.00", stock=10, active=True):
    product = Product(sku=sku, name=name, description="", price=Decimal(price), stock=stock, active=active)
    db.session.add(product)
    db.session.commit()
    return product


def assert_money(value):
    assert isinstance(value, Decimal)
    assert value == value.quantize(Decimal("0.01"))
    assert value.as_tuple().exponent == -2


def test_price_changed_in_db_after_adding_to_cart_uses_new_price(app):
    user = make_user()
    product = make_product(price="10.00")
    cart = {str(product.id): 2}  # added to the cart while the price was 10.00

    product.price = Decimal("12.50")
    db.session.commit()

    result = calculate_cart(user, cart)
    assert result.errors == []
    assert result.lines[0].unit_price == Decimal("12.50")
    assert result.subtotal == Decimal("25.00")


def test_empty_cart_cannot_pay(app):
    user = make_user()
    preview = build_checkout_preview(user, {})
    assert preview.cart.is_empty
    assert preview.total == Decimal("0.00")
    assert preview.can_pay is False


def test_inactive_product_is_an_error(app):
    user = make_user()
    product = make_product(name="Old Mug", active=False)
    preview = build_checkout_preview(user, {str(product.id): 1})
    assert any("Old Mug" in e for e in preview.cart.errors)
    assert preview.can_pay is False


def test_stock_shortfall_is_an_error(app):
    user = make_user()
    product = make_product(name="Mug", stock=3)
    preview = build_checkout_preview(user, {str(product.id): 5})
    assert "Only 3 left of Mug" in preview.cart.errors
    assert preview.can_pay is False


def test_unknown_product_is_dropped_with_error(app):
    user = make_user()
    product = make_product()
    result = calculate_cart(user, {str(product.id): 1, "999999": 1})
    assert [line.product_id for line in result.lines] == [product.id]
    assert len(result.errors) == 1
    assert result.subtotal == Decimal("10.00")


def test_insufficient_credit_cannot_pay(app):
    user = make_user(credit="5.00")
    product = make_product(price="10.00")
    preview = build_checkout_preview(user, {str(product.id): 1})
    assert preview.cart.errors == []
    assert preview.total == Decimal("10.00")
    assert preview.credit_balance == Decimal("5.00")
    assert preview.can_pay is False


def test_sufficient_credit_can_pay(app):
    user = make_user(credit="10.00")
    product = make_product(price="10.00")
    preview = build_checkout_preview(user, {str(product.id): 1})
    assert preview.can_pay is True


def test_credit_balance_read_from_db_not_from_user_object(app):
    user = make_user(credit="5.00")
    cart = {str(make_product(price="10.00").id): 1}
    user.credit_balance = Decimal("1000.00")  # tampered in memory, never committed
    preview = build_checkout_preview(user, cart)
    assert preview.credit_balance == Decimal("5.00")
    assert preview.can_pay is False


def test_discount_never_exceeds_subtotal(app, monkeypatch):
    user = make_user(credit="0.00")
    product = make_product(price="10.00")

    def fake_validate(user_id, code, subtotal, now):
        return coupon_gateway.CouponResult(valid=True, discount=Decimal("500.00"), reason="")

    monkeypatch.setattr(coupon_gateway, "validate_coupon", fake_validate)
    preview = build_checkout_preview(user, {str(product.id): 1}, coupon_code="HUGE")
    assert preview.discount == Decimal("10.00")
    assert preview.total == Decimal("0.00")


def test_coupon_validator_receives_server_values(app, monkeypatch):
    user = make_user()
    product = make_product(price="7.25")
    seen = {}

    def fake_validate(user_id, code, subtotal, now):
        seen.update(user_id=user_id, code=code, subtotal=subtotal, now=now)
        return coupon_gateway.CouponResult(valid=True, discount=Decimal("1.005"), reason="ok")

    monkeypatch.setattr(coupon_gateway, "validate_coupon", fake_validate)
    preview = build_checkout_preview(user, {str(product.id): 2}, coupon_code=" SAVE ", now="NOW")
    assert seen == {"user_id": user.id, "code": "SAVE", "subtotal": Decimal("14.50"), "now": "NOW"}
    assert preview.discount == Decimal("1.01")  # ROUND_HALF_UP
    assert preview.total == Decimal("13.49")


def test_stub_gateway_rejects_coupons(app):
    user = make_user()
    product = make_product()
    preview = build_checkout_preview(user, {str(product.id): 1}, coupon_code="ANY")
    assert preview.discount == Decimal("0.00")
    assert preview.coupon_reason == "Coupons are not available yet."


@pytest.mark.parametrize(
    "bad_entry",
    [
        {"abc": 1},
        {"-1": 1},
        {"1.5": 1},
        {"²": 1},
        {"1": 0},
        {"1": -3},
        {"1": 100},
        {"1": 1.5},
        {"1": "2"},
        {"1": True},
        {"1": {"price": "0.01"}},
    ],
)
def test_malicious_session_cart_entries_ignored(app, bad_entry):
    user = make_user()
    make_product()  # id 1
    result = calculate_cart(user, bad_entry)
    assert result.lines == []
    assert result.subtotal == Decimal("0.00")


@pytest.mark.parametrize("bad_cart", [None, [], "1:1", [("1", 1)], 42])
def test_non_dict_session_cart_is_empty(app, bad_cart):
    user = make_user()
    make_product()
    preview = build_checkout_preview(user, bad_cart)
    assert preview.cart.is_empty
    assert preview.can_pay is False


def test_client_supplied_price_fields_ignored(app):
    user = make_user()
    product = make_product(price="10.00")
    cart = {str(product.id): 1, "price": "0.01", "total": "0.00", "discount": "10.00", "user_id": 99}
    preview = build_checkout_preview(user, cart)
    assert preview.cart.subtotal == Decimal("10.00")
    assert preview.total == Decimal("10.00")
    assert preview.discount == Decimal("0.00")


def test_money_is_decimal_with_two_places(app):
    user = make_user(credit="50")
    a = make_product(sku="A", name="A", price="3.335", stock=10)  # stored as Numeric(10,2)
    b = make_product(sku="B", name="B", price="0.10", stock=10)
    preview = build_checkout_preview(user, {str(a.id): 3, str(b.id): 1})
    for line in preview.cart.lines:
        assert_money(line.unit_price)
        assert_money(line.line_total)
    for value in (preview.cart.subtotal, preview.discount, preview.total, preview.credit_balance):
        assert_money(value)
    assert preview.cart.subtotal == sum((line.line_total for line in preview.cart.lines), Decimal("0.00"))


def test_money_helper_rounds_half_up():
    assert checkout_service.money("2.345") == Decimal("2.35")
    assert checkout_service.money("2.344") == Decimal("2.34")


def test_order_items_relationship_and_constraints(app):
    from sqlalchemy.exc import IntegrityError

    user = make_user()
    product = make_product()
    order = Order(user_id=user.id, idempotency_key="k1", subtotal=Decimal("20.00"), total=Decimal("20.00"))
    order.items.append(OrderItem(product_id=product.id, quantity=2, unit_price_snapshot=Decimal("10.00")))
    db.session.add(order)
    db.session.commit()
    assert db.session.get(Order, order.id).items[0].unit_price_snapshot == Decimal("10.00")

    for bad in (
        OrderItem(order_id=order.id, product_id=product.id, quantity=0, unit_price_snapshot=Decimal("1.00")),
        OrderItem(order_id=order.id, product_id=product.id, quantity=1, unit_price_snapshot=Decimal("-1.00")),
        OrderItem(order_id=order.id, product_id=999, quantity=1, unit_price_snapshot=Decimal("1.00")),
    ):
        db.session.add(bad)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
