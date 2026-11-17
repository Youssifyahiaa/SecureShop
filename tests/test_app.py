import pytest

from app import FEATURE_BLUEPRINTS, create_app
from app.config import TEST_CONFIG


def test_home_page_responds(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"SecureShop" in response.data


def test_uses_in_memory_test_database(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_all_feature_blueprints_registered(app):
    for name in FEATURE_BLUEPRINTS:
        assert name in app.blueprints


def test_unknown_page_returns_safe_404(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    assert b"Traceback" not in response.data


def test_app_refuses_to_start_without_secret_key():
    config = dict(TEST_CONFIG, SECRET_KEY=None)
    with pytest.raises(RuntimeError):
        create_app(config)
