# FSGetraenkeSystem

Digitale Getränkestrichliste für das Büro – betrieben auf einem Raspberry Pi mit RFID-Kartenleser.

## Funktionen

- **Kiosk-Modus**: Karte ans RFID-Lesegerät halten → Benutzer wird erkannt → Getränk auswählen → fertig
- **Admin-Panel**:
  - Benutzer verwalten (anlegen, bearbeiten, RFID-Karte zuweisen)
  - Guthaben aufladen
  - Getränke verwalten (Name, Preis, aktiv/inaktiv)
  - Transaktionshistorie einsehen

## Schnellstart

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python run.py
```

Öffne dann:
- **Kiosk**: http://localhost:5000/
- **Admin-Panel**: http://localhost:5000/admin/  (Standard: `admin` / `admin`)

## Konfiguration (Umgebungsvariablen)

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask Secret Key |
| `DATABASE_URL` | `sqlite:///getraenke.db` | Datenbank-URL |
| `ADMIN_USERNAME` | `admin` | Admin-Benutzername |
| `ADMIN_PASSWORD` | `admin` | Admin-Passwort |
| `RFID_ENABLED` | `false` | `true` für echte RC522-Hardware |

## Tests

```bash
pip install pytest pytest-flask
python -m pytest tests/ -v
```

## Raspberry Pi Setup

1. RFID-Modul (RC522) anschließen und `mfrc522` installieren:
   ```bash
   pip install mfrc522
   ```
2. `RFID_ENABLED=true` als Umgebungsvariable setzen.
3. Anwendung starten.

Im Demo-Modus (ohne Hardware) kann die RFID-UID manuell im Kiosk-Formular eingegeben werden.
