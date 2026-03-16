"""Tests for database models."""

import pytest
from app.db.models import User, Product, Revenue
from app.db.helpers import get_balance
from app.helpers import calc_hash, format_currency


def test_user_has_card_field(db):
    user = User(name='Anna', card=calc_hash('MY_CARD_UID'))
    _db = db
    _db.session.add(user)
    _db.session.commit()
    assert user.card is not None


def test_user_isop_default_false(db):
    user = User(name='Bob')
    db.session.add(user)
    db.session.commit()
    assert user.isop is False


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
