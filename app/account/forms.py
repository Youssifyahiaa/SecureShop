
"""Forms for customer account management."""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length


def strip_whitespace(value):
    """Remove leading and trailing whitespace."""
    return value.strip() if isinstance(value, str) else value


class ProfileForm(FlaskForm):
    """Validate customer profile updates."""

    name = StringField(
        "Full Name",
        filters=[strip_whitespace],
        validators=[
            DataRequired(message="Name is required."),
            Length(
                max=100,
                message="Name cannot exceed 100 characters."
            )
        ]
    )
