
"""Customer account routes. Owner: Sandy."""
from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.extensions import db
from app.models.order import Order

from . import bp
from .forms import ProfileForm


@bp.get("/")
@login_required
def dashboard():
    """Display the authenticated customer's account dashboard."""

    # Retrieve only this customer's recent orders.
    recent_orders = db.session.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(
            Order.created_at.desc(),
            Order.id.desc()
        )
        .limit(5)
    ).scalars().all()

    # Count only orders belonging to this customer.
    order_count = db.session.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.user_id == current_user.id)
    ) or 0

    return render_template(
        "account/dashboard.html",
        recent_orders=recent_orders,
        order_count=order_count
    )


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update the authenticated customer's profile."""

    form = ProfileForm()

    if form.validate_on_submit():

        current_user.name = form.name.data

        # Commit the profile update first.
        db.session.commit()

        # Record the event using the independent audit transaction.
        try:
            from app.admin.audit import log_event

            log_event(
                "profile_updated",
                user_id=current_user.id,
                details={
                    "changed_fields": ["name"]
                }
            )

        except Exception:
            current_app.logger.exception(
                "Failed to record profile update audit event."
            )

        flash(
            "Your profile has been updated successfully.",
            "success"
        )

        return redirect(url_for("account.profile"))

    if not form.is_submitted():
        form.name.data = current_user.name

    return render_template(
        "account/profile.html",
        form=form
    )
