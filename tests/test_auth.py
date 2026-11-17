import logging
import re
from datetime import datetime

import pytest
from flask import Blueprint
from flask_login import login_required
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import text

from app import create_app
from app.auth.tokens import make_confirm_token
from app.config import TEST_CONFIG
from app.extensions import db
from app.models.user import User

GOOD = "correct-horse-battery-staple"


def reg_data(**over):
    data = {"name": "Alice", "email": "alice@example.com", "password": GOOD, "confirm_password": GOOD}
    data.update(over)
    return data


def post(client, **over):
    return client.post("/register", data=reg_data(**over))


def count():
    return db.session.query(User).count()


def test_valid_registration_creates_unconfirmed_customer(client):
    r = post(client)
    assert r.status_code == 302
    assert count() == 1
    u = db.session.query(User).one()
    assert u.email == "alice@example.com"
    assert u.role == "customer" and not u.is_confirmed and not u.is_admin
    assert str(u.credit_balance) == "0.00"


def test_duplicate_email_does_not_create_second_user(client):
    post(client)
    r = post(client, email="  ALICE@Example.com ", name="Mallory")
    assert r.status_code == 302
    assert count() == 1
    assert db.session.query(User).one().name == "Alice"


def test_register_new_and_existing_email_responses_identical(app):
    c1, c2 = app.test_client(), app.test_client()
    new = c1.post("/register", data=reg_data(email="new@example.com"))
    assert count() == 1
    existing = c2.post("/register", data=reg_data(email="new@example.com", name="Other"))
    assert count() == 1
    assert new.status_code == existing.status_code == 302
    assert new.headers["Location"] == existing.headers["Location"]
    page1 = c1.get("/").get_data(as_text=True)
    page2 = c2.get("/").get_data(as_text=True)
    assert page1 == page2
    assert "If this email can be used, you will receive a confirmation email." in page1
    assert "Account created" not in page1


def test_short_password_rejected(client):
    r = post(client, password="Short1!xyz", confirm_password="Short1!xyz")
    assert r.status_code == 200 and count() == 0


def test_common_password_rejected(client):
    r = post(client, password="Password1234", confirm_password="Password1234")
    assert r.status_code == 200 and count() == 0
    assert b"too common" in r.data


def test_mismatched_confirmation_rejected(client):
    r = post(client, confirm_password=GOOD + "x")
    assert r.status_code == 200 and count() == 0


def test_extra_fields_ignored(client):
    post(client, role="admin", credit_balance="9999", confirmed_at="2020-01-01", id="42")
    u = db.session.query(User).one()
    assert u.role == "customer" and str(u.credit_balance) == "0.00"
    assert u.confirmed_at is None and u.id != 42


def test_plaintext_password_not_stored(client):
    post(client)
    row = db.session.execute(text("select * from users")).mappings().one()
    assert all(GOOD not in str(v) for v in row.values())


def test_hashes_differ_and_are_argon2id(app):
    a, b = User(name="a", email="a@x.com"), User(name="b", email="b@x.com")
    a.set_password(GOOD)
    b.set_password(GOOD)
    assert a.password_hash != b.password_hash
    assert a.password_hash.startswith("$argon2id$") and b.password_hash.startswith("$argon2id$")


def test_check_password(app):
    u = User(name="a", email="a@x.com")
    u.set_password(GOOD)
    assert u.check_password(GOOD) is True
    assert u.check_password("wrong-password-here") is False
    u.password_hash = "not-a-hash"
    assert u.check_password(GOOD) is False


# ---------------------------------------------------------------- Task 3
@pytest.fixture
def app_with_protected(app):
    """Test-only protected route; never part of production code."""
    test_bp = Blueprint("t3_test", __name__)

    @test_bp.get("/_protected")
    @login_required
    def protected():
        return "secret"

    app.register_blueprint(test_bp)
    return app


def make_user(confirmed=True, email="alice@example.com"):
    u = User(name="Alice", email=email)
    u.set_password(GOOD)
    if confirmed:
        u.confirmed_at = datetime(2020, 1, 1)
    db.session.add(u)
    db.session.commit()
    return u


def login(client, email="alice@example.com", password=GOOD, **kw):
    return client.post("/login", data={"email": email, "password": password}, **kw)


def test_unconfirmed_user_cannot_login(client):
    make_user(confirmed=False)
    r = login(client)
    assert r.status_code == 200
    assert b"Please confirm your email before logging in." in r.data
    with client.session_transaction() as s:
        assert "_user_id" not in s


def test_unconfirmed_message_not_shown_for_wrong_password(client):
    make_user(confirmed=False)
    r = login(client, password="wrong-password-here")
    assert b"Invalid email or password." in r.data
    assert b"confirm your email" not in r.data


def test_registration_logs_link_but_page_does_not(client, caplog):
    caplog.set_level(logging.INFO)
    r = client.post("/register", data=reg_data(), follow_redirects=True)
    assert b"/confirm/" not in r.data
    assert "delivered" not in r.get_data(as_text=True).lower()
    logged = [m for m in caplog.messages if m.startswith("[DEV MAIL]")]
    assert len(logged) == 1 and "/confirm/" in logged[0]


def test_valid_token_confirms_account(client, caplog):
    caplog.set_level(logging.INFO)
    client.post("/register", data=reg_data())
    path = re.search(r"(/confirm/\S+)", " ".join(caplog.messages)).group(1)
    r = client.get(path)
    assert r.status_code == 200
    assert db.session.query(User).one().is_confirmed
    assert login(client).status_code == 302


def test_expired_token_rejected(app, client):
    u = make_user(confirmed=False)
    token = make_confirm_token(u.id)
    app.config["CONFIRM_TOKEN_MAX_AGE"] = -1  # every token is already older than this
    r = client.get(f"/confirm/{token}")
    assert r.status_code == 400 and b"invalid or has expired" in r.data
    assert db.session.get(User, u.id).confirmed_at is None


def test_tampered_token_rejected(client):
    u = make_user(confirmed=False)
    token = make_confirm_token(u.id)
    bad = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    r = client.get(f"/confirm/{bad}")
    assert r.status_code == 400 and b"Traceback" not in r.data
    assert client.get("/confirm/garbage").status_code == 400
    assert db.session.get(User, u.id).confirmed_at is None


def test_wrong_purpose_or_salt_rejected(app, client):
    u = make_user(confirmed=False)
    key = app.config["SECRET_KEY"]
    other_salt = URLSafeTimedSerializer(key, salt="other").dumps({"uid": u.id, "purpose": "confirm_email"})
    other_purpose = URLSafeTimedSerializer(key, salt="email-confirm").dumps({"uid": u.id, "purpose": "reset"})
    assert client.get(f"/confirm/{other_salt}").status_code == 400
    assert client.get(f"/confirm/{other_purpose}").status_code == 400
    assert db.session.get(User, u.id).confirmed_at is None


def test_reused_token_does_not_change_confirmed_at(client):
    u = make_user(confirmed=False)
    token = make_confirm_token(u.id)
    assert client.get(f"/confirm/{token}").status_code == 200
    first = db.session.get(User, u.id).confirmed_at
    assert first is not None
    r = client.get(f"/confirm/{token}")
    assert r.status_code == 200 and b"already been used" in r.data
    assert db.session.get(User, u.id).confirmed_at == first


def test_good_login_works(client):
    make_user()
    r = login(client)
    assert r.status_code == 302 and r.headers["Location"] == "/"
    assert b"Log out" in client.get("/").data


def test_wrong_password_and_unknown_email_identical(app):
    make_user()
    r1 = login(app.test_client(), password="wrong-password-here")
    r2 = login(app.test_client(), email="nobody@example.com")
    assert r1.status_code == r2.status_code == 200
    # The form re-displays the typed email; apart from that echo the pages must be identical.
    assert r1.data.replace(b"alice@example.com", b"X") == r2.data.replace(b"nobody@example.com", b"X")
    assert b"Invalid email or password." in r1.data


@pytest.mark.parametrize(
    "target", ["https://evil.com/x", "//evil.com", "http://evil.com", "/\\evil.com", "javascript:alert(1)"]
)
def test_external_next_ignored(client, target):
    make_user()
    r = client.post("/login", query_string={"next": target}, data={"email": "alice@example.com", "password": GOOD})
    assert r.status_code == 302 and r.headers["Location"] == "/"


def test_relative_next_followed(client):
    make_user()
    r = client.post("/login?next=/_protected", data={"email": "alice@example.com", "password": GOOD})
    assert r.headers["Location"] == "/_protected"


def test_login_clears_old_session_and_is_permanent(client):
    make_user()
    with client.session_transaction() as s:
        s["planted"] = "x"
    login(client)
    with client.session_transaction() as s:
        assert "planted" not in s and s.permanent


def test_logout_post_only_then_protected_redirects(app_with_protected):
    client = app_with_protected.test_client()
    make_user()
    login(client)
    assert client.get("/_protected").data == b"secret"
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    r = client.get("/_protected")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_logout_requires_login(client):
    r = client.post("/logout")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_logout_requires_csrf():
    app = create_app({**TEST_CONFIG, "WTF_CSRF_ENABLED": True})
    with app.app_context():
        db.create_all()
        make_user()
        c = app.test_client()
        with c.session_transaction() as s:
            s["_user_id"] = "1"
            s["_fresh"] = True
        assert c.post("/logout").status_code == 400
        db.session.remove()
        db.drop_all()


def test_navbar_links_when_anonymous(client):
    page = client.get("/").data
    assert b"/login" in page and b"/register" in page and b"Log out" not in page


def test_rate_limit_login_6th_attempt_429():
    app = create_app({**TEST_CONFIG, "RATELIMIT_ENABLED": True})
    with app.app_context():
        db.create_all()
        c = app.test_client()
        codes = [login(c, password="wrong-password-here").status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429
        assert b"Too many requests" in login(c).data
        db.session.remove()
        db.drop_all()
