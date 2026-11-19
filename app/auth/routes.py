import hmac
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import flash, make_response, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models.user import User

from . import bp
from .email import send_confirmation_email, send_password_reset_email
from .forms import LoginForm, RegistrationForm, ResetPasswordForm, ResetRequestForm
from .tokens import make_confirm_token, make_reset_token, read_confirm_token, read_reset_token

_GENERIC = "If this email can be used, you will receive a confirmation email."
_BAD_LOGIN = "Invalid email or password."
_UNCONFIRMED = "Please confirm your email before logging in."
_RESET_SENT = "If an account exists for that email, a reset link has been sent."
_RESET_INVALID = "This password reset link is invalid or has expired. Please request a new one."
_RESET_DONE = "Your password has been changed. Please log in with your new password."

# Guest cart kept across login (agreed with the cart owner): {"<product id>": quantity}.
CART_MAX_ENTRIES = 50
CART_MAX_QTY = 99
_PRODUCT_ID = re.compile(r"[0-9]{1,10}")  # ASCII digits only (str.isdigit() also accepts e.g. "²")


def _safe_next(target):
    """Allow only relative paths on this site."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


def redirect_to_next(default_endpoint="main.home"):
    """The single place auth follows a user-supplied ?next= target (open-redirect safe)."""
    return redirect(_safe_next(request.args.get("next")) or url_for(default_endpoint))


def _sanitize_cart(raw):
    """Return a clean copy of a guest cart; anything unexpected is dropped."""
    if not isinstance(raw, dict):
        return {}
    clean = {}
    for key, qty in raw.items():
        if len(clean) >= CART_MAX_ENTRIES:
            break
        if not isinstance(key, str) or not _PRODUCT_ID.fullmatch(key):
            continue
        if type(qty) is not int or not 1 <= qty <= CART_MAX_QTY:  # rejects bool, float, str
            continue
        clean[key] = qty
    return clean


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
        guest_cart = _sanitize_cart(session.get("cart"))  # the only key carried over
        session.clear()  # prevent session fixation
        if guest_cart:
            session["cart"] = guest_cart
        login_user(user)
        session.permanent = True
        return redirect_to_next()
    if request.method == "POST" and "csrf_token" not in form.errors:
        flash(_BAD_LOGIN)  # e.g. empty fields: same generic message
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("main.home"))


@bp.route("/reset-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def reset_request():
    form = ResetRequestForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(email=form.email.data)).scalar_one_or_none()
        if user is not None:
            user.reset_nonce = secrets.token_urlsafe(32)  # also invalidates any older reset link
            db.session.commit()
            token = make_reset_token(user.id, user.reset_nonce)
            send_password_reset_email(user, url_for("auth.reset_password", token=token, _external=True))
        # Identical response whether or not the account exists.
        flash(_RESET_SENT)
        return redirect(url_for("auth.reset_request"))
    return render_template("auth/reset_request.html", form=form)


def _user_for_reset_token(token):
    """Return the user a reset token is valid for, or None (all failures look the same)."""
    data = read_reset_token(token)
    if data is None:
        return None
    uid, nonce = data
    user = db.session.get(User, uid)
    if user is None or not user.reset_nonce:
        return None
    if not hmac.compare_digest(user.reset_nonce.encode(), nonce.encode()):
        return None
    return user


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = _user_for_reset_token(token)
    if user is None:
        html, status = render_template("auth/reset_password.html", form=None, invalid_message=_RESET_INVALID), 400
    else:
        form = ResetPasswordForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            user.reset_nonce = None  # single use
            user.session_version += 1  # logs out every existing session for this user
            db.session.commit()
            flash(_RESET_DONE)
            return redirect(url_for("auth.login"))  # never logged in automatically
        html, status = render_template("auth/reset_password.html", form=form, token=token), 200
    response = make_response(html, status)
    response.headers["Referrer-Policy"] = "no-referrer"  # the URL contains the reset token
    return response
