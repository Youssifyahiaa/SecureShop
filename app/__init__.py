"""SecureShop application factory.

Run (development only):   flask --app app run --debug
Tests:                    python -m pytest -q
"""
import os

from flask import Flask

from .config import Config

# The seven feature blueprints. Each package app/<name>/__init__.py exposes `bp`.
# Owners: auth/checkout = Youssef, catalog/cart = Mark, promotions = Ali,
#         account/admin = Sandy. Edit your own package only.
FEATURE_BLUEPRINTS = ("auth", "catalog", "cart", "promotions", "checkout", "account", "admin")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # 1) Load configuration (environment first, then test overrides).
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and set a random value.")

    os.makedirs(app.instance_path, exist_ok=True)

    # 2) Initialise extensions (imported here to avoid circular imports).
    from .extensions import csrf, db, limiter, login_manager, migrate

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    # 3) Register blueprints: the home page plus the seven features.
    from importlib import import_module

    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    for name in FEATURE_BLUEPRINTS:
        module = import_module(f"{__name__}.{name}")
        app.register_blueprint(module.bp)

    # 4) Safe error pages (no tracebacks or internal details shown to users).
    from .errors import register_error_handlers

    register_error_handlers(app)

    return app
