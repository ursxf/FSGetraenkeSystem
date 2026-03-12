from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Benutzername", validators=[DataRequired()])
    password = PasswordField("Passwort", validators=[DataRequired()])
    submit = SubmitField("Anmelden")


class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=128)])
    rfid_uid = StringField("RFID UID", validators=[Optional(), Length(max=64)])
    active = BooleanField("Aktiv", default=True)
    submit = SubmitField("Speichern")


class DrinkForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=128)])
    price_cents = IntegerField(
        "Preis (Cent)",
        validators=[DataRequired(), NumberRange(min=1, message="Preis muss größer als 0 sein.")],
    )
    active = BooleanField("Aktiv", default=True)
    submit = SubmitField("Speichern")


class DepositForm(FlaskForm):
    amount_cents = IntegerField(
        "Betrag (Cent)",
        validators=[DataRequired(), NumberRange(min=1, message="Betrag muss positiv sein.")],
    )
    note = StringField("Notiz", validators=[Optional(), Length(max=256)])
    submit = SubmitField("Guthaben aufladen")
