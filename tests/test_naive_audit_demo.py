"""Isolated comparison of naive and secure audit logging."""

from app.admin.audit import log_event
from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User


def create_pending_user(email):
    """Prepare a user without saving the transaction."""

    return User(
        name="Transaction Demo",
        email=email,
        password_hash="test-only-placeholder",
        role="customer"
    )


def naive_log_event():
    """
    INTENTIONALLY UNSAFE DEMONSTRATION.

    Committing the shared session also commits
    unrelated pending database changes.
    """

    event = AuditLog(
        event_type="admin_action",
        details='{"demo":"naive"}'
    )

    db.session.add(event)

    # This is the vulnerability being demonstrated.
    db.session.commit()


def find_user(email):

    return db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()


def test_naive_logger_commits_unrelated_changes(app):

    email = "naive-audit@example.test"

    # Another operation creates an unfinished user.
    pending_user = create_pending_user(email)

    db.session.add(pending_user)

    # The naive audit logger commits everything.
    naive_log_event()

    # A later rollback cannot undo that commit.
    db.session.rollback()

    persisted_user = find_user(email)

    # Vulnerability reproduced:
    # Unrelated unfinished work was saved.
    assert persisted_user is not None


def test_secure_logger_does_not_commit_unrelated_changes(app):

    email = "secure-audit@example.test"

    # Another operation creates an unfinished user.
    pending_user = create_pending_user(email)

    db.session.add(pending_user)

    # SecureShop's audit service uses its own transaction.
    log_event(
        "admin_action",
        details={"demo": "secure"}
    )

    # The caller decides to cancel its unfinished work.
    db.session.rollback()

    persisted_user = find_user(email)

    # Defense works:
    # The unrelated user was not saved.
    assert persisted_user is None