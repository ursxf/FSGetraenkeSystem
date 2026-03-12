import os
import secrets
import logging

logger = logging.getLogger(__name__)

_WEAK_SECRET = "change-me-in-production"


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
    SECRET_KEY: str = _get_secret_key()
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "sqlite:///getraenke.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # Admin credentials (override via environment variables in production)
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "")
    # RFID: set to True to use real hardware, False for demo/simulation mode
    RFID_ENABLED: bool = os.environ.get("RFID_ENABLED", "false").lower() == "true"
