"""Tests for database models."""

import pytest
from app.models import User, Drink, Transaction


def test_user_balance_property(db):
    user = User(name="Anna", balance_cents=250)
    assert user.balance_euro == pytest.approx(2.50)


def test_user_negative_balance(db):
    user = User(name="Bob", balance_cents=-100)
    assert user.balance_euro == pytest.approx(-1.00)


def test_drink_price_property(db):
    drink = Drink(name="Club Mate", price_cents=150)
    assert drink.price_euro == pytest.approx(1.50)


def test_transaction_amount_property(db):
    # Test via a real persisted transaction
    user = User(name="Tester", balance_cents=0)
    drink = Drink(name="Wasser", price_cents=150)
    db.session.add_all([user, drink])
    db.session.flush()
    tx = Transaction(
        user_id=user.id,
        drink_id=drink.id,
        amount_cents=-150,
        type=Transaction.PURCHASE,
    )
    db.session.add(tx)
    db.session.commit()
    assert tx.amount_euro == pytest.approx(-1.50)


def test_user_repr(db):
    user = User(name="Alice", balance_cents=100)
    assert "Alice" in repr(user)


def test_drink_repr(db):
    drink = Drink(name="Wasser", price_cents=80)
    assert "Wasser" in repr(drink)


def test_transaction_types():
    assert Transaction.PURCHASE == "purchase"
    assert Transaction.DEPOSIT == "deposit"
