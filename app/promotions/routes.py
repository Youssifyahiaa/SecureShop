
"""Promotions routes.

Owner: Ali
"""

from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from app.auth.email import send_email
from app.extensions import db, limiter
from app.models.promotion import Coupon, NewsletterSubscriber

from . import bp

from .forms import NewsletterForm, NewsletterConfirmForm
from .service import create_newsletter_subscription
from .tokens import (
    make_newsletter_confirm_token,
    read_newsletter_confirm_token,
)




@bp.route("/newsletter/subscribe", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
def newsletter_subscribe():
    """Request email confirmation before newsletter registration."""

    form = NewsletterForm()

    if request.method == "POST":
        if not form.validate_on_submit():
            return render_template(
                "promotions/subscribe.html",
                form=form,
            ), 400

        email = form.email.data

        # Avoid sending another confirmation email
        # to an already subscribed address.
        existing = db.session.scalar(
            select(NewsletterSubscriber.id).where(
                NewsletterSubscriber.email == email
            )
        )

        if existing is None:
            token = make_newsletter_confirm_token(email)

            confirmation_url = url_for(
                "promotions.newsletter_confirm",
                token=token,
                _external=True,
            )

            message = (
                "Welcome to SecureShop!\n\n"
                "Please confirm your email address to "
                "subscribe to our newsletter.\n\n"
                f"Confirmation link: {confirmation_url}\n\n"
                "This link expires in 24 hours.\n\n"
                "After confirmation, you will receive "
                "your personal 10% discount coupon.\n\n"
                "If you did not request this, "
                "you can safely ignore this email."
            )

            send_email(
                to=email,
                subject="Confirm your SecureShop newsletter subscription",
                body=message,
            )

        # Do not reveal whether an email is already subscribed.
        flash(
            "If this email is eligible, please check "
            "your inbox for a confirmation link.",
            "info",
        )

        return redirect(
            url_for("promotions.newsletter_subscribe")
        )

    return render_template(
        "promotions/subscribe.html",
        form=form,
    )


@bp.route("/newsletter/confirm/<token>", methods=["GET", "POST"])
def newsletter_confirm(token):
    """Complete newsletter signup only after explicit confirmation."""

    email = read_newsletter_confirm_token(token)

    if email is None:
        return (
            "This newsletter confirmation link is invalid or expired.",
            400,
        )

    form = NewsletterConfirmForm()

    if request.method == "GET":
        response = render_template(
            "promotions/confirm.html",
            form=form,
        )

        from flask import make_response

        response = make_response(response)
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"

        return response

    if not form.validate_on_submit():
        return "Invalid confirmation request.", 400

    # Only a valid, explicit POST can create a subscription.
    # Returns None if already subscribed.

    # Create a subscriber and coupon only if this email is new.
    # Existing subscribers keep their original coupon.
    create_newsletter_subscription(email)

    subscriber = db.session.scalar(
        select(NewsletterSubscriber).where(
            NewsletterSubscriber.email == email
        )
    )

    if (
        subscriber is not None
        and subscriber.coupon_email_status in ("pending", "failed")
        and subscriber.coupon_email_attempts < 3
    ):
        coupon = db.session.get(Coupon, subscriber.coupon_id)

        message = (
            "Welcome to the SecureShop newsletter!\n\n"
            "Your email has been confirmed.\n\n"
            f"Your personal 10% discount code is: {coupon.code}\n\n"
            "Your coupon expires 7 days after issuance.\n"
            "It can only be used once by a confirmed "
            "SecureShop account with this email address.\n\n"
            "Thank you,\n"
            "The SecureShop Team"
        )

        # The shared email helper returns False when it saves
        # to the development outbox, even though saving succeeded.
        is_dev_mode = (
            current_app.config.get("MAIL_DEV_LOG_ONLY")
            or not current_app.config.get("MAIL_SERVER")
        )

        try:
            smtp_accepted = send_email(
                to=email,
                subject="SecureShop - Your 10% Welcome Coupon",
                body=message,
            )
        except Exception:
            # Do not log the coupon code or email body.
            current_app.logger.error(
                "Newsletter coupon email delivery failed."
            )
            status = "failed"
        else:
            if smtp_accepted:
                status = "smtp_accepted"
            elif is_dev_mode:
                status = "dev_saved"
            else:
                status = "failed"

        subscriber.coupon_email_attempts += 1
        subscriber.coupon_email_status = status

        db.session.commit()

    # Always use a generic public response.
    flash(
        "Your newsletter confirmation has been processed. "
        "Please check your email.",
        "info",
    )

    return redirect(
        url_for("promotions.newsletter_subscribe")
    )
