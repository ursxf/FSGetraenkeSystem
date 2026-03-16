"""Tests for database models."""

import pytest
from app.db.models import User, Product, Revenue, RfidTag, UnknownScan
from app.db.helpers import get_balance
from app.helpers import calc_hash, format_currency


def test_user_has_rfid_tag(db):
    user = User(name='Anna', active=True)
    db.session.add(user)
    db.session.flush()
    tag = RfidTag(user_id=user.id, uid_hash=calc_hash('MY_CARD_UID'))
    db.session.add(tag)
    db.session.commit()
    assert user.rfid_tags.count() == 1


def test_user_isop_default_false(db):
    user = User(name='Bob')
    db.session.add(user)
    db.session.commit()
    assert user.isop is False


def test_user_active_default_true(db):
    user = User(name='Carol')
    db.session.add(user)
    db.session.commit()
    assert user.active is True


def test_product_has_price(db):
    product = Product(name='Club Mate', price=150)
    db.session.add(product)
    db.session.commit()
    assert product.price == 150


def test_product_visible_default_true(db):
    product = Product(name='Wasser', price=80)
    db.session.add(product)
    db.session.commit()
    assert product.visible is True


def test_revenue_balance_calculation(db):
    user = User(name='Tester')
    db.session.add(user)
    db.session.flush()
    db.session.add(Revenue(user=user.id, product=None, amount=500))
    product = Product(name='Wasser', price=150)
    db.session.add(product)
    db.session.flush()
    db.session.add(Revenue(user=user.id, product=product.id, amount=-150))
    db.session.commit()
    balance = get_balance(user.id)
    assert balance == 350


def test_revenue_age_property(db):
    user = User(name='AgeTest')
    db.session.add(user)
    db.session.flush()
    rev = Revenue(user=user.id, product=None, amount=100)
    db.session.add(rev)
    db.session.commit()
    assert rev.age.total_seconds() >= 0


def test_format_currency():
    assert format_currency(150) == '1,50 €'
    assert format_currency(0) == '0,00 €'
    assert format_currency(-100) == '-1,00 €'


def test_calc_hash_deterministic():
    h1 = calc_hash('RFID_UID_123')
    h2 = calc_hash('RFID_UID_123')
    assert h1 == h2


def test_calc_hash_different_inputs():
    assert calc_hash('CARD_A') != calc_hash('CARD_B')


def test_unknown_scan_model(db):
    scan = UnknownScan(uid_hash=calc_hash('UNKNOWN'))
    db.session.add(scan)
    db.session.commit()
    assert UnknownScan.query.filter_by(uid_hash=calc_hash('UNKNOWN')).first() is not None


def test_rfid_tag_unique(db):
    """Two users cannot share the same RFID tag UID hash."""
    user1 = User(name='User1', active=True)
    user2 = User(name='User2', active=True)
    db.session.add_all([user1, user2])
    db.session.flush()
    uid_hash = calc_hash('SHARED_UID')
    db.session.add(RfidTag(user_id=user1.id, uid_hash=uid_hash))
    db.session.commit()
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.session.add(RfidTag(user_id=user2.id, uid_hash=uid_hash))
        db.session.commit()

