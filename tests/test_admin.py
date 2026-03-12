"""Tests for admin routes."""

import pytest
from app.models import User, Drink, Transaction, AdminUser
from werkzeug.security import generate_password_hash
from app import db as _db


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_login_page_loads(client):
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert b"Anmelden" in response.data


def test_login_with_wrong_password(client):
    response = client.post(
        "/admin/login",
        data={"username": "testadmin", "password": "wrong"},
        follow_redirects=True,
    )
    assert "Ungültige Anmeldedaten".encode() in response.data


def test_login_success(client):
    response = client.post(
        "/admin/login",
        data={"username": "testadmin", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_protected_route_redirects_unauthenticated(client):
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_logout(auth_client):
    response = auth_client.get("/admin/logout", follow_redirects=True)
    assert b"Erfolgreich abgemeldet" in response.data


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def test_dashboard_loads(auth_client):
    response = auth_client.get("/admin/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


def test_users_list_empty(auth_client):
    response = auth_client.get("/admin/users")
    assert response.status_code == 200
    assert b"Noch keine Benutzer" in response.data


def test_create_user(auth_client, app):
    response = auth_client.post(
        "/admin/users/new",
        data={"name": "Erika Muster", "rfid_uid": "ABCD1234", "active": True},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Erika Muster" in response.data
    with app.app_context():
        assert User.query.filter_by(name="Erika Muster").first() is not None


def test_create_user_duplicate_rfid(auth_client, sample_user):
    response = auth_client.post(
        "/admin/users/new",
        data={"name": "Doppel", "rfid_uid": "RFID001", "active": True},
        follow_redirects=True,
    )
    assert b"bereits vergeben" in response.data


def test_edit_user(auth_client, sample_user):
    response = auth_client.post(
        f"/admin/users/{sample_user.id}/edit",
        data={"name": "Max Geändert", "rfid_uid": "RFID001", "active": True},
        follow_redirects=True,
    )
    assert b"aktualisiert" in response.data


def test_user_detail(auth_client, sample_user):
    response = auth_client.get(f"/admin/users/{sample_user.id}")
    assert response.status_code == 200
    assert sample_user.name.encode() in response.data


def test_deposit(auth_client, sample_user, app):
    prev_balance = sample_user.balance_cents
    response = auth_client.post(
        f"/admin/users/{sample_user.id}/deposit",
        data={"amount_cents": 300, "note": "Einzahlung Test"},
        follow_redirects=True,
    )
    assert b"aufgeladen" in response.data
    with app.app_context():
        user = _db.session.get(User, sample_user.id)
        assert user.balance_cents == prev_balance + 300


def test_deposit_invalid_amount(auth_client, sample_user):
    response = auth_client.post(
        f"/admin/users/{sample_user.id}/deposit",
        data={"amount_cents": 0, "note": ""},
        follow_redirects=True,
    )
    # Should show validation error, not redirect to success
    assert b"aufgeladen" not in response.data


# ---------------------------------------------------------------------------
# Drink management
# ---------------------------------------------------------------------------


def test_drinks_list_empty(auth_client):
    response = auth_client.get("/admin/drinks")
    assert response.status_code == 200
    assert "Noch keine Getränke".encode() in response.data


def test_create_drink(auth_client, app):
    response = auth_client.post(
        "/admin/drinks/new",
        data={"name": "Club Mate", "price_cents": 150, "active": True},
        follow_redirects=True,
    )
    assert b"Club Mate" in response.data
    with app.app_context():
        assert Drink.query.filter_by(name="Club Mate").first() is not None


def test_edit_drink(auth_client, sample_drink):
    response = auth_client.post(
        f"/admin/drinks/{sample_drink.id}/edit",
        data={"name": "Fritz Kola", "price_cents": 200, "active": True},
        follow_redirects=True,
    )
    assert b"aktualisiert" in response.data


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


def test_transactions_page(auth_client):
    response = auth_client.get("/admin/transactions")
    assert response.status_code == 200
    assert b"Transaktionen" in response.data
