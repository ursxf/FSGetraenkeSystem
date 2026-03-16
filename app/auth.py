import json
from typing import Union

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_principal import AnonymousIdentity, Identity, identity_changed
from werkzeug.wrappers import Response

from .db.models import User
from .forms import LoginForm
from .helpers import calc_hash, check_hash

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login() -> Union[Response, str]:
    if current_user.is_authenticated:
        flash('Already logged in.')
        return redirect(request.args.get('next') or url_for('main.index'))

    session['terminal'] = request.args.get('terminal', False, type=bool)
    form = LoginForm()

    rfid_enabled = current_app.config.get('RFID_ENABLED', False)

    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(name=form.username.data).one_or_none()

            if user and check_hash(user.pin, form.pin.data or ''):
                login_user(user, remember=form.remember.data)
                flash('Logged in', category='success')

                identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))  # type: ignore

                return redirect(request.args.get('next') or url_for('main.index'))

            flash('Please check your login details and try again.', category='danger')
        else:
            flash('Submitted form was not valid!', category='danger')

    return render_template('login.html', form=form, rfid_enabled=rfid_enabled)


@auth_bp.route('/logout')
@login_required
def logout() -> Response:
    logout_user()

    for key in ('identity.id', 'identity.auth_type'):
        session.pop(key, None)

    session.pop('impersonate', None)

    identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())  # type: ignore
    flash('Logged out')

    if session.get('terminal', False):
        return redirect(url_for('auth.login', terminal=True))

    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# RFID hardware endpoints
# ---------------------------------------------------------------------------


@auth_bp.route('/rfid/stream')
def rfid_stream() -> Response:
    """SSE endpoint: pushes the next RFID scan to the login page.

    The browser opens this endpoint via ``EventSource`` while the login page
    is visible in terminal mode.  The server enables the RFID scanner on
    connect, holds the connection open with periodic keepalive comments, and
    sends exactly one ``data:`` event when a card is scanned.
    """
    from flask import stream_with_context

    from .rfid import disable_scanning, enable_scanning, wait_for_scan

    def _generate():
        enable_scanning()
        try:
            while True:
                uid = wait_for_scan(timeout=15.0)
                if uid:
                    yield f'data: {json.dumps({"uid": uid})}\n\n'
                    return
                yield ': keepalive\n\n'
        finally:
            disable_scanning()

    return Response(
        stream_with_context(_generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@auth_bp.route('/rfid/login', methods=['POST'])
def rfid_login() -> Union[Response, str]:
    """Identify and log in a user by RFID card UID.

    Accepts JSON ``{"uid": "<UID>"}``.  Hashes the UID and looks up the
    matching ``User.card`` field.  On success, logs the user in with terminal
    mode active and returns a JSON redirect target.
    """
    from .rfid import disable_scanning

    data = request.get_json(force=True, silent=True) or {}
    uid = str(data.get('uid', '')).strip()
    if not uid:
        return jsonify({'error': 'uid required'}), 400

    disable_scanning()

    card_hash = calc_hash(uid)
    user = User.query.filter_by(card=card_hash).one_or_none()

    if user is None:
        return jsonify({'error': 'not_found'}), 404

    login_user(user, remember=False)
    session['terminal'] = True
    identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))  # type: ignore

    return jsonify({'redirect': url_for('main.index')})
