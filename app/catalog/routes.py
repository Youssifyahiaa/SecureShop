"""Catalog routes: product list and product detail (public, read-only)."""
from flask import abort, render_template

from app.extensions import db
from app.models.product import Product

from . import bp


@bp.route("/products/<int:product_id>")
def detail(product_id):
    # Only active products are public; anything else looks like it does not exist.
    product = db.session.get(Product, product_id)
    if product is None or not product.active:
        abort(404)
    return render_template("catalog/detail.html", product=product)