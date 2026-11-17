"""Shared Flask extensions.

Every module imports the extension objects from here, e.g.
    from app.extensions import db, login_manager, csrf, limiter

They are created without an app and attached to it in create_app()
(app factory pattern), which avoids circular imports.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
# Rate limiter shared by the whole team. Apply limits per route, e.g.
#   @limiter.limit("5 per minute")
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User  # imported here to avoid a circular import

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
