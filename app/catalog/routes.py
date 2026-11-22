"""Catalog routes: product list and product detail (public, read-only)."""
from flask import abort, render_template, request
from sqlalchemy import select

from app.extensions import db
from app.models.product import Product

from . import bp

MAX_QUERY_LENGTH = 100


def _escape_like(text):
    # Make %, _ and the escape character itself literal inside a LIKE pattern.
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@bp.route("/products")
def product_list():
    # Search text: strip spaces and cap the length (anything longer is cut, not an error).
    q = request.args.get("q", "", type=str).strip()[:MAX_QUERY_LENGTH]
    # Only the exact value "1" turns the filter on; any other value is ignored.
    in_stock = request.args.get("in_stock") == "1"

    stmt = select(Product).where(Product.active.is_(True))
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(Product.name.ilike(pattern, escape="\\"))
    if in_stock:
        stmt = stmt.where(Product.stock > 0)
    stmt = stmt.order_by(Product.name.asc(), Product.id.asc())

    products = db.session.execute(stmt).scalars().all()
    return render_template("catalog/list.html", products=products, q=q, in_stock=in_stock)


@bp.route("/products/<int:product_id>")
def detail(product_id):
    # Only active products are public; anything else looks like it does not exist.
    product = db.session.get(Product, product_id)
    if product is None or not product.active:
        abort(404)
    return render_template("catalog/detail.html", product=product)