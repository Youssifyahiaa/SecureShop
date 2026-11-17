"""catalog feature. Owner: Mark.

create_app() registers `bp` automatically. Keep the variable name `bp` and
the blueprint name "catalog"; add your routes in this package (e.g. routes.py)
and import them at the bottom of this file:  from . import routes  # noqa
You may set url_prefix here if your routes need one.
"""
from flask import Blueprint

bp = Blueprint("catalog", __name__)
