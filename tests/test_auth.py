from sqlalchemy import text

from app.extensions import db
from app.models.user import User

GOOD = "correct-horse-battery-staple"


def post(client, **over):
    data = {"name": "Alice", "email": "alice@example.com", "password": GOOD, "confirm_password": GOOD}
    data.update(over)
    return client.post("/register", data=data)


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
    assert "If this email can be used" in client.get("/").get_data(as_text=True)


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
