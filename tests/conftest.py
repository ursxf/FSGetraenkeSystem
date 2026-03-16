"""Pytest configuration and shared fixtures."""

import pytest
from app import create_app
from app.db import db as _db
from app.db.models import RfidTag, User, Product, Revenue
from app.helpers import calc_hash


class TestConfig:
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    TESTING = True
    RFID_ENABLED = False
    RFID_DEMO_UID = ''
    TERMINAL_LOGOUT_TIMEOUT = None
    QUICK_CANCEL_SEC = 60
    FAVORITES_DISPLAY = 3
    FAVORITES_DAYS = 100
    MINIMUM_BALANCE_CENTS = 0
    ADMIN_USERNAME = 'testadmin'
    ADMIN_PASSWORD = 'testpin'


@pytest.fixture(scope='session')
def app():
    """Create application configured for testing."""
    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean DB for each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        _seed_admin()


def _seed_admin():
    """Create the default admin user if it does not exist yet."""
    if not User.query.filter_by(name='testadmin').first():
        admin = User(
            name='testadmin',
            pin=calc_hash('testpin'),
            isop=True,
            active=True,
        )
        _db.session.add(admin)
        _db.session.commit()


@pytest.fixture(scope='function')
def client(app, db):
    return app.test_client()


@pytest.fixture(scope='function')
def auth_client(client, app):
    """A test client that is already logged in as admin."""
    with app.app_context():
        client.post(
            '/login',
            data={'username': 'testadmin', 'pin': 'testpin'},
            follow_redirects=True,
        )
    return client


@pytest.fixture()
def sample_user(db):
    user = User(
        name='Max Mustermann',
        active=True,
    )
    _db.session.add(user)
    _db.session.flush()
    # Add an RFID tag for the sample user
    tag = RfidTag(user_id=user.id, uid_hash=calc_hash('RFID001'))
    _db.session.add(tag)
    # Give them some balance via a revenue entry
    rev = Revenue(user=user.id, product=None, amount=500)
    _db.session.add(rev)
    _db.session.commit()
    return user


@pytest.fixture()
def sample_product(db):
    product = Product(name='Club Mate', price=150, visible=True)
    _db.session.add(product)
    _db.session.commit()
    return product

