from datetime import datetime, timezone
from decimal import Decimal
from flask import abort
from flask_login import login_user
from app.models.user import User
from app.admin.decorators import admin_required
from app.extensions import db, login_manager
def register_test_route(app):

    def admin_page():
        return "Welcome Admin", 200

    if "test_admin_only" not in app.view_functions:
        app.add_url_rule(
            "/_test/admin-only",
            endpoint="test_admin_only",
            view_func=admin_required(admin_page),
            methods=["GET"]
        )

def create_test_user(role, email):

    now = datetime.now(timezone.utc)

    user = User(
        name="Test User",
        email=email.lower(),
        password_hash="test-only-password-hash",
        confirmed_at=now,
        role=role,
        credit_balance=Decimal("0.00"),
        created_at=now,
        updated_at=now
    )

    db.session.add(user)
    db.session.commit()

    return user        

def login_as(client, user):

    response = client.post(
        f"/_test/login/{user.id}"
    )

    assert response.status_code == 204
def test_visitor_cannot_access_admin(app, client):

    register_test_route(app)

    response = client.get("/_test/admin-only")

    assert response.status_code == 302

def test_customer_cannot_access_admin(app, client):

    register_test_route(app)

    customer = create_test_user(
        "customer",
        "customer@test.com"
    )

    login_as(client, customer)

    response = client.get("/_test/admin-only")

    assert response.status_code == 403       

def test_admin_can_access_admin(app, client):

    register_test_route(app)

    admin = create_test_user(
        "admin",
        "admin@test.com"
    )

    login_as(client, admin)

    response = client.get("/_test/admin-only")

    assert response.status_code == 200

    assert response.data == b"Welcome Admin"       

def register_test_route(app):

    def admin_page():
        return "Welcome Admin", 200

    def test_login(user_id):

        user = db.session.get(User, user_id)

        if user is None:
            abort(404)

        login_user(user)

        return "", 204

    app.add_url_rule(
        "/_test/admin-only",
        endpoint="test_admin_only",
        view_func=admin_required(admin_page),
        methods=["GET"]
    )

    app.add_url_rule(
        "/_test/login/<int:user_id>",
        endpoint="test_login_user",
        view_func=test_login,
        methods=["POST"])

def test_admin_dashboard_displays_statistics(app, client):

    register_test_route(app)

    admin = create_test_user(
        "admin",
        "dashboard-admin@test.com"
    )

    customer = create_test_user(
        "customer",
        "dashboard-customer@test.com"
    )

    login_as(client, admin)

    response = client.get("/admin/")

    assert response.status_code == 200
    assert b"SecureShop Admin Dashboard" in response.data
    assert b"Total Users" in response.data
    assert b"Confirmed Users" in response.data
    assert b"Administrators" in response.data