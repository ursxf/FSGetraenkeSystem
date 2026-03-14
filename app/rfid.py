"""RFID reader abstraction.

On a real Raspberry Pi with an RC522 reader, set RFID_ENABLED=true in the
environment.  When RFID is disabled (development / demo mode) the module
exposes a stub that simply returns a configurable UID so the kiosk flow can
still be exercised without hardware.
"""

import os
import time
import threading

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

# Thread-safe storage for the most recently scanned UID.
_lock = threading.Lock()
_last_uid: str | None = None
_last_uid_time: float = 0.0
_reader_started: bool = False


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


def get_last_scan(max_age_seconds: float = 30.0) -> str | None:
    """Return and clear the most recently scanned UID.

    Returns the UID only if it was recorded within *max_age_seconds*.
    After returning the value it is cleared so the same scan is not
    delivered twice.
    """
    global _last_uid, _last_uid_time
    with _lock:
        if _last_uid and (time.monotonic() - _last_uid_time) <= max_age_seconds:
            uid = _last_uid
            _last_uid = None
            _last_uid_time = 0.0
            return uid
    return None


def _rfid_worker() -> None:  # pragma: no cover
    """Background thread: continuously reads RFID cards and stores the last UID.

    ``read_uid()`` blocks until a card is presented when using real hardware,
    so this loop does not busy-wait.  A short sleep after each scan prevents
    the same card from being recorded multiple times in rapid succession.
    """
    global _last_uid, _last_uid_time
    while True:
        uid = read_uid()
        if uid:
            with _lock:
                _last_uid = uid
                _last_uid_time = time.monotonic()
            # Brief pause so one physical tap is not recorded as multiple scans.
            time.sleep(0.5)


def start_background_reader() -> None:
    """Start the background RFID reader thread.

    Only starts when real hardware is available (``_USE_REAL=True``).
    Safe to call multiple times – subsequent calls are no-ops once the
    thread is already running.
    """
    global _reader_started
    if not _USE_REAL or _reader_started:  # pragma: no cover
        return
    # pragma: no cover
    _reader_started = True
    thread = threading.Thread(target=_rfid_worker, name="rfid-reader", daemon=True)
    thread.start()
