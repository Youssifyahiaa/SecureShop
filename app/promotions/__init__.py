"""promotions feature. Owner: Ali.

create_app() registers `bp` automatically.
"""

from flask import Blueprint

bp = Blueprint("promotions", __name__)

from . import routes  # noqa: E402,F401