from flask import flash, redirect, render_template, url_for
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.user import User

from . import bp
from .forms import RegistrationForm

_CREATED = "Account created. Please check your email to confirm your account."
_GENERIC = "If this email can be used, you will receive a confirmation email."


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        if db.session.execute(db.select(User.id).filter_by(email=email)).first():
            flash(_GENERIC)
            return redirect(url_for("main.home"))
        # Only name, email and password come from the request; everything else is server-set.
        user = User(name=form.name.data, email=email, role="customer")
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_GENERIC)
            return redirect(url_for("main.home"))
        flash(_CREATED)
        return redirect(url_for("main.home"))
    return render_template("auth/register.html", form=form)
