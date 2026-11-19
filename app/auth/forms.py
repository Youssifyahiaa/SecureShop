"""Auth forms (server-side validation)."""
from pathlib import Path

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

# Local screening list of well-known common passwords (NOT a breach-database check).
_COMMON_FILE = Path(__file__).with_name("common_passwords.txt")
COMMON_PASSWORDS = frozenset(
    line.strip().lower() for line in _COMMON_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
)


def _normalize_email(value):
    return value.strip().lower() if isinstance(value, str) else value


def _strip(value):
    return value.strip() if isinstance(value, str) else value


def not_common_password(form, field):
    if field.data and field.data.lower() in COMMON_PASSWORDS:
        raise ValidationError("This password is too common. Please choose a different one.")


class LoginForm(FlaskForm):
    email = StringField("Email", filters=[_normalize_email], validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=MAX_PASSWORD_LENGTH)])


def _new_password_validators():
    """Password policy shared by registration and password reset."""
    return [
        DataRequired(),
        Length(
            min=MIN_PASSWORD_LENGTH,
            max=MAX_PASSWORD_LENGTH,
            message=f"Password must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters.",
        ),
        not_common_password,
    ]


class RegistrationForm(FlaskForm):
    name = StringField("Name", filters=[_strip], validators=[DataRequired(), Length(max=100)])
    email = StringField(
        "Email",
        filters=[_normalize_email],
        validators=[DataRequired(), Length(max=255), Email()],
    )
    password = PasswordField("Password", validators=_new_password_validators())
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class ResetRequestForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[_normalize_email],
        validators=[DataRequired(), Length(max=255), Email()],
    )


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New password", validators=_new_password_validators())
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
