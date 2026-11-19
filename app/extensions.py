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
    """Load a user from the "<id>:<session_version>" value stored in the session.

    A session created before the user's last password reset carries an old
    version and is rejected, so the browser is treated as logged out.
    """
    from app.models.user import User  # imported here to avoid a circular import

    try:
        raw_id, raw_version = str(user_id).split(":", 1)
        uid, version = int(raw_id), int(raw_version)
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, uid)
    if user is None or user.session_version != version:
        return None
    return user
