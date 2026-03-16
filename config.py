import os
import secrets
import logging

logger = logging.getLogger(__name__)


def _get_secret_key() -> str:
    key = os.environ.get("SECRET_KEY")
    if not key:
        # In production, always set SECRET_KEY via environment variable.
        # During development a random key is generated (sessions won't
        # survive restarts).
        key = secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY is not set. A random key has been generated; "
            "sessions will not persist across restarts. "
            "Set the SECRET_KEY environment variable in production."
        )
    return key


class Config:
    # -------------------------------------------------------------------------
    # Flask / Security
    # -------------------------------------------------------------------------
    SECRET_KEY: str = _get_secret_key()

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "sqlite:///getraenke.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # -------------------------------------------------------------------------
    # Admin credentials
    # Only used on first start to seed the built-in admin account.
    # Override via environment variables; if ADMIN_PASSWORD is left empty, a
    # random one-time password is printed to the console on first start.
    # -------------------------------------------------------------------------
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")

    # -------------------------------------------------------------------------
    # Kiosk purchase rules
    #
    # MINIMUM_BALANCE_CENTS controls how low a user's balance may fall after a
    # purchase.  Set to 0 (default) to disallow negative balance entirely.
    # Set to e.g. -500 to allow users to go up to 5 € into debt.
    # -------------------------------------------------------------------------
    MINIMUM_BALANCE_CENTS: int = int(
        os.environ.get("MINIMUM_BALANCE_CENTS", "0")
    )

    # -------------------------------------------------------------------------
    # RFID / Demo mode
    #
    # RFID_ENABLED=false  →  Demo-Modus (Standard)
    #   • Kein Hardware-Lesegerät erforderlich
    #   • Im Kiosk-Formular kann eine beliebige UID manuell eingegeben werden
    #   • Optional: RFID_DEMO_UID setzen, damit das Kiosk automatisch eine
    #     fest hinterlegte UID verwendet (nützlich für Tests / Vorführungen)
    #
    # RFID_ENABLED=true   →  Produktiv-Modus
    #   • Liest echte Karten vom RC522-Lesegerät (Raspberry Pi)
    #   • RFID_DEMO_UID wird in diesem Modus ignoriert
    # -------------------------------------------------------------------------
    RFID_ENABLED: bool = os.environ.get("RFID_ENABLED", "false").lower() == "true"
    # UID, die im Demo-Modus automatisch verwendet wird (leer = manuelle Eingabe)
    RFID_DEMO_UID: str = os.environ.get("RFID_DEMO_UID", "")


def log_startup_mode() -> None:
    """Log whether the application is running in demo or production mode.

    Call this once after the app is created so the operator can see at a
    glance which mode is active.
    """
    if Config.RFID_ENABLED:
        logger.info(
            "RFID-Modus: PRODUKTIV – echtes RC522-Lesegerät wird verwendet."
        )
    else:
        if Config.RFID_DEMO_UID:
            logger.info(
                "RFID-Modus: DEMO – feste Demo-UID '%s' wird verwendet "
                "(kein Lesegerät erforderlich).",
                Config.RFID_DEMO_UID,
            )
        else:
            logger.info(
                "RFID-Modus: DEMO – manuelle UID-Eingabe im Kiosk-Formular "
                "(kein Lesegerät erforderlich)."
            )
