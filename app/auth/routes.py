from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models.user import User

from . import bp
from .email import send_confirmation_email
from .forms import LoginForm, RegistrationForm
from .tokens import make_confirm_token, read_confirm_token

_GENERIC = "If this email can be used, you will receive a confirmation email."
_BAD_LOGIN = "Invalid email or password."
_UNCONFIRMED = "Please confirm your email before logging in."


def _safe_next(target):
    """Allow only relative paths on this site."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        if not db.session.execute(db.select(User.id).filter_by(email=email)).first():
            # Only name, email and password come from the request; everything else is server-set.
            user = User(name=form.name.data, email=email, role="customer")
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            else:
                token = make_confirm_token(user.id)
                send_confirmation_email(user, url_for("auth.confirm_email", token=token, _external=True))
        # Identical response whether or not the email already existed.
        flash(_GENERIC)
        return redirect(url_for("main.home"))
    return render_template("auth/register.html", form=form)


@bp.get("/confirm/<token>")
def confirm_email(token):
    uid = read_confirm_token(token)
    user = db.session.get(User, uid) if uid is not None else None
    if user is None:
        return render_template(
            "auth/confirm_result.html",
            message="This confirmation link is invalid or has expired.",
        ), 400
    if user.confirmed_at is None:
        user.confirmed_at = datetime.now(timezone.utc)
        db.session.commit()
        message = "Your email has been confirmed. You can now log in."
    else:
        message = "This link has already been used. You can log in."
    return render_template("auth/confirm_result.html", message=message)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(email=form.email.data)).scalar_one_or_none()
        if user is None or not user.check_password(form.password.data):
            flash(_BAD_LOGIN)
            return render_template("auth/login.html", form=form)
        if not user.is_confirmed:  # only reached after the password was correct
            flash(_UNCONFIRMED)
            return render_template("auth/login.html", form=form)
        db.session.commit()  # persists a possible password rehash
        next_url = _safe_next(request.args.get("next"))
        session.clear()  # prevent session fixation
        login_user(user)
        session.permanent = True
        return redirect(next_url or url_for("main.home"))
    if request.method == "POST" and "csrf_token" not in form.errors:
        flash(_BAD_LOGIN)  # e.g. empty fields: same generic message
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("main.home"))
