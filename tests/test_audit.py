
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.admin.audit import log_event
from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User


def create_test_user(email):
    user = User(
        name="Audit Test User",
        email=email,
        password_hash="test-only-password-hash",
        role="customer"
    )

    db.session.add(user)
    db.session.commit()

    return user


def test_log_event_creates_record(app):
    event_id = log_event(
        "admin_action",
        details={"action": "test"}
    )

    record = db.session.get(AuditLog, event_id)

    assert record is not None
    assert record.event_type == "admin_action"


def test_log_event_records_user_and_actor(app):
    user = create_test_user("audit@test.com")

    event_id = log_event(
        "role_changed",
        user_id=user.id,
        actor_id=user.id,
        details={"new_role": "admin"}
    )

    record = db.session.get(AuditLog, event_id)

    assert record.user_id == user.id
    assert record.actor_id == user.id


def test_log_event_records_details_as_json(app):
    event_id = log_event(
        "admin_action",
        details={"action": "product_created"}
    )

    record = db.session.get(AuditLog, event_id)

    details = json.loads(record.details)

    assert details["action"] == "product_created"


def test_log_event_records_ip_address(app):
    with app.test_request_context(
        "/admin",
        environ_base={"REMOTE_ADDR": "203.0.113.10"}
    ):
        event_id = log_event("admin_action")

    record = db.session.get(AuditLog, event_id)

    assert record.ip_address == "203.0.113.10"


def test_log_event_records_utc_timestamp(app):
    before = datetime.now(timezone.utc).replace(tzinfo=None)

    event_id = log_event("admin_action")

    after = datetime.now(timezone.utc).replace(tzinfo=None)

    record = db.session.get(AuditLog, event_id)

    # SQLite stores DateTime values without timezone information.
    # The application convention is that these naive values represent UTC.
    assert before <= record.created_at <= after


@pytest.mark.parametrize(
    "details",
    [
        {"password": "secret123"},
        {"password_hash": "secret-hash"},
        {"reset_token": "secret-token"},
        {"nested": {"cookie": "secret-cookie"}},
        {"card_number": "4111111111111111"},
        {"csrf_token": "secret-csrf"},
    ]
)
def test_log_event_rejects_sensitive_information(app, details):
    with pytest.raises(ValueError):
        log_event(
            "admin_action",
            details=details
        )


def test_log_event_rejects_details_over_2kb(app):
    details = {
        "description": "A" * 2100
    }

    with pytest.raises(ValueError):
        log_event(
            "admin_action",
            details=details
        )


@pytest.mark.parametrize(
    "event_type",
    [
        "",
        "INVALID EVENT",
        "LOGIN FAILED",
        "a" * 51,
        "login-failed",
    ]
)
def test_log_event_rejects_invalid_event_type(app, event_type):
    with pytest.raises(ValueError):
        log_event(event_type)


def test_log_event_rejects_non_dictionary_details(app):
    with pytest.raises(ValueError):
        log_event(
            "admin_action",
            details="password=secret"
        )


def test_log_event_rejects_invalid_user_id(app):
    with pytest.raises(ValueError):
        log_event(
            "admin_action",
            user_id=-1
        )


def test_log_event_does_not_commit_caller_transaction(app):
    pending_user = User(
        name="Pending User",
        email="pending-audit@test.com",
        password_hash="test-only-password-hash",
        role="customer"
    )

    # Add a user without committing it.
    db.session.add(pending_user)

    event_id = log_event(
        "admin_action",
        details={"action": "transaction_test"}
    )

    # The audit event should be committed independently.
    # The pending user must remain uncommitted.
    with db.engine.connect() as conn:
        saved_user = conn.execute(
            select(User.id).where(
                User.email == "pending-audit@test.com"
            )
        ).scalar_one_or_none()

        saved_event = conn.execute(
            select(AuditLog.id).where(
                AuditLog.id == event_id
            )
        ).scalar_one_or_none()

    assert saved_user is None
    assert saved_event == event_id

    # Clean up the pending user from the test session.
    db.session.rollback()
