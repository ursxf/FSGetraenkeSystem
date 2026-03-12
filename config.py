import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///getraenke.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Admin credentials (override via environment variables)
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
    # RFID: set to True to use real hardware, False for demo/simulation mode
    RFID_ENABLED = os.environ.get("RFID_ENABLED", "false").lower() == "true"
