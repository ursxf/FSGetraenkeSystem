from typing import Union

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from werkzeug.wrappers import Response

from .forms import AdminForm, ChangePasswordForm
from .helpers import admin_permission
from ..db import db
from ..db.models import User
from ..helpers import calc_hash, check_hash

admins_bp = Blueprint('admins', __name__, url_prefix='/admins')


@admins_bp.route('/')
@login_required
@admin_permission.require(http_exception=401)
def index() -> str:
    admins = User.query.filter_by(isop=True).order_by(User.name).all()
    return render_template('admins/index.html', admins=admins)


@admins_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=401)
def new() -> Union[Response, str]:
    form = AdminForm()
    if form.validate_on_submit():
        if form.pin.data != form.confirm_pin.data:
            flash('PIN und Bestätigung stimmen nicht überein.', category='danger')
            return render_template('admins/form.html', form=form)

        if User.query.filter_by(name=form.name.data).first():
            flash(f'Benutzername "{form.name.data}" existiert bereits.', category='danger')
            return render_template('admins/form.html', form=form)

        admin = User(name=form.name.data, pin=calc_hash(form.pin.data), isop=True, active=True)
        db.session.add(admin)
        db.session.commit()
        flash(f'Admin "{form.name.data}" angelegt.', category='success')
        return redirect(url_for('admin.admins.index'))

    return render_template('admins/form.html', form=form)


@admins_bp.route('/delete/<int:admin_id>')
@login_required
@admin_permission.require(http_exception=401)
def delete(admin_id: int) -> Response:
    admin = db.session.get(User, admin_id)

    if admin is None or not admin.isop:
        flash('Admin nicht gefunden.', category='danger')
        return redirect(url_for('admin.admins.index'))

    if admin.id == current_user.id:
        flash('Du kannst deinen eigenen Account nicht löschen.', category='danger')
        return redirect(url_for('admin.admins.index'))

    remaining = User.query.filter_by(isop=True).count()
    if remaining <= 1:
        flash('Es muss mindestens ein Admin-Account verbleiben.', category='danger')
        return redirect(url_for('admin.admins.index'))

    db.session.delete(admin)
    db.session.commit()
    flash(f'Admin "{admin.name}" gelöscht.', category='success')
    return redirect(url_for('admin.admins.index'))


@admins_bp.route('/password', methods=['GET', 'POST'])
@login_required
@admin_permission.require(http_exception=401)
def change_password() -> Union[Response, str]:
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_hash(current_user.pin, form.old_pin.data):
            flash('Aktuelles Passwort ist falsch.', category='danger')
            return render_template('admins/change_password.html', form=form)

        if form.new_pin.data != form.confirm_pin.data:
            flash('Neues Passwort und Bestätigung stimmen nicht überein.', category='danger')
            return render_template('admins/change_password.html', form=form)

        current_user.pin = calc_hash(form.new_pin.data)
        db.session.commit()
        flash('Passwort geändert.', category='success')
        return redirect(url_for('admin.admins.index'))

    return render_template('admins/change_password.html', form=form)
