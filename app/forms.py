from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Optional


class LoginForm(FlaskForm):
    username = StringField(
        label='Username',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Username', 'autofocus': True},
    )
    pin = PasswordField(
        label='PIN',
        validators=[InputRequired()],
        render_kw={'placeholder': 'PIN'},
    )
    remember = BooleanField(
        label='Remember me',
    )
    submit = SubmitField(
        label='Sign in',
    )


class MainForm(FlaskForm):
    ean = IntegerField(
        label='EAN',
        validators=[Optional()],
        render_kw={'placeholder': 'EAN', 'autofocus': True},
    )


class PinForm(FlaskForm):
    old_pin = PasswordField(
        label='Old PIN',
        validators=[InputRequired()],
        render_kw={'placeholder': 'PIN'},
    )
    unset_pin = BooleanField(
        label='Unset PIN',
    )
    new_pin = PasswordField(
        label='New PIN',
        render_kw={'placeholder': 'PIN'},
    )
    confirm_pin = PasswordField(
        label='Confirm new PIN',
        render_kw={'placeholder': 'PIN'},
    )
    change_pin = SubmitField(
        label='Change PIN',
    )

