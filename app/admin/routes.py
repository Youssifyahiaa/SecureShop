from flask import render_template, request
from sqlalchemy import func, or_, select

from app.extensions import db
from app.models.user import User
from app.models.audit_log import AuditLog
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

@bp.get("/audit-logs")
@admin_required
def audit_logs():

    search = request.args.get("q", "").strip()[:100]

    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)

    per_page = 25

    filters = []

    if search:
        pattern = f"%{search}%"

        filters.append(
            or_(
                AuditLog.event_type.ilike(pattern),
                AuditLog.ip_address.ilike(pattern)
            )
        )

    total = db.session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(*filters)
    ) or 0

    total_pages = max(
        (total + per_page - 1) // per_page,
        1
    )

    page = min(page, total_pages)

    logs = db.session.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc()
        )
        .limit(per_page)
        .offset((page - 1) * per_page)
    ).scalars().all()

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        search=search,
        page=page,
        total_pages=total_pages,
        total=total
    )
