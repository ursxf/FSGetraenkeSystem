from flask import Blueprint, render_template, request
from flask_login import login_required

from .helpers import admin_permission
from ..db import db
from ..db.models import Product, Revenue, User

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')

_PER_PAGE = 50


@transactions_bp.route('/')
@login_required
@admin_permission.require(http_exception=401)
def index() -> str:
    page = request.args.get('page', 1, type=int)
    query = (
        db.select(Revenue, db.func.coalesce(User.name, ''), db.func.coalesce(Product.name, ''))
        .outerjoin(User, Revenue.user == User.id)
        .outerjoin(Product, Revenue.product == Product.id)
        .order_by(db.desc(Revenue.date))
    )
    total = db.session.execute(db.select(db.func.count()).select_from(Revenue)).scalars().first() or 0
    offset = (page - 1) * _PER_PAGE
    rows = db.session.execute(query.limit(_PER_PAGE).offset(offset)).all()
    total_pages = max(1, (total + _PER_PAGE - 1) // _PER_PAGE)
    return render_template(
        'transactions/index.html',
        rows=rows,
        page=page,
        total_pages=total_pages,
        per_page=_PER_PAGE,
    )
