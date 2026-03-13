# FSGetraenkeSystem

Digitale Getränkestrichliste für das Büro – betrieben auf einem Raspberry Pi mit RFID-Kartenleser.

## Funktionen

- **Kiosk-Modus**: Karte ans RFID-Lesegerät halten → Benutzer wird erkannt → Getränk auswählen → fertig
- **Admin-Panel**:
  - Benutzer verwalten (anlegen mit Startguthaben, bearbeiten)
  - Mehrere RFID-Tags pro Konto (hinzufügen, entfernen)
  - Unbekannte Scans anzeigen → direkt neues Konto erstellen oder vorhandenem Konto zuweisen
  - Guthaben aufladen
  - Getränke verwalten (Name, Preis, aktiv/inaktiv)
  - Transaktionshistorie einsehen
  - Mehrere Admin-Konten verwalten

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

## Mehrere Admins verwalten

Im Admin-Panel unter **Admins** (Seitenleiste) können weitere Admin-Konten angelegt und gelöscht werden.
Der eigene Account sowie der letzte verbleibende Admin können nicht gelöscht werden.

Alternativ kann der erste Admin auch über Umgebungsvariablen konfiguriert werden (siehe unten).

## Konfiguration (Umgebungsvariablen)

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask Secret Key |
| `DATABASE_URL` | `sqlite:///getraenke.db` | Datenbank-URL |
| `ADMIN_USERNAME` | `admin` | Benutzername des initialen Admins |
| `ADMIN_PASSWORD` | wird in der Konsole angezeigt | Passwort des initialen Admins |
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
