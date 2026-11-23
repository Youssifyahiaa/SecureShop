"""Catalog tests: visibility, 404s, search, LIKE wildcards, SQLi-like input, in_stock, money filter."""
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Product


def make_product(sku="SKU-1", name="Mug", price="10.00", stock=10, active=True, description=""):
    product = Product(sku=sku, name=name, description=description, price=Decimal(price), stock=stock, active=active)
    db.session.add(product)
    db.session.commit()
    return product


def test_list_shows_only_active_products(app, client):
    make_product(sku="A", name="Visible Mug")
    make_product(sku="B", name="Hidden Mug", active=False)
    page = client.get("/products").get_data(as_text=True)
    assert "Visible Mug" in page
    assert "Hidden Mug" not in page


def test_list_empty_shows_message(app, client):
    page = client.get("/products").get_data(as_text=True)
    assert "No products found." in page


def test_detail_shows_product(app, client):
    p = make_product(name="Nice Mug", price="12.50", description="A mug")
    resp = client.get(f"/products/{p.id}")
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert "Nice Mug" in page
    assert "12.50 EGP" in page


def test_detail_inactive_is_404(app, client):
    p = make_product(active=False)
    assert client.get(f"/products/{p.id}").status_code == 404


@pytest.mark.parametrize("bad_id", ["9999", "abc", "-1", "1.5", "0"])
def test_detail_invalid_ids_are_404(app, client, bad_id):
    assert client.get(f"/products/{bad_id}").status_code == 404


def test_xss_is_escaped_in_detail_and_list(app, client):
    p = make_product(name="<script>alert(1)</script>", description="<b>x</b>")
    detail = client.get(f"/products/{p.id}").get_data(as_text=True)
    listing = client.get("/products").get_data(as_text=True)
    for page in (detail, listing):
        assert "<script>alert(1)</script>" not in page
        assert "&lt;script&gt;" in page


def test_search_is_case_insensitive_and_partial(app, client):
    make_product(sku="A", name="Ceramic Coffee Mug")
    make_product(sku="B", name="Notebook")
    page = client.get("/products?q=COFFEE").get_data(as_text=True)
    assert "Ceramic Coffee Mug" in page
    assert "Notebook" not in page
    assert "Ceramic Coffee Mug" in client.get("/products?q=ffee m").get_data(as_text=True)


def test_search_no_results(app, client):
    make_product(name="Mug")
    page = client.get("/products?q=zzzz").get_data(as_text=True)
    assert "No products found." in page


def test_search_does_not_return_inactive(app, client):
    make_product(name="Secret Mug", active=False)
    assert "Secret Mug" not in client.get("/products?q=secret").get_data(as_text=True)


def test_percent_and_underscore_are_literal(app, client):
    make_product(sku="A", name="Mug")
    make_product(sku="B", name="100% Cotton")
    make_product(sku="C", name="a_b")
    pct = client.get("/products?q=%25").get_data(as_text=True)
    assert "100% Cotton" in pct
    assert ">Mug<" not in pct
    under = client.get("/products?q=_").get_data(as_text=True)
    assert "a_b" in under
    assert ">Mug<" not in under


@pytest.mark.parametrize(
    "payload",
    ["' OR '1'='1", "'; DROP TABLE products; --", "\" OR 1=1 --", "' UNION SELECT * FROM users --", "\\"],
)
def test_sqli_like_input_is_harmless(app, client, payload):
    make_product(name="Mug")
    resp = client.get("/products", query_string={"q": payload})
    assert resp.status_code == 200
    assert "No products found." in resp.get_data(as_text=True)
    assert db.session.query(Product).count() == 1


def test_overlong_query_is_truncated_not_an_error(app, client):
    make_product(name="Mug")
    resp = client.get("/products", query_string={"q": "a" * 5000})
    assert resp.status_code == 200


def test_query_truncated_to_100_chars(app, client):
    make_product(name="a" * 100)
    resp = client.get("/products", query_string={"q": "a" * 100 + "zzz"})
    assert "No products found." not in resp.get_data(as_text=True)


@pytest.mark.parametrize("value", ["2", "true", "yes", "", "abc", "0"])
def test_invalid_in_stock_values_are_ignored(app, client, value):
    make_product(sku="A", name="In Mug", stock=5)
    make_product(sku="B", name="Out Mug", stock=0)
    page = client.get("/products", query_string={"in_stock": value}).get_data(as_text=True)
    assert "In Mug" in page
    assert "Out Mug" in page


def test_in_stock_filter(app, client):
    make_product(sku="A", name="In Mug", stock=5)
    make_product(sku="B", name="Out Mug", stock=0)
    page = client.get("/products?in_stock=1").get_data(as_text=True)
    assert "In Mug" in page
    assert "Out Mug" not in page


def test_money_filter_uses_decimal_two_places(app):
    f = app.jinja_env.filters["money"]
    assert f(Decimal("19.99")) == "19.99"
    assert f(Decimal("5")) == "5.00"
    assert f(Decimal("2.345")) == "2.35"
    assert f(None) == "0.00"
    assert f("abc") == "0.00"