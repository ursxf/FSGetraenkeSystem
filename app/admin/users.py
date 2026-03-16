from typing import Union

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from werkzeug.wrappers import Response

from .forms import BalanceForm, RfidTagForm, UserForm
from .helpers import admin_permission
from ..db import db
from ..db.helpers import revenue_query
from ..db.models import Revenue, RfidTag, UnknownScan, User
from ..helpers import calc_hash

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
@login_required
@admin_permission.require(http_exception=401)
def index() -> str:
    aggregation = (
        db.select(db.func.sum(Revenue.amount).label('balance'), Revenue.user.label('user_id')).group_by(Revenue.user).subquery()
    )
    user_query = (
        db.select(User, db.func.coalesce(aggregation.c.balance, 0))
        .outerjoin(aggregation, User.id == aggregation.c.user_id)
        .order_by(User.name)
    )
    users_list = db.session.execute(user_query).all()
    unknown_scans = UnknownScan.query.order_by(UnknownScan.scanned_at.desc()).all()
    return render_template('users/index.html', users=users_list, unknown_scans=unknown_scans)


@users_bp.route('/', methods=['POST'])
@login_required
@admin_permission.require(http_exception=401)
def post() -> Union[Response, str]:
    form = UserForm()
    if not form.validate_on_submit():
        flash('Submitted form was not valid!', category='danger')
        return render_template('users/form.html', form=form, edit=False)

    create = False
    user = User.query.filter_by(id=form.id.data).one_or_none()
    if user is None:
        create = True
        user = User()

    user.name = form.name.data
    user.isop = form.isop.data
    user.active = form.active.data

    if form.unset_pin.data:
        user.pin = None
    elif form.pin.data:
        user.pin = calc_hash(form.pin.data)

    if create:
        db.session.add(user)
        db.session.flush()
        # Add initial RFID tag if provided
        if form.new_tag_uid.data:
            uid_hash = calc_hash(form.new_tag_uid.data)
            existing_tag = RfidTag.query.filter_by(uid_hash=uid_hash).one_or_none()
            if existing_tag is None:
                db.session.add(RfidTag(user_id=user.id, uid_hash=uid_hash))
                # Remove from unknown scans if it was there
                UnknownScan.query.filter_by(uid_hash=uid_hash).delete()
        db.session.commit()
        flash(f'Created user {form.name.data}', category='success')
    else:
        db.session.commit()
        flash(f'Updated user "{form.name.data}"', category='success')

    return redirect(url_for('admin.users.index'))


@users_bp.route('/<int:user_id>/tags/add', methods=['POST'])
@login_required
@admin_permission.require(http_exception=401)
def add_tag(user_id: int) -> Response:
    """Add an RFID tag to an existing user."""
    user = db.session.get(User, user_id)
    form = RfidTagForm()
    if form.validate_on_submit():
        uid_hash = calc_hash(form.uid.data)
        existing = RfidTag.query.filter_by(uid_hash=uid_hash).one_or_none()
        if existing is not None:
            flash('Dieser RFID-Tag ist bereits einem Konto zugewiesen.', category='danger')
        else:
            db.session.add(RfidTag(user_id=user.id, uid_hash=uid_hash))
            # Remove from unknown scans if present
            UnknownScan.query.filter_by(uid_hash=uid_hash).delete()
            db.session.commit()
            flash('RFID-Tag hinzugefügt.', category='success')
    else:
        flash('Ungültige Eingabe.', category='danger')
    return redirect(url_for('admin.users.detail', user_id=user_id))


@users_bp.route('/<int:user_id>/tags/remove/<int:tag_id>', methods=['POST'])
@login_required
@admin_permission.require(http_exception=401)
def remove_tag(user_id: int, tag_id: int) -> Response:
    """Remove an RFID tag from a user."""
    tag = db.session.get(RfidTag, tag_id)
    if tag and tag.user_id == user_id:
        db.session.delete(tag)
        db.session.commit()
        flash('RFID-Tag entfernt.', category='success')
    return redirect(url_for('admin.users.detail', user_id=user_id))


@users_bp.route('/<int:user_id>')
@login_required
@admin_permission.require(http_exception=401)
def detail(user_id: int) -> str:
    """Show user detail page with RFID tags and transaction history."""
    user = db.session.get(User, user_id)
    tag_form = RfidTagForm()
    revenues_query = revenue_query(user_id)
    revenues = db.session.execute(revenues_query).all()
    return render_template('users/detail.html', user=user, tag_form=tag_form, revenues=revenues)


@users_bp.route('/unknown-scans/<int:scan_id>/assign/<int:user_id>', methods=['POST'])
@login_required
@admin_permission.require(http_exception=401)
def assign_unknown_scan(scan_id: int, user_id: int) -> Response:
    """Assign an unknown scan to an existing user."""
    scan = db.session.get(UnknownScan, scan_id)
    user = db.session.get(User, user_id)
    if scan and user:
        existing = RfidTag.query.filter_by(uid_hash=scan.uid_hash).one_or_none()
        if existing is None:
            db.session.add(RfidTag(user_id=user.id, uid_hash=scan.uid_hash))
            db.session.delete(scan)
            db.session.commit()
            flash(f'RFID-Tag wurde {user.name} zugewiesen.', category='success')
        else:
            flash('Dieser Tag ist bereits einem Konto zugewiesen.', category='danger')
    return redirect(url_for('admin.users.index'))


@users_bp.route('/unknown-scans/<int:scan_id>/dismiss', methods=['POST'])
@login_required
@admin_permission.require(http_exception=401)
def dismiss_unknown_scan(scan_id: int) -> Response:
    """Discard an unknown scan."""
    scan = db.session.get(UnknownScan, scan_id)
    if scan:
        db.session.delete(scan)
        db.session.commit()
        flash('Unbekannter Scan verworfen.', category='success')
    return redirect(url_for('admin.users.index'))


@users_bp.route('/impersonate/<user_id>')
@login_required
@admin_permission.require(http_exception=401)
def impersonate(user_id: int) -> Response:
    session['impersonate'] = user_id
    return redirect(url_for('main.index'))


@users_bp.route('/impersonate/pop')
@login_required
@admin_permission.require(http_exception=401)
def pop_impersonate() -> Response:
    session.pop('impersonate', None)
    return redirect(url_for('admin.users.index'))


@users_bp.route('/balance/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=401)
def balance(user_id: int) -> Union[Response, str]:
    user = db.session.get(User, int(user_id))
    form = BalanceForm()

    if request.method == 'POST':
        if form.validate_on_submit() and form.amount.data:
            euros = form.amount.data
            cents = int(euros * 100)

            if form.recharge.data:
                factor = 1
                flash(f'Added {euros:.2f} € for {user.name}', category='success')
            elif form.charge.data:
                factor = -1
                flash(f'Charged {euros:.2f} € from {user.name}', category='success')
            else:
                flash('Submitted form was not valid!', category='danger')
                return render_template('users/balance.html', form=form, user=user)

            rev = Revenue(user=user.id, product=None, amount=cents * factor)
            db.session.add(rev)
            db.session.commit()
            return redirect(url_for('admin.users.index'))

        flash('Submitted form was not valid!', category='danger')

    return render_template('users/balance.html', form=form, user=user)


@users_bp.route('/revenues/<user_id>', methods=['GET'])
@login_required
@admin_permission.require(http_exception=401)
def revenues(user_id: int) -> str:
    user = db.session.get(User, int(user_id))
    revenues_query = revenue_query(user_id)

    return render_template('users/revenues.html', user=user, revenues=db.session.execute(revenues_query).all())


@users_bp.route('/add')
@login_required
@admin_permission.require(http_exception=401)
def add() -> str:
    form = UserForm(active=True)
    return render_template('users/form.html', form=form, edit=False)


@users_bp.route('/edit/<user_id>')
@login_required
@admin_permission.require(http_exception=401)
def edit(user_id: int) -> str:
    user = db.session.get(User, int(user_id))
    form = UserForm(id=user.id, name=user.name, isop=user.isop, active=user.active)

    return render_template('users/form.html', form=form, edit=True)


@users_bp.route('/delete/<user_id>')
@login_required
@admin_permission.require(http_exception=401)
def delete(user_id: int) -> Response:
    user = db.session.get(User, int(user_id))
    db.session.delete(user)
    db.session.commit()
    flash(f'Deleted user "{user.name}"', category='success')
    return redirect(url_for('admin.users.index'))

