"""Tests for kiosk/main routes and RFID hardware integration."""

from unittest.mock import patch

from app.db import db as _db
from app.db.models import RfidTag, UnknownScan, User, Product, Revenue
from app.helpers import calc_hash


# ---------------------------------------------------------------------------
# Main index (requires login)
# ---------------------------------------------------------------------------


def test_index_redirects_unauthenticated(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_index_loads_when_logged_in(auth_client, sample_product):
    response = auth_client.get('/')
    assert response.status_code == 200
    assert sample_product.name.encode() in response.data


def test_purchase_product(auth_client, sample_product, sample_user, app):
    # auth_client is logged in as the admin user – give them some balance
    with app.app_context():
        admin = User.query.filter_by(name='testadmin').first()
        rev = Revenue(user=admin.id, product=None, amount=1000)
        _db.session.add(rev)
        _db.session.commit()

    response = auth_client.post(
        '/',
        data={'product_id': sample_product.id},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert sample_product.name.encode() in response.data


def test_purchase_blocked_by_minimum_balance(app, sample_product):
    """Purchase should be blocked when balance would drop below minimum."""
    import json
    from app.db.models import RfidTag, User, Revenue

    app.config['MINIMUM_BALANCE_CENTS'] = 100_00  # 100 € minimum

    with app.app_context():
        poor_user = User(name='PoorUser', active=True, pin=calc_hash('poorpin'))
        _db.session.add(poor_user)
        _db.session.flush()
        _db.session.commit()

    test_client = app.test_client()
    test_client.post('/login', data={'username': 'PoorUser', 'pin': 'poorpin'})

    response = test_client.post(
        '/',
        data={'product_id': sample_product.id},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Should not have created a purchase revenue
    with app.app_context():
        poor_user = User.query.filter_by(name='PoorUser').first()
        purchase_count = Revenue.query.filter(
            Revenue.user == poor_user.id,
            Revenue.product is not None,
        ).count()
        assert purchase_count == 0

    app.config['MINIMUM_BALANCE_CENTS'] = 0  # reset


def test_quick_cancel(auth_client, sample_product, app):
    with app.app_context():
        admin = User.query.filter_by(name='testadmin').first()
        # Give balance and create a cancelable revenue
        _db.session.add(Revenue(user=admin.id, product=None, amount=1000))
        _db.session.commit()
    auth_client.post('/', data={'product_id': sample_product.id}, follow_redirects=True)
    response = auth_client.get('/quick-cancel', follow_redirects=True)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Terminal / RFID login
# ---------------------------------------------------------------------------


def test_login_page_terminal_mode(client):
    response = client.get('/login?terminal=True')
    assert response.status_code == 200
    assert b'Terminal' in response.data


def test_rfid_login_unknown_card_records_scan(client, app):
    """An unknown RFID UID should return 404 and create an UnknownScan."""
    response = client.post('/rfid/login', json={'uid': 'TRULY_UNKNOWN_UID'})
    assert response.status_code == 404
    assert response.get_json()['error'] == 'not_found'
    with app.app_context():
        scan = UnknownScan.query.filter_by(uid_hash=calc_hash('TRULY_UNKNOWN_UID')).first()
        assert scan is not None


def test_rfid_login_missing_uid(client):
    response = client.post('/rfid/login', json={})
    assert response.status_code == 400
    assert response.get_json()['error'] == 'uid required'


def test_rfid_login_success(client, sample_user, app):
    """A registered RFID card should log in the user and return a redirect."""
    response = client.post('/rfid/login', json={'uid': 'RFID001'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'redirect' in data
    assert '/' in data['redirect']


def test_rfid_login_inactive_user(client, app):
    """An inactive user's RFID card should return 403."""
    with app.app_context():
        user = User(name='InactiveUser', active=False)
        _db.session.add(user)
        _db.session.flush()
        tag = RfidTag(user_id=user.id, uid_hash=calc_hash('INACTIVE_CARD'))
        _db.session.add(tag)
        _db.session.commit()

    response = client.post('/rfid/login', json={'uid': 'INACTIVE_CARD'})
    assert response.status_code == 403
    assert response.get_json()['error'] == 'inactive'


def test_rfid_login_sets_terminal_mode(client, sample_user, app):
    """After RFID login the session should have terminal=True."""
    with client.session_transaction() as sess:
        sess.clear()
    client.post('/rfid/login', json={'uid': 'RFID001'})
    with client.session_transaction() as sess:
        assert sess.get('terminal') is True


# ---------------------------------------------------------------------------
# API: identify
# ---------------------------------------------------------------------------


def test_api_identify_success(client, sample_user, app):
    response = client.post('/api/identify', json={'uid': 'RFID001'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == sample_user.name
    assert 'balance_euro' in data


def test_api_identify_unknown(client, app):
    response = client.post('/api/identify', json={'uid': 'NEVER_EXISTS'})
    assert response.status_code == 404


def test_api_identify_missing_uid(client):
    response = client.post('/api/identify', json={})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# SSE scan stream
# ---------------------------------------------------------------------------


def test_rfid_stream_delivers_uid(app):
    """The SSE endpoint streams the scanned UID as a data event."""
    with patch('app.rfid.enable_scanning'), \
         patch('app.rfid.disable_scanning'), \
         patch('app.rfid.wait_for_scan', return_value='CAFEBABE'):
        test_client = app.test_client()
        response = test_client.get('/rfid/stream')
        body = response.data
    assert response.status_code == 200
    assert response.content_type.startswith('text/event-stream')
    assert b'"uid": "CAFEBABE"' in body


def test_rfid_stream_keepalive_then_uid(app):
    """The SSE endpoint sends keepalive comments while waiting, then the UID."""
    call_count = 0

    def _wait_side_effect(timeout=30.0):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None
        return 'BEEFDEAD'

    with patch('app.rfid.enable_scanning'), \
         patch('app.rfid.disable_scanning'), \
         patch('app.rfid.wait_for_scan', side_effect=_wait_side_effect):
        test_client = app.test_client()
        response = test_client.get('/rfid/stream')
        body = response.data
    assert b': keepalive' in body
    assert b'"uid": "BEEFDEAD"' in body


# ---------------------------------------------------------------------------
# Account routes
# ---------------------------------------------------------------------------


def test_account_revenues(auth_client):
    response = auth_client.get('/account/revenues')
    assert response.status_code == 200


def test_account_pin_page(auth_client):
    response = auth_client.get('/account/pin')
    assert response.status_code == 200


def test_account_card_page(auth_client):
    response = auth_client.get('/account/card')
    assert response.status_code == 200

