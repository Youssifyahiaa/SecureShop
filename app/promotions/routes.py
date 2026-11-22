
"""Promotions routes.

Owner: Ali
"""

from flask import flash, redirect, render_template, request, url_for

from app.auth.email import send_email

from . import bp
from .forms import NewsletterForm
from .service import create_newsletter_subscription


@bp.route("/newsletter/subscribe", methods=["GET", "POST"])
def newsletter_subscribe():
    """Handle newsletter subscription requests."""
    form = NewsletterForm()

    if request.method == "POST":
        if not form.validate_on_submit():
            return render_template(
                "promotions/subscribe.html",
                form=form,
            ), 400

        email = form.email.data

        # Returns None when the address is already subscribed.
        coupon = create_newsletter_subscription(email)

        if coupon is not None:
            message = (
                "Welcome to the SecureShop newsletter!\n\n"
                "Thank you for subscribing.\n\n"
                f"Your personal 10% discount code is: {coupon.code}\n\n"
                "This coupon is valid for 7 days and can only "
                "be redeemed by a confirmed SecureShop account "
                "using this email address.\n\n"
                "Thank you,\n"
                "The SecureShop Team"
            )

            send_email(
                to=email,
                subject="Welcome to SecureShop - Your 10% Coupon",
                body=message,
            )

        # Same public response for new and existing subscribers.
        # Never expose coupon codes in the HTTP response.
        flash(
            "If this email is eligible, please check your inbox "
            "for our welcome message.",
            "info",
        )

        return redirect(
            url_for("promotions.newsletter_subscribe")
        )

    return render_template(
        "promotions/subscribe.html",
        form=form,
    )
