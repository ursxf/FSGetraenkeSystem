"""Tests for admin routes (nanposweb architecture)."""

import pytest
from app.db import db as _db
from app.db.models import RfidTag, UnknownScan, User, Product, Revenue
from app.helpers import calc_hash


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_login_page_loads(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'NANPOS' in response.data


def test_login_with_wrong_pin(client):
    response = client.post(
        '/login',
        data={'username': 'testadmin', 'pin': 'wrong'},
        follow_redirects=True,
    )
    assert b'login details' in response.data


def test_login_success(client):
    response = client.post(
        '/login',
        data={'username': 'testadmin', 'pin': 'testpin'},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_protected_route_redirects_unauthenticated(client):
    response = client.get('/admin/users/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_logout(auth_client):
    response = auth_client.get('/logout', follow_redirects=True)
    assert b'Logged out' in response.data


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


def test_users_list_loads(auth_client):
    response = auth_client.get('/admin/users/')
    assert response.status_code == 200


def test_create_user(auth_client, app):
    response = auth_client.post(
        '/admin/users/',
        data={'name': 'Erika Muster', 'isop': False, 'active': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(name='Erika Muster').first()
        assert user is not None


def test_create_user_with_rfid_tag(auth_client, app):
    response = auth_client.post(
        '/admin/users/',
        data={'name': 'Card User', 'new_tag_uid': 'RFID_UID_XY', 'active': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(name='Card User').first()
        assert user is not None
        # RFID tag should be stored as hash
        tag = RfidTag.query.filter_by(uid_hash=calc_hash('RFID_UID_XY')).first()
        assert tag is not None
        assert tag.user_id == user.id


def test_edit_user(auth_client, sample_user, app):
    response = auth_client.post(
        '/admin/users/',
        data={'id': sample_user.id, 'name': 'Max Geaendert', 'active': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = _db.session.get(User, sample_user.id)
        assert user.name == 'Max Geaendert'


def test_admin_can_view_user_revenues(auth_client, sample_user):
    response = auth_client.get(f'/admin/users/revenues/{sample_user.id}')
    assert response.status_code == 200
    assert sample_user.name.encode() in response.data


def test_admin_user_detail(auth_client, sample_user):
    response = auth_client.get(f'/admin/users/{sample_user.id}')
    assert response.status_code == 200
    assert sample_user.name.encode() in response.data


def test_admin_add_rfid_tag(auth_client, sample_user, app):
    response = auth_client.post(
        f'/admin/users/{sample_user.id}/tags/add',
        data={'uid': 'NEW_RFID_TAG'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        tag = RfidTag.query.filter_by(uid_hash=calc_hash('NEW_RFID_TAG')).first()
        assert tag is not None
        assert tag.user_id == sample_user.id


def test_admin_remove_rfid_tag(auth_client, sample_user, app):
    with app.app_context():
        tag = RfidTag.query.filter_by(user_id=sample_user.id).first()
        assert tag is not None
        tag_id = tag.id
    response = auth_client.post(
        f'/admin/users/{sample_user.id}/tags/remove/{tag_id}',
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert _db.session.get(RfidTag, tag_id) is None


def test_admin_balance_recharge(auth_client, sample_user, app):
    response = auth_client.post(
        f'/admin/users/balance/{sample_user.id}',
        data={'amount': '5.00', 'recharge': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        balance = _db.session.execute(
            _db.select(_db.func.sum(Revenue.amount)).where(Revenue.user == sample_user.id)
        ).scalars().first()
        assert balance == 1000  # 500 initial + 500 added


def test_admin_balance_charge(auth_client, sample_user, app):
    response = auth_client.post(
        f'/admin/users/balance/{sample_user.id}',
        data={'amount': '1.00', 'charge': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        balance = _db.session.execute(
            _db.select(_db.func.sum(Revenue.amount)).where(Revenue.user == sample_user.id)
        ).scalars().first()
        assert balance == 400  # 500 initial - 100 charged


def test_delete_user(auth_client, app):
    with app.app_context():
        user = User(name='ToDelete')
        _db.session.add(user)
        _db.session.commit()
        uid = user.id
    response = auth_client.get(f'/admin/users/delete/{uid}', follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert _db.session.get(User, uid) is None


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------


def test_admin_dashboard_loads(auth_client):
    response = auth_client.get('/admin/')
    assert response.status_code == 200
    assert b'Dashboard' in response.data


def test_admin_transactions_loads(auth_client):
    response = auth_client.get('/admin/transactions/')
    assert response.status_code == 200


def test_admin_admins_list_loads(auth_client):
    response = auth_client.get('/admin/admins/')
    assert response.status_code == 200
    assert b'testadmin' in response.data


def test_admin_unknown_scan_assign(auth_client, sample_user, app):
    with app.app_context():
        scan = UnknownScan(uid_hash=calc_hash('UNKNOWN_CARD'))
        _db.session.add(scan)
        _db.session.commit()
        scan_id = scan.id

    response = auth_client.post(
        f'/admin/users/unknown-scans/{scan_id}/assign/{sample_user.id}',
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert _db.session.get(UnknownScan, scan_id) is None
        tag = RfidTag.query.filter_by(uid_hash=calc_hash('UNKNOWN_CARD')).first()
        assert tag is not None


def test_admin_unknown_scan_dismiss(auth_client, app):
    with app.app_context():
        scan = UnknownScan(uid_hash=calc_hash('TOBE_DISMISSED'))
        _db.session.add(scan)
        _db.session.commit()
        scan_id = scan.id

    response = auth_client.post(
        f'/admin/users/unknown-scans/{scan_id}/dismiss',
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert _db.session.get(UnknownScan, scan_id) is None


# ---------------------------------------------------------------------------
# Product management
# ---------------------------------------------------------------------------


def test_products_list_loads(auth_client):
    response = auth_client.get('/admin/products/')
    assert response.status_code == 200


def test_create_product(auth_client, app):
    response = auth_client.post(
        '/admin/products/',
        data={'name': 'Club Mate', 'price': 150, 'visible': True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert Product.query.filter_by(name='Club Mate').first() is not None


def test_edit_product(auth_client, sample_product, app):
    response = auth_client.post(
        '/admin/products/',
        data={
            'id': sample_product.id,
            'name': 'Fritz Kola',
            'price': 200,
            'visible': True,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        product = _db.session.get(Product, sample_product.id)
        assert product.name == 'Fritz Kola'
        assert product.price == 200


def test_delete_product(auth_client, sample_product, app):
    response = auth_client.get(
        f'/admin/products/delete/{sample_product.id}',
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert _db.session.get(Product, sample_product.id) is None


# ---------------------------------------------------------------------------
# Impersonate
# ---------------------------------------------------------------------------


def test_impersonate_user(auth_client, sample_user):
    response = auth_client.get(
        f'/admin/users/impersonate/{sample_user.id}',
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert '/' in response.headers['Location']


def test_impersonate_pop(auth_client, sample_user):
    auth_client.get(f'/admin/users/impersonate/{sample_user.id}')
    response = auth_client.get('/admin/users/impersonate/pop', follow_redirects=False)
    assert response.status_code == 302


