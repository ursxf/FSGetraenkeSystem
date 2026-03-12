"""RFID reader abstraction.

On a real Raspberry Pi with an RC522 reader, set RFID_ENABLED=true in the
environment.  When RFID is disabled (development / demo mode) the module
exposes a stub that simply returns a configurable UID so the kiosk flow can
still be exercised without hardware.
"""

import os

_RFID_ENABLED = os.environ.get("RFID_ENABLED", "false").lower() == "true"

if _RFID_ENABLED:
    try:
        from mfrc522 import SimpleMFRC522  # type: ignore

        _reader = SimpleMFRC522()
        _USE_REAL = True
    except Exception:  # pragma: no cover
        _USE_REAL = False
else:
    _USE_REAL = False


def read_uid() -> str | None:
    """Block until an RFID card is presented and return its UID as a string.

    Returns ``None`` if reading failed or hardware is unavailable.
    """
    if _USE_REAL:  # pragma: no cover
        try:
            uid, _ = _reader.read()
            return str(uid)
        except Exception:
            return None
    # Simulation: return the value of the RFID_DEMO_UID env var (if set).
    demo_uid = os.environ.get("RFID_DEMO_UID")
    return demo_uid if demo_uid else None
