from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login_manager
from app.models import AdminUser, User, Drink, Transaction, RFIDTag, UnknownScan
from app.admin import admin_bp
from app.admin.forms import LoginForm, UserForm, DrinkForm, DepositForm, AdminUserForm


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(AdminUser, int(user_id))


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Ungültige Anmeldedaten.", "danger")
    return render_template("admin/login.html", form=form)


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Erfolgreich abgemeldet.", "success")
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@admin_bp.route("/")
@login_required
def dashboard():
    user_count = User.query.filter_by(active=True).count()
    drink_count = Drink.query.filter_by(active=True).count()
    recent_transactions = (
        Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    )
    total_balance = db.session.query(db.func.sum(User.balance_cents)).scalar() or 0
    return render_template(
        "admin/dashboard.html",
        user_count=user_count,
        drink_count=drink_count,
        recent_transactions=recent_transactions,
        total_balance_euro=total_balance / 100,
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


@admin_bp.route("/users")
@login_required
def users():
    all_users = User.query.order_by(User.name).all()
    unknown_scans = (
        UnknownScan.query.order_by(UnknownScan.last_seen_at.desc()).limit(10).all()
    )
    return render_template("admin/users.html", users=all_users, unknown_scans=unknown_scans)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
def user_new():
    form = UserForm()
    if request.method == "GET":
        prefill_uid = request.args.get("prefill_uid", "").strip()
        if prefill_uid:
            form.rfid_uid.data = prefill_uid
    if form.validate_on_submit():
        rfid = form.rfid_uid.data.strip() if form.rfid_uid.data else None
        if rfid and RFIDTag.query.filter_by(uid=rfid).first():
            flash("Diese RFID UID ist bereits vergeben.", "danger")
            return render_template("admin/user_form.html", form=form, title="Neuer Benutzer", is_new=True)
        initial_balance = (
            form.initial_balance_cents.data
            if form.initial_balance_cents.data is not None
            else 0
        )
        user = User(
            name=form.name.data.strip(),
            balance_cents=initial_balance,
            active=form.active.data,
        )
        db.session.add(user)
        db.session.flush()
        if rfid:
            tag = RFIDTag(uid=rfid, user_id=user.id)
            db.session.add(tag)
            UnknownScan.query.filter_by(uid=rfid).delete()
        if initial_balance != 0:
            tx = Transaction(
                user_id=user.id,
                amount_cents=initial_balance,
                type=Transaction.DEPOSIT,
                note="Startguthaben",
            )
            db.session.add(tx)
        db.session.commit()
        flash(f"Benutzer '{user.name}' wurde erstellt.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Neuer Benutzer", is_new=True)


@admin_bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@login_required
def user_detail(user_id):
    user = db.get_or_404(User, user_id)
    transactions = (
        Transaction.query.filter_by(user_id=user_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return render_template(
        "admin/user_detail.html", user=user, transactions=transactions
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.name = form.name.data.strip()
        user.active = form.active.data
        db.session.commit()
        flash(f"Benutzer '{user.name}' wurde aktualisiert.", "success")
        return redirect(url_for("admin.user_detail", user_id=user.id))
    return render_template(
        "admin/user_form.html", form=form, title=f"{user.name} bearbeiten", is_new=False
    )


@admin_bp.route("/users/<int:user_id>/deposit", methods=["GET", "POST"])
@login_required
def user_deposit(user_id):
    user = db.get_or_404(User, user_id)
    form = DepositForm()
    if form.validate_on_submit():
        amount = form.amount_cents.data
        tx = Transaction(
            user_id=user.id,
            amount_cents=amount,
            type=Transaction.DEPOSIT,
            note=form.note.data or None,
        )
        user.balance_cents += amount
        db.session.add(tx)
        db.session.commit()
        flash(
            f"{amount / 100:.2f} € wurden auf das Konto von '{user.name}' aufgeladen.",
            "success",
        )
        return redirect(url_for("admin.user_detail", user_id=user.id))
    return render_template(
        "admin/deposit_form.html", form=form, user=user
    )


# ---------------------------------------------------------------------------
# Drink management
# ---------------------------------------------------------------------------


@admin_bp.route("/drinks")
@login_required
def drinks():
    all_drinks = Drink.query.order_by(Drink.name).all()
    return render_template("admin/drinks.html", drinks=all_drinks)


@admin_bp.route("/drinks/new", methods=["GET", "POST"])
@login_required
def drink_new():
    form = DrinkForm()
    if form.validate_on_submit():
        drink = Drink(
            name=form.name.data.strip(),
            price_cents=form.price_cents.data,
            active=form.active.data,
        )
        db.session.add(drink)
        db.session.commit()
        flash(f"Getränk '{drink.name}' wurde hinzugefügt.", "success")
        return redirect(url_for("admin.drinks"))
    return render_template("admin/drink_form.html", form=form, title="Neues Getränk")


@admin_bp.route("/drinks/<int:drink_id>/edit", methods=["GET", "POST"])
@login_required
def drink_edit(drink_id):
    drink = db.get_or_404(Drink, drink_id)
    form = DrinkForm(obj=drink)
    if form.validate_on_submit():
        drink.name = form.name.data.strip()
        drink.price_cents = form.price_cents.data
        drink.active = form.active.data
        db.session.commit()
        flash(f"Getränk '{drink.name}' wurde aktualisiert.", "success")
        return redirect(url_for("admin.drinks"))
    return render_template(
        "admin/drink_form.html", form=form, title=f"{drink.name} bearbeiten"
    )


# ---------------------------------------------------------------------------
# Transaction log
# ---------------------------------------------------------------------------


@admin_bp.route("/transactions")
@login_required
def transactions():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Transaction.query.order_by(Transaction.created_at.desc())
        .paginate(page=page, per_page=25)
    )
    return render_template("admin/transactions.html", pagination=pagination)


# ---------------------------------------------------------------------------
# RFID tag management
# ---------------------------------------------------------------------------


@admin_bp.route("/users/<int:user_id>/tags/add", methods=["POST"])
@login_required
def user_tag_add(user_id):
    user = db.get_or_404(User, user_id)
    uid = request.form.get("uid", "").strip()
    if not uid:
        flash("Bitte eine RFID UID eingeben.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user_id))
    if RFIDTag.query.filter_by(uid=uid).first():
        flash("Diese RFID UID ist bereits vergeben.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user_id))
    tag = RFIDTag(uid=uid, user_id=user.id)
    db.session.add(tag)
    UnknownScan.query.filter_by(uid=uid).delete()
    db.session.commit()
    flash(f"Tag '{uid}' wurde hinzugefügt.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/users/<int:user_id>/tags/<int:tag_id>/remove", methods=["POST"])
@login_required
def user_tag_remove(user_id, tag_id):
    tag = db.get_or_404(RFIDTag, tag_id)
    if tag.user_id != user_id:
        flash("Ungültige Anfrage.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user_id))
    uid = tag.uid
    db.session.delete(tag)
    db.session.commit()
    flash(f"Tag '{uid}' wurde entfernt.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


# ---------------------------------------------------------------------------
# Unknown scan management
# ---------------------------------------------------------------------------


@admin_bp.route("/unknown-scans/<int:scan_id>/assign", methods=["POST"])
@login_required
def unknown_scan_assign(scan_id):
    scan = db.get_or_404(UnknownScan, scan_id)
    user_id = request.form.get("user_id", type=int)
    if not user_id:
        flash("Bitte einen Benutzer auswählen.", "danger")
        return redirect(url_for("admin.users"))
    user = db.session.get(User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "danger")
        return redirect(url_for("admin.users"))
    if RFIDTag.query.filter_by(uid=scan.uid).first():
        flash("Diese RFID UID ist bereits vergeben.", "danger")
        db.session.delete(scan)
        db.session.commit()
        return redirect(url_for("admin.users"))
    tag = RFIDTag(uid=scan.uid, user_id=user.id)
    db.session.add(tag)
    db.session.delete(scan)
    db.session.commit()
    flash(f"Tag '{scan.uid}' wurde dem Konto '{user.name}' zugewiesen.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/unknown-scans/<int:scan_id>/dismiss", methods=["POST"])
@login_required
def unknown_scan_dismiss(scan_id):
    scan = db.get_or_404(UnknownScan, scan_id)
    db.session.delete(scan)
    db.session.commit()
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Admin user management
# ---------------------------------------------------------------------------


@admin_bp.route("/admins")
@login_required
def admin_users():
    admins = AdminUser.query.order_by(AdminUser.username).all()
    return render_template("admin/admin_users.html", admins=admins)


@admin_bp.route("/admins/new", methods=["GET", "POST"])
@login_required
def admin_user_new():
    form = AdminUserForm()
    if form.validate_on_submit():
        if AdminUser.query.filter_by(username=form.username.data.strip()).first():
            flash("Dieser Benutzername ist bereits vergeben.", "danger")
            return render_template("admin/admin_user_form.html", form=form)
        admin = AdminUser(
            username=form.username.data.strip(),
            password_hash=generate_password_hash(form.password.data),
        )
        db.session.add(admin)
        db.session.commit()
        flash(f"Admin '{admin.username}' wurde erstellt.", "success")
        return redirect(url_for("admin.admin_users"))
    return render_template("admin/admin_user_form.html", form=form)


@admin_bp.route("/admins/<int:admin_id>/delete", methods=["POST"])
@login_required
def admin_user_delete(admin_id):
    admin = db.get_or_404(AdminUser, admin_id)
    if admin.id == current_user.id:
        flash("Du kannst deinen eigenen Account nicht löschen.", "danger")
        return redirect(url_for("admin.admin_users"))
    if AdminUser.query.count() <= 1:
        flash("Es muss mindestens ein Admin-Account vorhanden sein.", "danger")
        return redirect(url_for("admin.admin_users"))
    username = admin.username
    db.session.delete(admin)
    db.session.commit()
    flash(f"Admin '{username}' wurde gelöscht.", "success")
    return redirect(url_for("admin.admin_users"))

