import os
import logging

logger = logging.getLogger(__name__)


class Config:
    # -------------------------------------------------------------------------
    # Flask / Security
    # -------------------------------------------------------------------------
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'change-me-in-production')
    SESSION_COOKIE_SAMESITE: str = 'Strict'
    SESSION_COOKIE_SECURE: bool = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_SECURE: bool = os.environ.get('REMEMBER_COOKIE_SECURE', 'false').lower() == 'true'

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL', 'sqlite:///getraenke.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # -------------------------------------------------------------------------
    # Application behaviour
    # -------------------------------------------------------------------------
    # Seconds before automatic logout in Terminal mode (None = disabled)
    TERMINAL_LOGOUT_TIMEOUT: int = int(os.environ.get('TERMINAL_LOGOUT_TIMEOUT', '30'))
    # Time window in seconds during which a revenue can be cancelled
    QUICK_CANCEL_SEC: int = int(os.environ.get('QUICK_CANCEL_SEC', '60'))
    # Number of favourite products highlighted
    FAVORITES_DISPLAY: int = int(os.environ.get('FAVORITES_DISPLAY', '3'))
    # Timespan (days) used to calculate favourite products
    FAVORITES_DAYS: int = int(os.environ.get('FAVORITES_DAYS', '100'))

    # -------------------------------------------------------------------------
    # RFID / Demo mode
    #
    # RFID_ENABLED=false  →  Demo-Modus (Standard)
    #   • Kein Hardware-Lesegerät erforderlich
    #   • Im Terminal-Login kann eine beliebige UID manuell eingegeben werden
    #   • Optional: RFID_DEMO_UID setzen, damit automatisch eine fest
    #     hinterlegte UID verwendet wird (nützlich für Tests / Vorführungen)
    #
    # RFID_ENABLED=true   →  Produktiv-Modus
    #   • Liest echte Karten vom RC522-Lesegerät (Raspberry Pi)
    #   • RFID_DEMO_UID wird in diesem Modus ignoriert
    # -------------------------------------------------------------------------
    RFID_ENABLED: bool = os.environ.get('RFID_ENABLED', 'false').lower() == 'true'
    RFID_DEMO_UID: str = os.environ.get('RFID_DEMO_UID', '')
