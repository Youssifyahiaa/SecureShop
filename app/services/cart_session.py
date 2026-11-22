"""Session cart helpers shared by login (cart carried across login) and checkout.

The session cart format (agreed with the cart owner) is {"<product id>": quantity}.
Only ids and quantities are ever stored there; prices are always read from the DB.
"""
import re

CART_MAX_ENTRIES = 50
CART_MAX_QTY = 99
_PRODUCT_ID = re.compile(r"[0-9]{1,10}")  # ASCII digits only (str.isdigit() also accepts e.g. "²")


def sanitize_cart(raw):
    """Return a clean copy of a session cart; anything unexpected is dropped."""
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, qty in raw.items():
        if len(clean) >= CART_MAX_ENTRIES:
            break
        if not isinstance(key, str) or not _PRODUCT_ID.fullmatch(key):
            continue
        if type(qty) is not int or not 1 <= qty <= CART_MAX_QTY:  # rejects bool, float, str
            continue
        clean[key] = qty
    return clean
