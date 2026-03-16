from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Optional


class ProductForm(FlaskForm):
    id = IntegerField(
        label='ID',
        render_kw={'placeholder': 'id', 'readonly': ''},
    )
    name = StringField(
        label='Name',
        validators=[InputRequired()],
        render_kw={'placeholder': 'name'},
    )
    ean = IntegerField(
        label='EAN',
        validators=[Optional(strip_whitespace=True)],
        render_kw={'placeholder': 'ean'},
    )
    price = IntegerField(
        label='Price',
        validators=[InputRequired()],
        render_kw={'placeholder': 'price'},
    )
    visible = BooleanField(
        label='Visible',
    )
    has_alc = BooleanField(
        label='Has Alcohol',
    )
    is_food = BooleanField(
        label='Is Food',
    )


class UserForm(FlaskForm):
    id = IntegerField(
        label='ID',
        render_kw={'placeholder': 'id', 'readonly': ''},
    )
    name = StringField(
        label='Name',
        validators=[InputRequired()],
        render_kw={'placeholder': 'name'},
    )
    new_tag_uid = StringField(
        label='RFID-Tag UID (beim Erstellen)',
        render_kw={'placeholder': 'RFID UID'},
    )
    pin = PasswordField(
        label='PIN',
        render_kw={'placeholder': 'pin'},
    )
    unset_pin = BooleanField(
        label='Unset PIN',
    )
    isop = BooleanField(
        label='Admin',
    )
    active = BooleanField(
        label='Aktiv',
    )


class RfidTagForm(FlaskForm):
    uid = StringField(
        label='RFID-Tag UID',
        validators=[InputRequired()],
        render_kw={'placeholder': 'RFID UID'},
    )
    submit = SubmitField(label='Tag hinzufügen')


class BalanceForm(FlaskForm):
    amount = DecimalField(
        label='Amount',
        validators=[InputRequired()],
        render_kw={'placeholder': '0.00'},
    )
    comment = StringField(
        label='Kommentar',
        render_kw={'placeholder': 'optional'},
    )
    recharge = SubmitField(label='Recharge')
    charge = SubmitField(label='Charge')


class AdminForm(FlaskForm):
    """Form to create a new admin account."""
    name = StringField(
        label='Benutzername',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Benutzername'},
    )
    pin = PasswordField(
        label='PIN',
        validators=[InputRequired()],
        render_kw={'placeholder': 'PIN'},
    )
    confirm_pin = PasswordField(
        label='PIN bestätigen',
        validators=[InputRequired()],
        render_kw={'placeholder': 'PIN bestätigen'},
    )
    submit = SubmitField(label='Admin anlegen')


class ChangePasswordForm(FlaskForm):
    """Form to change the current admin's own password."""
    old_pin = PasswordField(
        label='Aktuelles Passwort',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Aktuelles Passwort'},
    )
    new_pin = PasswordField(
        label='Neues Passwort',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Neues Passwort'},
    )
    confirm_pin = PasswordField(
        label='Passwort bestätigen',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Passwort bestätigen'},
    )
    submit = SubmitField(label='Passwort ändern')
