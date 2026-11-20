
"""Promotions routes.

Owner: Ali
"""

from flask import render_template, request

from . import bp
from .forms import NewsletterForm


@bp.route("/newsletter/subscribe", methods=["GET", "POST"])
def newsletter_subscribe():
    """Display and validate newsletter subscription requests."""
    form = NewsletterForm()

    if request.method == "POST":
        if not form.validate_on_submit():
            return render_template(
                "promotions/subscribe.html",
                form=form,
            ), 400

        # Subscription processing will be implemented next.
        # Do not claim success or create coupons yet.
        return "Newsletter subscriptions are not available yet.", 503

    return render_template(
        "promotions/subscribe.html",
        form=form,
    )
