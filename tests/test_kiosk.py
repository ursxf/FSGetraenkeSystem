"""Tests for kiosk/main routes and RFID hardware integration."""

from unittest.mock import patch

from app.db import db as _db
from app.db.models import User, Product, Revenue
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


def test_rfid_login_unknown_card(client, app):
    """An unknown RFID UID should return 404."""
    response = client.post('/rfid/login', json={'uid': 'UNKNOWN_UID_XYZ'})
    assert response.status_code == 404
    assert response.get_json()['error'] == 'not_found'


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


def test_rfid_login_sets_terminal_mode(client, sample_user, app):
    """After RFID login the session should have terminal=True."""
    with client.session_transaction() as sess:
        sess.clear()
    client.post('/rfid/login', json={'uid': 'RFID001'})
    with client.session_transaction() as sess:
        assert sess.get('terminal') is True


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
