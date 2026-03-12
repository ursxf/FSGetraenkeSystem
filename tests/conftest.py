"""Pytest configuration and shared fixtures."""

import pytest
from app import create_app, db as _db
from app.models import User, Drink, Transaction, AdminUser
from werkzeug.security import generate_password_hash


class TestConfig:
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    TESTING = True
    ADMIN_USERNAME = "testadmin"
    ADMIN_PASSWORD = "testpass"
    RFID_ENABLED = False


@pytest.fixture(scope="session")
def app():
    """Create application configured for testing."""
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Provide a clean DB for each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        # Clean tables
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        # Re-seed admin
        if not AdminUser.query.filter_by(username="testadmin").first():
            admin = AdminUser(
                username="testadmin",
                password_hash=generate_password_hash("testpass"),
            )
            _db.session.add(admin)
            _db.session.commit()


@pytest.fixture(scope="function")
def client(app, db):
    return app.test_client()


@pytest.fixture(scope="function")
def auth_client(client, app):
    """A test client that is already logged in as admin."""
    with app.app_context():
        client.post(
            "/admin/login",
            data={"username": "testadmin", "password": "testpass"},
            follow_redirects=True,
        )
    return client


@pytest.fixture()
def sample_user(db):
    user = User(name="Max Mustermann", rfid_uid="RFID001", balance_cents=500)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def sample_drink(db):
    drink = Drink(name="Club Mate", price_cents=150, active=True)
    db.session.add(drink)
    db.session.commit()
    return drink
