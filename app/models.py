from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class AdminUser(UserMixin, db.Model):
    """Represents a system administrator who can log in to the admin panel."""

    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f"<AdminUser {self.username}>"


class User(db.Model):
    """A person who uses the drink system (identified via RFID card)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    # Balance stored in euro-cents (integer) to avoid floating-point issues.
    balance_cents = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    transactions = db.relationship(
        "Transaction", back_populates="user", lazy="dynamic"
    )
    rfid_tags = db.relationship(
        "RFIDTag", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def balance_euro(self):
        return self.balance_cents / 100

    def __repr__(self):
        return f"<User {self.name} ({self.balance_euro:.2f} €)>"


class Drink(db.Model):
    """A drink available in the system."""

    __tablename__ = "drinks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    # Price stored in euro-cents.
    price_cents = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    transactions = db.relationship(
        "Transaction", back_populates="drink", lazy="dynamic"
    )

    @property
    def price_euro(self):
        return self.price_cents / 100

    def __repr__(self):
        return f"<Drink {self.name} ({self.price_euro:.2f} €)>"


class Transaction(db.Model):
    """Records every purchase or deposit in the system."""

    __tablename__ = "transactions"

    PURCHASE = "purchase"
    DEPOSIT = "deposit"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # drink_id is NULL for deposit transactions.
    drink_id = db.Column(db.Integer, db.ForeignKey("drinks.id"), nullable=True)
    # Signed amount in cents: negative = purchase, positive = deposit.
    amount_cents = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(16), nullable=False)
    note = db.Column(db.String(256), nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", back_populates="transactions")
    drink = db.relationship("Drink", back_populates="transactions")

    @property
    def amount_euro(self):
        return self.amount_cents / 100

    def __repr__(self):
        return f"<Transaction {self.type} {self.amount_euro:.2f} € for user {self.user_id}>"


class RFIDTag(db.Model):
    """An RFID tag/card assigned to a user account."""

    __tablename__ = "rfid_tags"

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship("User", back_populates="rfid_tags")

    def __repr__(self):
        return f"<RFIDTag {self.uid} -> user {self.user_id}>"


class UnknownScan(db.Model):
    """Records an RFID scan of a tag that is not yet assigned to any account."""

    __tablename__ = "unknown_scans"

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(64), unique=True, nullable=False)
    last_seen_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<UnknownScan {self.uid}>"
