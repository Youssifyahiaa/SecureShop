"""Cart tests: add/update/remove, input validation, server-owned prices, stock never touched."""
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Product


def make_product(sku="SKU-1", name="Mug", price="10.00", stock=10, active=True):
    product = Product(sku=sku, name=name, description="", price=Decimal(price), stock=stock, active=active)
    db.session.add(product)
    db.session.commit()
    return product


def cart_of(client):
    with client.session_transaction() as sess:
        return sess.get("cart")


def test_add_product(app, client):
    p = make_product()
    resp = client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    assert resp.status_code == 302
    assert cart_of(client) == {str(p.id): 2}


def test_add_defaults_to_one(app, client):
    p = make_product()
    client.post(f"/cart/add/{p.id}")
    assert cart_of(client) == {str(p.id): 1}


def test_add_same_product_twice_sums_quantity(app, client):
    p = make_product()
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    client.post(f"/cart/add/{p.id}", data={"quantity": "3"})
    assert cart_of(client) == {str(p.id): 5}


def test_update_quantity(app, client):
    p = make_product()
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    client.post(f"/cart/update/{p.id}", data={"quantity": "4"})
    assert cart_of(client) == {str(p.id): 4}


def test_remove_item(app, client):
    p = make_product()
    client.post(f"/cart/add/{p.id}")
    client.post(f"/cart/remove/{p.id}")
    assert cart_of(client) == {}


def test_view_cart_shows_db_price_and_subtotal(app, client):
    p = make_product(price="12.50")
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    page = client.get("/cart").get_data(as_text=True)
    assert "12.50 EGP" in page
    assert "25.00 EGP" in page


@pytest.mark.parametrize("bad", ["0", "-1", "1.5", "abc", "", " ", "100", "1000", "1e2", "٣", "99999999999"])
def test_add_rejects_bad_quantities(app, client, bad):
    p = make_product(stock=500)
    resp = client.post(f"/cart/add/{p.id}", data={"quantity": bad})
    assert resp.status_code == 302
    assert not cart_of(client)


@pytest.mark.parametrize("bad", ["0", "-1", "1.5", "abc", "", "100"])
def test_update_rejects_bad_quantities(app, client, bad):
    p = make_product(stock=500)
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    client.post(f"/cart/update/{p.id}", data={"quantity": bad})
    assert cart_of(client) == {str(p.id): 2}


def test_add_unknown_product_rejected(app, client):
    client.post("/cart/add/9999")
    assert not cart_of(client)


def test_add_non_numeric_id_is_404(app, client):
    assert client.post("/cart/add/abc").status_code == 404


def test_add_inactive_product_rejected(app, client):
    p = make_product(active=False)
    client.post(f"/cart/add/{p.id}")
    assert not cart_of(client)


def test_add_out_of_stock_rejected(app, client):
    p = make_product(stock=0)
    client.post(f"/cart/add/{p.id}")
    assert not cart_of(client)


def test_add_more_than_stock_rejected(app, client):
    p = make_product(stock=3)
    client.post(f"/cart/add/{p.id}", data={"quantity": "4"})
    assert not cart_of(client)


def test_second_add_cannot_exceed_stock(app, client):
    p = make_product(stock=3)
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    assert cart_of(client) == {str(p.id): 2}


def test_update_above_stock_rejected(app, client):
    p = make_product(stock=3)
    client.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    client.post(f"/cart/update/{p.id}", data={"quantity": "5"})
    assert cart_of(client) == {str(p.id): 2}


def test_update_item_not_in_cart_rejected(app, client):
    p = make_product()
    client.post(f"/cart/update/{p.id}", data={"quantity": "2"})
    assert not cart_of(client)


def test_forged_price_fields_ignored(app, client):
    p = make_product(price="10.00")
    client.post(f"/cart/add/{p.id}", data={"quantity": "1", "price": "0.01", "total": "0.00"})
    assert cart_of(client) == {str(p.id): 1}
    page = client.get("/cart").get_data(as_text=True)
    assert "10.00 EGP" in page
    assert "0.01" not in page


def test_db_price_change_is_reflected(app, client):
    p = make_product(price="10.00")
    client.post(f"/cart/add/{p.id}")
    p.price = Decimal("15.00")
    db.session.commit()
    assert "15.00 EGP" in client.get("/cart").get_data(as_text=True)


def test_tampered_session_cart_is_sanitized(app, client):
    p = make_product()
    with client.session_transaction() as sess:
        sess["cart"] = {str(p.id): 1, "abc": 5, "-1": 2, "7": 0, "8": 1000, "9": 1.5}
    client.get("/cart")
    assert cart_of(client) == {str(p.id): 1}


def test_cart_never_changes_stock(app, client):
    p = make_product(stock=10)
    client.post(f"/cart/add/{p.id}", data={"quantity": "3"})
    client.post(f"/cart/update/{p.id}", data={"quantity": "5"})
    client.post(f"/cart/remove/{p.id}")
    db.session.refresh(p)
    assert p.stock == 10


def test_get_not_allowed_on_mutations(app, client):
    p = make_product()
    for path in ("add", "update", "remove"):
        assert client.get(f"/cart/{path}/{p.id}").status_code == 405


def test_carts_are_isolated_between_clients(app):
    p = make_product()
    a = app.test_client()
    b = app.test_client()
    a.post(f"/cart/add/{p.id}", data={"quantity": "2"})
    assert cart_of(a) == {str(p.id): 2}
    assert not cart_of(b)


def test_cart_entry_limit(app, client):
    from app.services.cart_session import CART_MAX_ENTRIES

    ids = [make_product(sku=f"S{i}", name=f"P{i}").id for i in range(CART_MAX_ENTRIES + 1)]
    for pid in ids:
        client.post(f"/cart/add/{pid}")
    assert len(cart_of(client)) == CART_MAX_ENTRIES


def test_csrf_blocks_post_without_token(app):
    from app import create_app
    from app.config import TEST_CONFIG

    config = dict(TEST_CONFIG, WTF_CSRF_ENABLED=True)
    csrf_app = create_app(config)
    with csrf_app.app_context():
        db.create_all()
        p = make_product()
        client = csrf_app.test_client()
        resp = client.post(f"/cart/add/{p.id}", data={"quantity": "1"})
        assert resp.status_code == 400
        with client.session_transaction() as sess:
            assert not sess.get("cart")
        db.session.remove()
        db.drop_all()