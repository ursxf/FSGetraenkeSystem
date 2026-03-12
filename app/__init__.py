from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_object="config.Config"):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "Bitte melde dich an."
    login_manager.login_message_category = "warning"

    from app.admin.routes import admin_bp
    from app.kiosk.routes import kiosk_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(kiosk_bp, url_prefix="/")

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app):
    """Create the built-in admin user if it does not exist yet."""
    from app.models import AdminUser
    from werkzeug.security import generate_password_hash

    if not AdminUser.query.filter_by(username=app.config["ADMIN_USERNAME"]).first():
        admin = AdminUser(
            username=app.config["ADMIN_USERNAME"],
            password_hash=generate_password_hash(app.config["ADMIN_PASSWORD"]),
        )
        db.session.add(admin)
        db.session.commit()
