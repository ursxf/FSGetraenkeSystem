"""Tests for kiosk routes."""

import pytest
from unittest.mock import patch
from app.models import User, Drink, Transaction, RFIDTag
from app import db as _db


def test_kiosk_index_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"RFID" in response.data


def test_kiosk_index_demo_mode_shows_form(client):
    """In demo mode (RFID_ENABLED=False) the manual UID input form is visible."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Demo-Modus" in response.data
    assert b'name="uid"' in response.data


def test_kiosk_index_rfid_mode_hides_form(app):
    """In hardware mode (RFID_ENABLED=True) the demo form is hidden and
    the EventSource-based scan subscriber is rendered instead of the old
    polling loop."""
    app.config["RFID_ENABLED"] = True
    try:
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert b"Demo-Modus" not in response.data
        assert b"Bitte Karte ans" in response.data
        assert b"EventSource" in response.data
    finally:
        app.config["RFID_ENABLED"] = False


def test_scan_unknown_uid(client):
    response = client.post("/scan", data={"uid": "UNKNOWN999"}, follow_redirects=True)
    assert b"nicht erkannt" in response.data


def test_scan_empty_uid(client):
    response = client.post("/scan", data={"uid": ""}, follow_redirects=True)
    assert b"keine" in response.data.lower() or response.status_code in (200, 302)


def test_scan_known_user_redirects_to_select(client, sample_user, app):
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    response = client.post("/scan", data={"uid": uid}, follow_redirects=False)
    assert response.status_code == 302
    assert "/select" in response.headers["Location"]


def test_select_drink_shows_drinks(client, sample_user, sample_drink, app):
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    client.post("/scan", data={"uid": uid})
    response = client.get("/select")
    assert response.status_code == 200
    assert sample_drink.name.encode() in response.data


def test_select_without_session_redirects(client):
    response = client.get("/select", follow_redirects=False)
    assert response.status_code == 302


def test_purchase_deducts_balance(client, sample_user, sample_drink, app):
    prev_balance = sample_user.balance_cents
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    client.post("/scan", data={"uid": uid})
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


def test_cancel_clears_session(client, sample_user, app):
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    client.post("/scan", data={"uid": uid})
    response = client.get("/cancel", follow_redirects=False)
    assert response.status_code == 302
    # Accessing select should redirect back to index
    response = client.get("/select", follow_redirects=False)
    assert response.status_code == 302


def test_api_identify_success(client, sample_user, app):
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    response = client.post("/api/identify", json={"uid": uid})
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


def test_scan_unknown_uid_recorded(client, app):
    """Unknown scans should be recorded in the UnknownScan table."""
    from app.models import UnknownScan
    client.post("/scan", data={"uid": "BRAND_NEW_TAG"}, follow_redirects=True)
    with app.app_context():
        assert UnknownScan.query.filter_by(uid="BRAND_NEW_TAG").first() is not None


def test_drinks_sorted_by_user_habit(client, sample_user, app):
    """Most-purchased drinks should appear first for a user."""
    with app.app_context():
        drink_a = Drink(name="Apfelsaft", price_cents=100, active=True)
        drink_b = Drink(name="Bionade", price_cents=150, active=True)
        drink_c = Drink(name="Cola", price_cents=120, active=True)
        _db.session.add_all([drink_a, drink_b, drink_c])
        _db.session.flush()
        # User has bought Bionade 3 times, Cola once, Apfelsaft never
        for _ in range(3):
            tx = Transaction(
                user_id=sample_user.id,
                drink_id=drink_b.id,
                amount_cents=-drink_b.price_cents,
                type=Transaction.PURCHASE,
            )
            _db.session.add(tx)
        tx2 = Transaction(
            user_id=sample_user.id,
            drink_id=drink_c.id,
            amount_cents=-drink_c.price_cents,
            type=Transaction.PURCHASE,
        )
        _db.session.add(tx2)
        _db.session.commit()
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid

    client.post("/scan", data={"uid": uid})
    response = client.get("/select")
    assert response.status_code == 200
    content = response.data.decode()
    # Bionade (3 purchases) should come before Cola (1) which comes before Apfelsaft (0)
    assert content.index("Bionade") < content.index("Cola") < content.index("Apfelsaft")


def test_api_last_scan_no_scan(client):
    """Without any scan the endpoint returns uid=null."""
    with patch("app.kiosk.routes.get_last_scan", return_value=None):
        response = client.get("/api/last_scan")
    assert response.status_code == 200
    assert response.get_json() == {"uid": None}


def test_api_last_scan_with_scan(client):
    """When a scan is available the endpoint returns the UID and clears it."""
    with patch("app.kiosk.routes.get_last_scan", return_value="DEADBEEF"):
        response = client.get("/api/last_scan")
    assert response.status_code == 200
    assert response.get_json() == {"uid": "DEADBEEF"}


def test_scan_disables_scanning(client, sample_user, app):
    """Posting to /scan disables the RFID scanner so cards held during
    order processing do not queue up a second order."""
    import app.rfid as rfid_module

    # Start from a known enabled state so the assertion is meaningful.
    rfid_module.enable_scanning()
    with app.app_context():
        tag = RFIDTag.query.filter_by(user_id=sample_user.id).first()
        uid = tag.uid
    client.post("/scan", data={"uid": uid})
    assert not rfid_module._scanning_active


def test_cancel_disables_scanning(client, app):
    """Cancelling the session disables the RFID scanner."""
    import app.rfid as rfid_module

    # Start from a known enabled state so the assertion is meaningful.
    rfid_module.enable_scanning()
    client.get("/cancel")
    assert not rfid_module._scanning_active


def test_api_scan_stream_delivers_uid(app):
    """The SSE endpoint streams the scanned UID as a data event."""
    with patch("app.kiosk.routes.enable_scanning"), \
         patch("app.kiosk.routes.disable_scanning"), \
         patch("app.kiosk.routes.wait_for_scan", return_value="CAFEBABE"):
        client = app.test_client()
        response = client.get("/api/scan_stream")
        # Read body inside the patch context in case the streaming generator
        # is consumed lazily (avoids the real wait_for_scan being called).
        body = response.data
    assert response.status_code == 200
    assert response.content_type.startswith("text/event-stream")
    assert b'"uid": "CAFEBABE"' in body


def test_api_scan_stream_keepalive_then_uid(app):
    """The SSE endpoint sends keepalive comments while waiting, then the UID."""
    call_count = 0

    def _wait_side_effect(timeout=30.0):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return None  # first call → keepalive
        return "BEEFDEAD"  # second call → scan found

    with patch("app.kiosk.routes.enable_scanning"), \
         patch("app.kiosk.routes.disable_scanning"), \
         patch("app.kiosk.routes.wait_for_scan", side_effect=_wait_side_effect):
        client = app.test_client()
        response = client.get("/api/scan_stream")
        # Read response.data inside the patch context so that the streaming
        # generator still sees the mocked wait_for_scan on every iteration.
        body = response.data
    assert b": keepalive" in body
    assert b'"uid": "BEEFDEAD"' in body


def test_purchase_blocked_when_balance_insufficient(client, db, sample_drink, app):
    """Purchase is rejected when the resulting balance would fall below MINIMUM_BALANCE_CENTS."""
    app.config["MINIMUM_BALANCE_CENTS"] = 0
    try:
        poor_user = User(name="Poor User", balance_cents=sample_drink.price_cents - 1)
        db.session.add(poor_user)
        db.session.flush()
        db.session.add(RFIDTag(uid="POORUSER001", user_id=poor_user.id))
        db.session.commit()
        poor_user_id = poor_user.id

        client.post("/scan", data={"uid": "POORUSER001"})
        response = client.post(f"/purchase/{sample_drink.id}", follow_redirects=True)
        assert response.status_code == 200
        assert "Nicht genügend Guthaben".encode() in response.data
        # Balance must not have been changed.
        with app.app_context():
            user = _db.session.get(User, poor_user_id)
            assert user.balance_cents == sample_drink.price_cents - 1
    finally:
        app.config.pop("MINIMUM_BALANCE_CENTS", None)


def test_purchase_allowed_when_balance_exactly_meets_minimum(client, db, sample_drink, app):
    """Purchase succeeds when the resulting balance equals MINIMUM_BALANCE_CENTS exactly."""
    app.config["MINIMUM_BALANCE_CENTS"] = 0
    try:
        exact_user = User(name="Exact User", balance_cents=sample_drink.price_cents)
        db.session.add(exact_user)
        db.session.flush()
        db.session.add(RFIDTag(uid="EXACTUSER001", user_id=exact_user.id))
        db.session.commit()
        exact_user_id = exact_user.id

        client.post("/scan", data={"uid": "EXACTUSER001"})
        response = client.post(f"/purchase/{sample_drink.id}", follow_redirects=True)
        assert response.status_code == 200
        assert sample_drink.name.encode() in response.data
        with app.app_context():
            user = _db.session.get(User, exact_user_id)
            assert user.balance_cents == 0
    finally:
        app.config.pop("MINIMUM_BALANCE_CENTS", None)


def test_purchase_allowed_with_negative_minimum(client, db, sample_drink, app):
    """When MINIMUM_BALANCE_CENTS allows debt, purchases into negative balance succeed."""
    app.config["MINIMUM_BALANCE_CENTS"] = -500
    try:
        zero_user = User(name="Zero User", balance_cents=0)
        db.session.add(zero_user)
        db.session.flush()
        db.session.add(RFIDTag(uid="ZEROUSER001", user_id=zero_user.id))
        db.session.commit()
        zero_user_id = zero_user.id

        client.post("/scan", data={"uid": "ZEROUSER001"})
        response = client.post(f"/purchase/{sample_drink.id}", follow_redirects=True)
        assert response.status_code == 200
        assert sample_drink.name.encode() in response.data
        with app.app_context():
            user = _db.session.get(User, zero_user_id)
            assert user.balance_cents == -sample_drink.price_cents
    finally:
        app.config.pop("MINIMUM_BALANCE_CENTS", None)


def test_select_drink_marks_unaffordable(client, db, app):
    """Drinks the user cannot afford are rendered with the disabled attribute."""
    app.config["MINIMUM_BALANCE_CENTS"] = 0
    try:
        broke_user = User(name="Broke User", balance_cents=10)
        db.session.add(broke_user)
        db.session.flush()
        db.session.add(RFIDTag(uid="BROKEUSER001", user_id=broke_user.id))
        expensive = Drink(name="Champagner", price_cents=99999, active=True)
        db.session.add(expensive)
        db.session.commit()

        client.post("/scan", data={"uid": "BROKEUSER001"})
        response = client.get("/select")
        assert response.status_code == 200
        assert b"disabled" in response.data
        assert b"Champagner" in response.data
    finally:
        app.config.pop("MINIMUM_BALANCE_CENTS", None)
