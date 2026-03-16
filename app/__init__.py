import contextlib
from importlib import metadata
from pathlib import Path
from typing import Optional

from flask import Flask, flash, redirect, session, url_for
from flask_login import LoginManager, current_user
from flask_principal import Principal, RoleNeed, UserNeed, identity_loaded
from werkzeug.wrappers import Response

from .account import account_bp
from .admin import admin_bp
from .auth import auth_bp
from .db import db
from .db.helpers import get_balance
from .db.models import User
from .helpers import format_currency, get_user_id
from .main import main_bp


def create_app(test_config: Optional[dict] = None) -> Flask:  # noqa: C901
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=True,
        REMEMBER_COOKIE_SECURE=True,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///getraenke.db',
        TERMINAL_LOGOUT_TIMEOUT=30,
        QUICK_CANCEL_SEC=60,
        BANK_DATA=None,
        FAVORITES_DISPLAY=3,
        FAVORITES_DAYS=100,
        RFID_ENABLED=False,
        RFID_DEMO_UID='',
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    elif isinstance(test_config, dict):
        app.config.from_mapping(test_config)
    else:
        app.config.from_object(test_config)

    app.config.from_prefixed_env()

    with contextlib.suppress(OSError):
        Path(app.instance_path).mkdir(parents=True)

    db.init_app(app)

    Principal(app)

    login_manager = LoginManager()
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized() -> Response:
        if login_manager.localize_callback is not None:
            flash(login_manager.localize_callback(login_manager.login_message), category=login_manager.login_message_category)
        else:
            flash(login_manager.login_message, category=login_manager.login_message_category)

        if session.get('terminal', False):
            return redirect(url_for('auth.login', terminal=True))

        return redirect(url_for('auth.login'))

    @login_manager.user_loader
    def load_user(user_id: int) -> User:
        return User.query.get(user_id)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):  # noqa: ANN001
        identity.user = current_user

        if hasattr(current_user, 'id'):
            identity.provides.add(UserNeed(current_user.id))

        if hasattr(current_user, 'isop'):
            identity.provides.add(RoleNeed('admin'))

    app.jinja_env.filters.update(
        format_currency=format_currency,
    )

    @app.context_processor
    def functions() -> dict:
        return {'get_balance': get_balance, 'get_user_id': get_user_id}

    @app.context_processor
    def get_version() -> dict:
        try:
            version = metadata.version('nanposweb')
        except metadata.PackageNotFoundError:
            version = 'devel'
        return {'version': version}

    @app.context_processor
    def get_utils() -> dict:
        utils = []
        if app.config.get('BANK_DATA', False):
            utils.append(('main.bank_account', 'Bank Account'))
        if app.config.get('utils', False):
            utils.extend(app.config['utils'])
        return {'utils': utils}

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    from .rfid import start_background_reader
    start_background_reader()

    return app
