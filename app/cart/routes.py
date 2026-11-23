"""Cart routes. The session cart is {"<product id>": quantity} and nothing else.

Prices, totals and stock are always read from the database. This module never
changes stock (only the checkout transaction does that).
"""
import re

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.product import Product
from app.services.cart_session import CART_MAX_ENTRIES, CART_MAX_QTY, sanitize_cart
from app.services.checkout_service import calculate_cart

from . import bp

_QTY = re.compile(r"[0-9]{1,3}")  # ASCII digits only


def _get_cart():
    cart = sanitize_cart(session.get("cart"))
    session["cart"] = cart
    return cart


def _parse_qty(raw):
    """Return an int 1..CART_MAX_QTY, or None if the value is not acceptable."""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    if not _QTY.fullmatch(raw):
        return None
    qty = int(raw)
    if not 1 <= qty <= CART_MAX_QTY:
        return None
    return qty


def _active_product_or_none(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.active:
        return None
    return product


@bp.route("/cart")
def view_cart():
    cart = _get_cart()
    result = calculate_cart(None, cart)
    return render_template("cart/cart.html", result=result)


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add(product_id):
    qty = _parse_qty(request.form.get("quantity", "1"))
    if qty is None:
        flash(f"Quantity must be a whole number from 1 to {CART_MAX_QTY}.")
        return redirect(url_for("cart.view_cart"))

    product = _active_product_or_none(product_id)
    if product is None:
        flash("That product is not available.")
        return redirect(url_for("cart.view_cart"))
    if product.stock <= 0:
        flash(f"{product.name} is out of stock.")
        return redirect(url_for("cart.view_cart"))

    cart = _get_cart()
    key = str(product.id)
    if key not in cart and len(cart) >= CART_MAX_ENTRIES:
        flash("Your cart is full.")
        return redirect(url_for("cart.view_cart"))

    new_qty = cart.get(key, 0) + qty
    if new_qty > CART_MAX_QTY:
        flash(f"You can order at most {CART_MAX_QTY} of one item.")
        return redirect(url_for("cart.view_cart"))
    if new_qty > product.stock:
        flash(f"Only {product.stock} left of {product.name}")
        return redirect(url_for("cart.view_cart"))

    cart[key] = new_qty
    session["cart"] = cart
    session.modified = True
    flash(f"Added {product.name} to your cart.")
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update(product_id):
    qty = _parse_qty(request.form.get("quantity"))
    if qty is None:
        flash(f"Quantity must be a whole number from 1 to {CART_MAX_QTY}.")
        return redirect(url_for("cart.view_cart"))

    cart = _get_cart()
    key = str(product_id)
    if key not in cart:
        flash("That item is not in your cart.")
        return redirect(url_for("cart.view_cart"))

    product = _active_product_or_none(product_id)
    if product is None:
        flash("That product is not available.")
        return redirect(url_for("cart.view_cart"))
    if qty > product.stock:
        flash(f"Only {product.stock} left of {product.name}")
        return redirect(url_for("cart.view_cart"))

    cart[key] = qty
    session["cart"] = cart
    session.modified = True
    flash("Cart updated.")
    return redirect(url_for("cart.view_cart"))


@bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove(product_id):
    cart = _get_cart()
    cart.pop(str(product_id), None)
    session["cart"] = cart
    session.modified = True
    flash("Item removed from your cart.")
    return redirect(url_for("cart.view_cart"))