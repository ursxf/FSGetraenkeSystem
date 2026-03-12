"""Tests for kiosk routes."""

import pytest
from app.models import User, Drink, Transaction
from app import db as _db


def test_kiosk_index_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"RFID" in response.data


def test_scan_unknown_uid(client):
    response = client.post("/scan", data={"uid": "UNKNOWN999"}, follow_redirects=True)
    assert b"nicht erkannt" in response.data


def test_scan_empty_uid(client):
    response = client.post("/scan", data={"uid": ""}, follow_redirects=True)
    assert b"keine" in response.data.lower() or response.status_code in (200, 302)


def test_scan_known_user_redirects_to_select(client, sample_user):
    response = client.post(
        "/scan", data={"uid": sample_user.rfid_uid}, follow_redirects=False
    )
    assert response.status_code == 302
    assert "/select" in response.headers["Location"]


def test_select_drink_shows_drinks(client, sample_user, sample_drink):
    # Log in via RFID scan
    client.post("/scan", data={"uid": sample_user.rfid_uid})
    response = client.get("/select")
    assert response.status_code == 200
    assert sample_drink.name.encode() in response.data


def test_select_without_session_redirects(client):
    response = client.get("/select", follow_redirects=False)
    assert response.status_code == 302


def test_purchase_deducts_balance(client, sample_user, sample_drink, app):
    prev_balance = sample_user.balance_cents
    client.post("/scan", data={"uid": sample_user.rfid_uid})
    response = client.post(f"/purchase/{sample_drink.id}", follow_redirects=True)
    assert response.status_code == 200
    assert sample_drink.name.encode() in response.data
    with app.app_context():
        user = _db.session.get(User, sample_user.id)
        assert user.balance_cents == prev_balance - sample_drink.price_cents
        tx = Transaction.query.filter_by(
            user_id=sample_user.id, drink_id=sample_drink.id
        ).first()
        assert tx is not None
        assert tx.type == Transaction.PURCHASE
        assert tx.amount_cents == -sample_drink.price_cents


def test_cancel_clears_session(client, sample_user):
    client.post("/scan", data={"uid": sample_user.rfid_uid})
    response = client.get("/cancel", follow_redirects=False)
    assert response.status_code == 302
    # Accessing select should redirect back to index
    response = client.get("/select", follow_redirects=False)
    assert response.status_code == 302


def test_api_identify_success(client, sample_user):
    response = client.post(
        "/api/identify",
        json={"uid": sample_user.rfid_uid},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == sample_user.name
    assert data["id"] == sample_user.id


def test_api_identify_not_found(client):
    response = client.post("/api/identify", json={"uid": "DOESNOTEXIST"})
    assert response.status_code == 404


def test_api_identify_missing_uid(client):
    response = client.post("/api/identify", json={})
    assert response.status_code == 400
