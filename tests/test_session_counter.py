"""Session request window counter (app/auth/session_tracking.py)."""
import re
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.auth import session_tracking
from app.extensions import db
from app.models.user import User

GOOD = "correct-horse-battery-staple"
NEW = "purple-elephant-sings-opera"
KEYS = ("req_window_start", "req_count")


def make_user(email="alice@example.com"):
    u = User(name="Alice", email=email)
    u.set_password(GOOD)
    u.confirmed_at = datetime(2020, 1, 1)
    db.session.add(u)
    db.session.commit()
    return u


def login(client, email="alice@example.com", password=GOOD):
    r = client.post("/login", data={"email": email, "password": password})
    assert r.status_code == 302
    return r


def counter(client):
    with client.session_transaction() as s:
        return {k: s[k] for k in KEYS if k in s}


@pytest.fixture
def clock(monkeypatch):
    """Controls only the clock the counter reads; nothing else is affected."""
    state = {"now": 1_000_000.0}
    monkeypatch.setattr(session_tracking, "time", SimpleNamespace(time=lambda: state["now"]))
    return state


def test_counter_increases_across_requests(client, clock):
    make_user()
    login(client)
    assert counter(client) == {}  # the login request itself runs while anonymous
    for expected in (1, 2, 3):
        client.get("/")
        assert counter(client) == {"req_window_start": 1_000_000, "req_count": expected}


def test_counter_resets_after_60_seconds(client, clock):
    make_user()
    login(client)
    client.get("/")
    clock["now"] += 59
    client.get("/")
    assert counter(client) == {"req_window_start": 1_000_000, "req_count": 2}
    clock["now"] += 1  # exactly 60 s after the window started
    client.get("/")
    assert counter(client) == {"req_window_start": 1_000_060, "req_count": 1}


def test_anonymous_requests_do_not_create_keys(client, clock):
    for _ in range(3):
        client.get("/")
    client.get("/login")
    assert counter(client) == {}


def test_static_requests_are_not_counted(client, clock):
    make_user()
    login(client)
    client.get("/")
    client.get("/static/site.css")
    assert counter(client)["req_count"] == 1


def test_keys_gone_after_logout(client, clock):
    make_user()
    login(client)
    client.get("/")
    assert set(counter(client)) == set(KEYS)
    client.post("/logout")
    assert counter(client) == {}
    client.get("/")  # still logged out: nothing recreated
    assert counter(client) == {}


def test_counter_capped_at_10000(client, clock):
    make_user()
    login(client)
    client.get("/")
    with client.session_transaction() as s:
        s["req_count"] = 9999
    client.get("/")
    assert counter(client)["req_count"] == 10000
    client.get("/")
    client.get("/")
    assert counter(client)["req_count"] == 10000


def _reset_password(client, email="alice@example.com"):
    outbox = client.application.extensions.setdefault("dev_outbox", [])
    outbox.clear()
    client.post("/reset-password", data={"email": email})
    path = re.search(r"(/reset-password/\S+)", outbox[-1]["body"]).group(1)
    r = client.post(path, data={"password": NEW, "confirm_password": NEW})
    assert r.status_code == 302


def test_keys_gone_after_password_reset_in_same_session(client, clock):
    make_user()
    login(client)
    client.get("/")
    assert set(counter(client)) == set(KEYS)
    _reset_password(client)
    assert counter(client) == {}


def test_keys_gone_from_other_session_after_password_reset(app, clock):
    make_user()
    victim, other = app.test_client(), app.test_client()
    login(victim)
    victim.get("/")
    assert set(counter(victim)) == set(KEYS)
    _reset_password(other)
    with app.app_context():  # fresh context so the user_loader re-checks session_version
        victim.get("/")
    assert counter(victim) == {}
