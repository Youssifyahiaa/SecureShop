from app.extensions import db
from flask import render_template, request
from sqlalchemy import or_, select
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


@bp.get("/users")
@admin_required
def users():

    search = request.args.get("q", "").strip()[:100]

    # Select only fields that administrators are allowed to view.
    # Password hashes and credit balances are deliberately excluded.
    statement = select(
        User.id,
        User.name,
        User.email,
        User.confirmed_at,
        User.role,
        User.created_at
    )

    if search:
        pattern = f"%{search}%"

        statement = statement.where(
            or_(
                User.name.ilike(pattern),
                User.email.ilike(pattern)
            )
        )

    statement = (
        statement
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(100)
    )

    users_list = db.session.execute(statement).all()

    return render_template(
        "admin/users.html",
        users=users_list,
        search=search
    )
