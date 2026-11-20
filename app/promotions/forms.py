
"""Newsletter subscription forms.

Owner: Ali
"""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Email, Length


def normalize_email(value):
    """Normalize email input for consistent storage."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


class NewsletterForm(FlaskForm):
    """Validate newsletter signup email addresses."""

    email = StringField(
        "Email address",
        filters=[normalize_email],
        validators=[
            DataRequired(),
            Length(max=255),
            Email(),
        ],
    )
