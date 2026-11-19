
"""AuditLog database model."""

from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=_utcnow,
        index=True
    )

    event_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    ip_address = db.Column(
        db.String(45),
        nullable=True
    )

    details = db.Column(
        db.Text,
        nullable=True
    )

    def __repr__(self):
        return (
            f"<AuditLog id={self.id} "
            f"event_type={self.event_type!r}>"
        )
