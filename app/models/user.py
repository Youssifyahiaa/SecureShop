"""User model. Passwords are stored only as Argon2id encoded hashes."""
from datetime import datetime, timezone
from decimal import Decimal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask_login import UserMixin

from app.extensions import db

ph = PasswordHasher()  # Argon2id with the library's recommended parameters


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (db.CheckConstraint("credit_balance >= 0", name="ck_users_credit_balance_nonneg"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)  # None = unconfirmed
    role = db.Column(db.String(20), nullable=False, default="customer")
    credit_balance = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    # Bumped on password reset: every session cookie issued before that stops working.
    session_version = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    # Current password-reset nonce; None = no reset link is valid. Replaced on each request.
    reset_nonce = db.Column(db.String(64), nullable=True)

    def get_id(self):
        """Session identifier "<id>:<session_version>" (checked by the user_loader)."""
        return f"{self.id}:{self.session_version}"

    def set_password(self, password):
        self.password_hash = ph.hash(password)

    def check_password(self, password):
        try:
            ph.verify(self.password_hash, password)  # VerifyMismatchError is a VerificationError
        except (VerificationError, InvalidHashError, TypeError, ValueError):
            return False
        try:
            if ph.check_needs_rehash(self.password_hash):
                self.password_hash = ph.hash(password)
        except Exception:
            pass
        return True

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    @property
    def is_admin(self):
        return self.role == "admin"
