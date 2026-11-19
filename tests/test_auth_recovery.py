"""Task 4: password reset, session invalidation, role safety, safe redirects, cart on login."""
import logging
import re
from datetime import datetime

import pytest
from flask import Blueprint
from flask_login import login_required

from app import create_app
from app.auth.tokens import make_confirm_token, make_reset_token
from app.config import TEST_CONFIG
from app.extensions import db
from app.models.user import User

GOOD = "correct-horse-battery-staple"
NEW = "purple-elephant-sings-opera"
RESET_SENT = b"If an account exists for that email, a reset link has been sent."
RESET_INVALID = b"This password reset link is invalid or has expired."


# ---------------------------------------------------------------- helpers
def make_user(email="alice@example.com", password=GOOD):
    u = User(name="Alice", email=email)
    u.set_password(password)
    u.confirmed_at = datetime(2020, 1, 1)
    db.session.add(u)
    db.session.commit()
    return u


def login(client, email="alice@example.com", password=GOOD, **kw):
    return client.post("/login", data={"email": email, "password": password}, **kw)


def is_logged_in(client):
    return b"Log out" in client.get("/").data


def request_reset_link(client, caplog, email="alice@example.com"):
    """POST /reset-password and return the reset path written to the dev mail log."""
    caplog.clear()
    client.post("/reset-password", data={"email": email})
    match = re.search(r"(/reset-password/\S+)", " ".join(caplog.messages))
    return match.group(1) if match else None


def set_new_password(client, path, password=NEW, confirm=None):
    return client.post(path, data={"password": password, "confirm_password": confirm or password})


def get_in_fresh_context(app, client, path):
    """GET in a new app context, as a real server does per request.

    The shared test app context keeps Flask-Login's cached user in `g`, which would
    skip the user_loader; a fresh context forces the session cookie to be re-checked.
    """
    with app.app_context():
        return client.get(path)


@pytest.fixture
def mail_log(caplog):
    caplog.set_level(logging.INFO)
    return caplog


@pytest.fixture
def app_with_protected(app):
    """Test-only protected route; never part of production code."""
    test_bp = Blueprint("t4_test", __name__)

    @test_bp.get("/_t4_protected")
    @login_required
    def protected():
        return "secret"

    app.register_blueprint(test_bp)
    return app


# ---------------------------------------------------------------- reset request
def test_reset_request_existing_and_unknown_email_identical(app, mail_log):
    make_user()
    c1, c2 = app.test_client(), app.test_client()
    r1 = c1.post("/reset-password", data={"email": "alice@example.com"})
    r2 = c2.post("/reset-password", data={"email": "nobody@example.com"})
    assert r1.status_code == r2.status_code == 302
    assert r1.headers["Location"] == r2.headers["Location"]
    p1, p2 = c1.get(r1.headers["Location"]).data, c2.get(r2.headers["Location"]).data
    assert p1 == p2 and RESET_SENT in p1
    # Only the real account got a link (in the server log, never on the page).
    links = [m for m in mail_log.messages if "/reset-password/" in m]
    assert len(links) == 1 and "alice@example.com" in links[0]
    assert b"/reset-password/" not in p1


def test_reset_request_page_and_login_link(client):
    assert client.get("/reset-password").status_code == 200
    assert b"/reset-password" in client.get("/login").data


# ---------------------------------------------------------------- reset password
def test_valid_reset_link_changes_password(app, client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    assert client.get(path).status_code == 200
    r = set_new_password(client, path)
    assert r.status_code == 302 and r.headers["Location"] == "/login"
    assert not is_logged_in(client)  # not logged in automatically
    u = db.session.query(User).one()
    assert u.reset_nonce is None and u.session_version == 1
    assert b"Invalid email or password." in login(app.test_client(), password=GOOD).data
    assert login(app.test_client(), password=NEW).status_code == 302


def test_reset_link_single_use(client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    assert set_new_password(client, path).status_code == 302
    r = set_new_password(client, path, password="another-long-passphrase-x")
    assert r.status_code == 400 and RESET_INVALID in r.data
    assert client.get(path).status_code == 400
    assert db.session.query(User).one().check_password(NEW)


def test_second_reset_request_invalidates_first_link(client, mail_log):
    make_user()
    first = request_reset_link(client, mail_log)
    second = request_reset_link(client, mail_log)
    assert first != second
    r = set_new_password(client, first)
    assert r.status_code == 400 and RESET_INVALID in r.data
    assert db.session.query(User).one().check_password(GOOD)
    assert set_new_password(client, second).status_code == 302


def test_expired_reset_token_rejected(app, client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    app.config["RESET_TOKEN_MAX_AGE"] = -1  # every token is already older than this
    r = set_new_password(client, path)
    assert r.status_code == 400 and RESET_INVALID in r.data
    assert db.session.query(User).one().check_password(GOOD)


def test_tampered_reset_token_rejected(client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    bad = path[:-2] + ("AA" if path[-2:] != "AA" else "BB")
    r = set_new_password(client, bad)
    assert r.status_code == 400 and RESET_INVALID in r.data and b"Traceback" not in r.data
    assert client.get("/reset-password/garbage").status_code == 400
    assert db.session.query(User).one().check_password(GOOD)


def test_confirmation_token_cannot_be_used_for_reset(client, mail_log):
    u = make_user()
    request_reset_link(client, mail_log)  # the user has a live nonce
    r = set_new_password(client, f"/reset-password/{make_confirm_token(u.id)}")
    assert r.status_code == 400 and RESET_INVALID in r.data
    assert db.session.get(User, u.id).check_password(GOOD)


def test_reset_token_with_wrong_nonce_or_unknown_user_rejected(client, mail_log):
    u = make_user()
    request_reset_link(client, mail_log)
    for token in (make_reset_token(u.id, "guessed-nonce"), make_reset_token(999, u.reset_nonce)):
        r = set_new_password(client, f"/reset-password/{token}")
        assert r.status_code == 400 and RESET_INVALID in r.data
    assert db.session.get(User, u.id).check_password(GOOD)


@pytest.mark.parametrize("weak", ["Password1234", "short-pw", "x" * 129])
def test_weak_or_common_new_password_rejected(client, mail_log, weak):
    make_user()
    path = request_reset_link(client, mail_log)
    r = set_new_password(client, path, password=weak)
    assert r.status_code == 200
    u = db.session.query(User).one()
    assert u.check_password(GOOD) and u.reset_nonce is not None and u.session_version == 0


def test_mismatched_reset_confirmation_rejected(client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    r = set_new_password(client, path, confirm=NEW + "x")
    assert r.status_code == 200 and b"Passwords must match." in r.data
    assert db.session.query(User).one().check_password(GOOD)


def test_reset_page_sends_no_referrer(client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    assert client.get(path).headers["Referrer-Policy"] == "no-referrer"


# ---------------------------------------------------------------- session versioning
def test_password_reset_kills_existing_session(app_with_protected, mail_log):
    make_user()
    client_a, client_b = app_with_protected.test_client(), app_with_protected.test_client()
    login(client_a)
    assert client_a.get("/_t4_protected").data == b"secret"
    path = request_reset_link(client_b, mail_log)
    assert set_new_password(client_b, path).status_code == 302
    r = get_in_fresh_context(app_with_protected, client_a, "/_t4_protected")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    # Logging in again with the new password works.
    login(client_a, password=NEW)
    assert client_a.get("/_t4_protected").data == b"secret"


@pytest.mark.parametrize("stored", ["1", "1:5", "abc:0", "1:x", "2:0", ""])
def test_session_id_without_matching_version_rejected(app_with_protected, stored):
    make_user()
    client = app_with_protected.test_client()
    login(client)
    assert get_in_fresh_context(app_with_protected, client, "/_t4_protected").data == b"secret"
    with client.session_transaction() as s:  # keeps the real session-protection identifier
        s["_user_id"] = stored
    r = get_in_fresh_context(app_with_protected, client, "/_t4_protected")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_get_id_includes_session_version(app):
    u = make_user()
    assert u.get_id() == f"{u.id}:0"


# ---------------------------------------------------------------- role safety
def test_extra_role_fields_on_register_and_login_change_nothing(client):
    extra = {"role": "admin", "is_admin": "1", "credit_balance": "500", "session_version": "7", "reset_nonce": "x"}
    client.post(
        "/register",
        data={"name": "Alice", "email": "alice@example.com", "password": GOOD, "confirm_password": GOOD, **extra},
    )
    u = db.session.query(User).one()
    assert u.role == "customer" and not u.is_admin and str(u.credit_balance) == "0.00"
    assert u.session_version == 0 and u.reset_nonce is None
    u.confirmed_at = datetime(2020, 1, 1)
    db.session.commit()
    r = client.post("/login", data={"email": "alice@example.com", "password": GOOD, **extra})
    assert r.status_code == 302
    db.session.expire_all()
    u = db.session.query(User).one()
    assert u.role == "customer" and not u.is_admin and str(u.credit_balance) == "0.00"
    assert u.session_version == 0 and u.reset_nonce is None
    with client.session_transaction() as s:
        assert not {"role", "is_admin"} & set(s.keys())


def test_extra_role_fields_on_reset_change_nothing(client, mail_log):
    make_user()
    path = request_reset_link(client, mail_log)
    client.post(path, data={"password": NEW, "confirm_password": NEW, "role": "admin", "is_admin": "1",
                            "session_version": "0", "reset_nonce": "keep"})
    u = db.session.query(User).one()
    assert u.role == "customer" and u.session_version == 1 and u.reset_nonce is None


# ---------------------------------------------------------------- safe redirects
def test_external_next_after_login_goes_home(client):
    make_user()
    r = client.post("/login?next=https://evil.com", data={"email": "alice@example.com", "password": GOOD})
    assert r.status_code == 302 and r.headers["Location"] == "/"


def test_wrong_password_generic_message(client):
    make_user()
    r = login(client, password="wrong-password-here")
    assert r.status_code == 200 and b"Invalid email or password." in r.data
    assert not is_logged_in(client)


# ---------------------------------------------------------------- cart on login
def test_sanitized_guest_cart_survives_login(client):
    make_user()
    with client.session_transaction() as s:
        s["cart"] = {"1": 2, "17": 99}
        s["planted"] = "x"
        s["role"] = "admin"
    login(client)
    with client.session_transaction() as s:
        assert s["cart"] == {"1": 2, "17": 99}
        assert "planted" not in s and "role" not in s


def test_malicious_cart_entries_dropped_on_login(client):
    make_user()
    with client.session_transaction() as s:
        s["cart"] = {"abc": 5, "1": -3, "2": 1000, "3": 0, "4": "5", "5": 2.5, "6": True, "-7": 1, "8": 4}
    login(client)
    with client.session_transaction() as s:
        assert s["cart"] == {"8": 4}


@pytest.mark.parametrize("bad", [["1", 2], "1:2", 42, None, {"abc": 5}, {"1": -3}, {"2": 1000}])
def test_non_dict_or_fully_invalid_cart_dropped(client, bad):
    make_user()
    with client.session_transaction() as s:
        s["cart"] = bad
    login(client)
    with client.session_transaction() as s:
        assert "cart" not in s


def test_cart_capped_at_50_entries(client):
    make_user()
    with client.session_transaction() as s:
        s["cart"] = {str(i): 1 for i in range(1, 81)}
    login(client)
    with client.session_transaction() as s:
        assert len(s["cart"]) == 50


# ---------------------------------------------------------------- rate limit
@pytest.fixture
def limited_app():
    app = create_app({**TEST_CONFIG, "RATELIMIT_ENABLED": True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_rate_limit_reset_request_6th_in_hour_429(limited_app):
    c = limited_app.test_client()
    codes = [c.post("/reset-password", data={"email": "x@example.com"}).status_code for _ in range(6)]
    assert codes[:5] == [302] * 5 and codes[5] == 429
    assert c.get("/reset-password").status_code == 200  # GET is not limited
