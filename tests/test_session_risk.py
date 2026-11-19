
from datetime import datetime, timezone

from flask import request, session
from flask_login import login_user

from app.extensions import db
from app.models.user import User
from app.admin.session_risk import score_session_risk


def create_test_user():

    user = User(
        name="Risk Test User",
        email="risk-test@example.com",
        password_hash="test-only-password-hash",
        confirmed_at=datetime.now(timezone.utc),
        role="customer"
    )

    db.session.add(user)
    db.session.commit()

    return user


def calculate_score(
    app,
    user,
    fresh=True,
    permanent=True,
    user_agent="TestBrowser/1.0",
    remote_addr="192.0.2.10"
):

    with app.test_request_context(
        "/",
        headers={"User-Agent": user_agent},
        environ_overrides={"REMOTE_ADDR": remote_addr}
    ):

        login_user(user)

        session.permanent = permanent
        session["_fresh"] = fresh

        return score_session_risk(user, request)


def test_normal_session_has_zero_risk(app):

    user = create_test_user()

    score = calculate_score(app, user)

    assert score == 0


def test_non_fresh_session_adds_40_points(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        fresh=False
    )

    assert score == 40


def test_non_permanent_session_adds_15_points(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        permanent=False
    )

    assert score == 15


def test_missing_user_agent_adds_10_points(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        user_agent=""
    )

    assert score == 10


def test_missing_ip_adds_10_points(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        remote_addr=""
    )

    assert score == 10


def test_combined_risk_indicators(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        fresh=False,
        permanent=False,
        user_agent="",
        remote_addr=""
    )

    assert score == 75


def test_unauthenticated_user_has_maximum_risk(app):

    with app.test_request_context("/"):

        score = score_session_risk(None, request)

        assert score == 100


def test_mismatched_session_user_has_maximum_risk(app):

    user = create_test_user()

    with app.test_request_context("/"):

        login_user(user)

        session["_user_id"] = "999999:0"

        score = score_session_risk(user, request)

        assert score == 100


def test_missing_request_context_has_maximum_risk(app):

    user = create_test_user()

    score = score_session_risk(user, None)

    assert score == 100


def test_score_never_exceeds_100(app):

    user = create_test_user()

    score = calculate_score(
        app,
        user,
        fresh=False,
        permanent=False,
        user_agent="",
        remote_addr=""
    )

    assert 0 <= score <= 100
