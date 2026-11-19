import pytest  # pyright: ignore[reportMissingImports]

from app import create_app
from app.config import TEST_CONFIG
from app.extensions import db


@pytest.fixture
def app():
    app = create_app(dict(TEST_CONFIG))
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
