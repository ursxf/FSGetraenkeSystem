from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session, jsonify

from app import db
from app.models import User, Drink, Transaction, RFIDTag, UnknownScan
from app.kiosk import kiosk_bp


@kiosk_bp.route("/")
def index():
    """Kiosk start screen: waiting for RFID scan."""
    return render_template("kiosk/index.html")


@kiosk_bp.route("/scan", methods=["POST"])
def scan():
    """Receive an RFID UID (posted from hardware or demo form) and identify the user."""
    uid = request.form.get("uid", "").strip()
    if not uid:
        flash("Keine RFID-UID empfangen.", "danger")
        return redirect(url_for("kiosk.index"))

    tag = RFIDTag.query.filter_by(uid=uid).first()
    if tag:
        user = tag.user
        if user.active:
            session["kiosk_user_id"] = user.id
            return redirect(url_for("kiosk.select_drink"))
        flash("Konto ist inaktiv. Bitte wende dich an einen Administrator.", "warning")
        return redirect(url_for("kiosk.index"))

    # Tag not assigned – record so admins can see and act on it
    existing = UnknownScan.query.filter_by(uid=uid).first()
    if existing:
        existing.last_seen_at = datetime.now(timezone.utc)
    else:
        db.session.add(UnknownScan(uid=uid))
    db.session.commit()
    flash("Karte nicht erkannt. Bitte wende dich an einen Administrator.", "warning")
    return redirect(url_for("kiosk.index"))


@kiosk_bp.route("/select")
def select_drink():
    """Show available drinks so the identified user can choose one."""
    user_id = session.get("kiosk_user_id")
    if not user_id:
        return redirect(url_for("kiosk.index"))

    user = db.session.get(User, user_id)
    if not user or not user.active:
        session.pop("kiosk_user_id", None)
        return redirect(url_for("kiosk.index"))

    drinks = Drink.query.filter_by(active=True).order_by(Drink.name).all()
    return render_template("kiosk/select_drink.html", user=user, drinks=drinks)


@kiosk_bp.route("/purchase/<int:drink_id>", methods=["POST"])
def purchase(drink_id):
    """Record a drink purchase for the currently identified user."""
    user_id = session.get("kiosk_user_id")
    if not user_id:
        return redirect(url_for("kiosk.index"))

    user = db.session.get(User, user_id)
    drink = db.session.get(Drink, drink_id)

    if not user or not user.active or not drink or not drink.active:
        flash("Ungültige Auswahl.", "danger")
        return redirect(url_for("kiosk.index"))

    tx = Transaction(
        user_id=user.id,
        drink_id=drink.id,
        amount_cents=-drink.price_cents,
        type=Transaction.PURCHASE,
    )
    user.balance_cents -= drink.price_cents
    db.session.add(tx)
    db.session.commit()

    session.pop("kiosk_user_id", None)
    return render_template("kiosk/confirmation.html", user=user, drink=drink)


@kiosk_bp.route("/cancel")
def cancel():
    """Cancel the current session and return to the start screen."""
    session.pop("kiosk_user_id", None)
    return redirect(url_for("kiosk.index"))


# ---------------------------------------------------------------------------
# JSON API – used by RFID background polling (optional hardware integration)
# ---------------------------------------------------------------------------


@kiosk_bp.route("/api/identify", methods=["POST"])
def api_identify():
    """Identify a user by RFID UID; returns JSON."""
    data = request.get_json(force=True, silent=True) or {}
    uid = str(data.get("uid", "")).strip()
    if not uid:
        return jsonify({"error": "uid required"}), 400

    tag = RFIDTag.query.filter_by(uid=uid).first()
    if not tag or not tag.user.active:
        return jsonify({"error": "not_found"}), 404

    user = tag.user
    session["kiosk_user_id"] = user.id
    return jsonify(
        {
            "id": user.id,
            "name": user.name,
            "balance_euro": user.balance_euro,
        }
    )
