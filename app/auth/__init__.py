"""auth feature. Owner: Youssef.

create_app() registers `bp` automatically. Keep the variable name `bp` and
the blueprint name "auth"; add your routes in this package (e.g. routes.py)
and import them at the bottom of this file:  from . import routes  # noqa
You may set url_prefix here if your routes need one.
"""
from flask import Blueprint

bp = Blueprint("auth", __name__)

from . import routes  # noqa: E402,F401
from . import session_tracking  # noqa: E402,F401
