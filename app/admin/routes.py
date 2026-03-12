from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app import db, login_manager
from app.models import AdminUser, User, Drink, Transaction
from app.admin import admin_bp
from app.admin.forms import LoginForm, UserForm, DrinkForm, DepositForm


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
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@login_required
def user_new():
    form = UserForm()
    if form.validate_on_submit():
        rfid = form.rfid_uid.data.strip() if form.rfid_uid.data else None
        if rfid and User.query.filter_by(rfid_uid=rfid).first():
            flash("Diese RFID UID ist bereits vergeben.", "danger")
            return render_template("admin/user_form.html", form=form, title="Neuer Benutzer")
        user = User(
            name=form.name.data.strip(),
            rfid_uid=rfid or None,
            active=form.active.data,
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Benutzer '{user.name}' wurde erstellt.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, title="Neuer Benutzer")


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
        rfid = form.rfid_uid.data.strip() if form.rfid_uid.data else None
        conflict = (
            User.query.filter_by(rfid_uid=rfid).first()
            if rfid
            else None
        )
        if conflict and conflict.id != user.id:
            flash("Diese RFID UID ist bereits vergeben.", "danger")
            return render_template(
                "admin/user_form.html", form=form, title=f"{user.name} bearbeiten"
            )
        user.name = form.name.data.strip()
        user.rfid_uid = rfid or None
        user.active = form.active.data
        db.session.commit()
        flash(f"Benutzer '{user.name}' wurde aktualisiert.", "success")
        return redirect(url_for("admin.user_detail", user_id=user.id))
    return render_template(
        "admin/user_form.html", form=form, title=f"{user.name} bearbeiten"
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
