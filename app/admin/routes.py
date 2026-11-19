from flask import render_template

from app.models.user import User
from app.admin import bp
from app.admin.decorators import admin_required


@bp.get("/")
@admin_required
def dashboard():

    total_users = User.query.count()

    confirmed_users = User.query.filter(
        User.confirmed_at.isnot(None)
    ).count()

    admin_users = User.query.filter_by(
        role="admin"
    ).count()

    stats = {
        "total_users": total_users,
        "confirmed_users": confirmed_users,
        "admin_users": admin_users
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats
    )