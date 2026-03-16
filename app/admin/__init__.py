from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required

from .admins import admins_bp as admins_blueprint
from .helpers import admin_permission
from .products import products_bp as products_blueprint
from .transactions import transactions_bp as transactions_blueprint
from .users import users_bp as users_blueprint
from ..db import db
from ..db.models import Product, Revenue, User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates')

admin_bp.register_blueprint(users_blueprint)
admin_bp.register_blueprint(products_blueprint)
admin_bp.register_blueprint(admins_blueprint)
admin_bp.register_blueprint(transactions_blueprint)


@admin_bp.route('/')
@login_required
@admin_permission.require(http_exception=401)
def dashboard():
    active_users = User.query.filter_by(active=True).count()
    active_products = Product.query.filter_by(visible=True).count()
    total_balance = db.session.execute(
        db.select(db.func.coalesce(db.func.sum(Revenue.amount), 0))
    ).scalars().first() or 0
    latest_revenues = db.session.execute(
        db.select(Revenue, db.func.coalesce(User.name, ''), db.func.coalesce(Product.name, ''))
        .outerjoin(User, Revenue.user == User.id)
        .outerjoin(Product, Revenue.product == Product.id)
        .order_by(db.desc(Revenue.date))
        .limit(10)
    ).all()
    return render_template(
        'dashboard.html',
        active_users=active_users,
        active_products=active_products,
        total_balance=total_balance,
        latest_revenues=latest_revenues,
    )

