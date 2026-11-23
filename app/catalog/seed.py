"""Idempotent demo data for the catalog.

Run from the project root (venv active):   python -m app.catalog.seed
Safe to run many times: a product is added only if its SKU does not exist yet.
"""
from decimal import Decimal

from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models.product import Product

SEED_PRODUCTS = [
    {
        "sku": "MUG-001",
        "name": "Ceramic Coffee Mug",
        "description": "350 ml ceramic mug, dishwasher safe.",
        "price": Decimal("149.99"),
        "stock": 25,
    },
    {
        "sku": "BOTTLE-001",
        "name": "Insulated Water Bottle",
        "description": "750 ml stainless steel bottle, keeps drinks cold for 24 hours.",
        "price": Decimal("299.50"),
        "stock": 40,
    },
    {
        "sku": "NOTE-001",
        "name": "Hardcover Notebook",
        "description": "A5 hardcover notebook, 200 ruled pages.",
        "price": Decimal("89.00"),
        "stock": 60,
    },
    {
        "sku": "BAG-001",
        "name": "Canvas Backpack",
        "description": "20 L canvas backpack with a padded laptop pocket.",
        "price": Decimal("649.00"),
        "stock": 12,
    },
    {
        "sku": "CABLE-001",
        "name": "USB-C Charging Cable",
        "description": "1 m braided USB-C cable. Currently sold out.",
        "price": Decimal("79.95"),
        "stock": 0,
    },
]


def seed_products():
    """Insert missing products; return how many were added."""
    added = 0
    for data in SEED_PRODUCTS:
        exists = db.session.execute(
            select(Product.id).where(Product.sku == data["sku"])
        ).scalar_one_or_none()
        if exists is not None:
            continue
        db.session.add(Product(active=True, **data))
        added += 1
    db.session.commit()
    return added


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        count = seed_products()
        print(f"Seed done: {count} product(s) added.")