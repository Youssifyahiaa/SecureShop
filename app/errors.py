"""Generic error pages for 400/403/404/429/500.

Users only ever see a short safe message; details go to the server log.
"""
from flask import render_template

MESSAGES = {
    400: ("Bad request", "The request could not be processed."),
    403: ("Forbidden", "You do not have permission to do that."),
    404: ("Page not found", "The page you asked for does not exist."),
    413: ("Request too large", "The data you sent is too large."),
    429: ("Too many requests", "Please wait a moment and try again."),
    500: ("Something went wrong", "An unexpected error occurred. Please try again later."),
}


def register_error_handlers(app):
    def make_handler(code):
        def handler(error):
            if code == 500:
                from .extensions import db

                db.session.rollback()  # never leave a half-finished transaction behind
                app.logger.exception("Unhandled server error")
            title, message = MESSAGES[code]
            return render_template("errors/error.html", code=code, title=title, message=message), code

        return handler

    for code in MESSAGES:
        app.register_error_handler(code, make_handler(code))
