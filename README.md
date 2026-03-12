# FSGetraenkeSystem

Digitale Getränkestrichliste für das Büro – betrieben auf einem Raspberry Pi mit RFID-Kartenleser.

## Funktionen

- **Kiosk-Modus**: Karte ans RFID-Lesegerät halten → Benutzer wird erkannt → Getränk auswählen → fertig
- **Admin-Panel**:
  - Benutzer verwalten (anlegen, bearbeiten, RFID-Karte zuweisen)
  - Guthaben aufladen
  - Getränke verwalten (Name, Preis, aktiv/inaktiv)
  - Transaktionshistorie einsehen

## Schnellstart (Windows)

> **Voraussetzung:** Python 3.11+ muss installiert sein. Download: https://www.python.org/downloads/

### 1. Virtuelle Umgebung erstellen und Abhängigkeiten installieren

**PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**CMD:**
```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 2. Konfigurationsdatei anlegen

```powershell
# PowerShell
Copy-Item .env.example .env
```
```cmd
:: CMD
copy .env.example .env
```

Die `.env`-Datei enthält alle Einstellungen (Admin-Passwort, Datenbank usw.).  
Die Standardwerte aus `.env.example` sind direkt für lokale Tests geeignet.

### 3. Anwendung starten

```powershell
python run.py
```

Öffne dann im Browser:
- **Kiosk**: http://localhost:5000/
- **Admin-Panel**: http://localhost:5000/admin/  (Standard: `admin` / `admin` – aus der `.env`-Datei)

---

## Schnellstart (Linux / macOS / Raspberry Pi)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

---

## Konfiguration (.env-Datei)

Kopiere `.env.example` nach `.env` und passe die Werte an:

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECRET_KEY` | `change-me-before-using-in-production` | Flask Secret Key |
| `DATABASE_URL` | `sqlite:///getraenke.db` | Datenbank-URL |
| `ADMIN_USERNAME` | `admin` | Admin-Benutzername |
| `ADMIN_PASSWORD` | `admin` | Admin-Passwort |
| `RFID_ENABLED` | `false` | `true` für echte RC522-Hardware |

Alternativ können die Variablen auch direkt als Umgebungsvariablen gesetzt werden:

**PowerShell:**
```powershell
$env:ADMIN_PASSWORD = "meinPasswort"
python run.py
```

**CMD:**
```cmd
set ADMIN_PASSWORD=meinPasswort
python run.py
```

**Linux/macOS:**
```bash
export ADMIN_PASSWORD="meinPasswort"
python run.py
```

## Tests

```powershell
# PowerShell / CMD / bash
pip install pytest pytest-flask
python -m pytest tests/ -v
```

## Raspberry Pi Setup

1. RFID-Modul (RC522) anschließen und `mfrc522` installieren:
   ```bash
   pip install mfrc522
   ```
2. In der `.env`-Datei `RFID_ENABLED=true` setzen.
3. Anwendung starten.

Im Demo-Modus (ohne Hardware, z. B. unter Windows) kann die RFID-UID manuell im Kiosk-Formular eingegeben werden.
