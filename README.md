# FSGetraenkeSystem

Digitale Getränkestrichliste für das Büro – betrieben auf einem Raspberry Pi mit RFID-Kartenleser.  
Jeder Benutzer hält seine RFID-Karte ans Lesegerät, wählt ein Getränk aus und der Betrag wird automatisch vom Guthaben abgebucht. Admins verwalten alles über ein Web-Panel.

---

## Inhaltsverzeichnis

1. [Funktionsübersicht](#1-funktionsübersicht)
2. [Schnellstart (Demo-Modus)](#2-schnellstart-demo-modus)
3. [Demo-Modus vs. Produktiv-Modus](#3-demo-modus-vs-produktiv-modus)
4. [Karten anlernen (RFID-Tags zuweisen)](#4-karten-anlernen-rfid-tags-zuweisen)
5. [Admin-Panel im Detail](#5-admin-panel-im-detail)
6. [Kiosk-Modus im Detail](#6-kiosk-modus-im-detail)
7. [Konfiguration (Umgebungsvariablen)](#7-konfiguration-umgebungsvariablen)
8. [Raspberry Pi Setup](#8-raspberry-pi-setup)
9. [JSON-API](#9-json-api)
10. [Tests](#10-tests)

---

## 1. Funktionsübersicht

| Bereich | Feature |
|---|---|
| **Kiosk** | RFID-Karte scannen → Benutzer wird erkannt → Getränk wählen → fertig |
| **Kiosk** | Getränkeliste nach Kaufhäufigkeit sortiert (häufigstes Getränk zuerst) |
| **Kiosk** | Demo-Modus: UID manuell eingeben, kein Lesegerät nötig |
| **Admin** | Dashboard mit Statistiken (aktive Benutzer, Getränke, Gesamt-Guthaben) |
| **Admin** | Benutzer anlegen, bearbeiten, deaktivieren |
| **Admin** | Mehrere RFID-Tags pro Konto hinzufügen und entfernen |
| **Admin** | Unbekannte Scans anzeigen → Karte direkt einem Konto zuweisen oder anlegen |
| **Admin** | Guthaben aufladen (mit optionalem Kommentar) |
| **Admin** | Getränke verwalten (Name, Preis, aktiv/inaktiv) |
| **Admin** | Transaktionshistorie einsehen (blätterbar) |
| **Admin** | Mehrere Admin-Konten anlegen und löschen |
| **Admin** | Eigenes Passwort ändern |
| **API** | JSON-Endpunkt zum Identifizieren eines Benutzers per UID |

---

## 2. Schnellstart (Demo-Modus)

Kein Raspberry Pi, kein Lesegerät nötig – der Demo-Modus läuft auf jedem Rechner.

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Anwendung starten
python run.py
```

Öffne dann im Browser:

| URL | Beschreibung |
|---|---|
| http://localhost:5000/ | Kiosk-Modus |
| http://localhost:5000/admin/ | Admin-Panel |

**Standard-Zugangsdaten Admin-Panel:** `admin` / *(zufälliges Passwort wird beim ersten Start in der Konsole ausgegeben)*

> **Tipp:** Setze `ADMIN_PASSWORD=admin` als Umgebungsvariable, um beim Entwickeln ein festes Passwort zu verwenden.

---

## 3. Demo-Modus vs. Produktiv-Modus

Der Modus wird beim Start in der Konsole ausgegeben, z. B.:

```
INFO  RFID-Modus: DEMO – manuelle UID-Eingabe im Kiosk-Formular (kein Lesegerät erforderlich).
```

oder:

```
INFO  RFID-Modus: PRODUKTIV – echtes RC522-Lesegerät wird verwendet.
```

### Demo-Modus (`RFID_ENABLED=false`, Standard)

- Kein Hardware-Lesegerät erforderlich.
- Im Kiosk erscheint ein Eingabefeld, in das eine RFID-UID manuell eingegeben wird.
- Optional: `RFID_DEMO_UID=<uid>` setzen – dann wird diese UID automatisch ohne Eingabe verwendet (ideal für Vorführungen und Tests).

```bash
# Demo mit fester UID starten
RFID_DEMO_UID=1234567890 python run.py
```

### Produktiv-Modus (`RFID_ENABLED=true`)

- Liest echte Karten vom angeschlossenen RC522-RFID-Modul (Raspberry Pi).
- Erfordert die `mfrc522`-Bibliothek und aktiviertes SPI-Interface.
- Siehe [Raspberry Pi Setup](#8-raspberry-pi-setup).

---

## 4. Karten anlernen (RFID-Tags zuweisen)

Es gibt drei Wege, eine RFID-Karte mit einem Benutzer zu verknüpfen:

### Weg 1 – Beim Anlegen eines neuen Benutzers

1. Admin-Panel → **Benutzer** → **Neuer Benutzer**
2. Name, Startguthaben und optional direkt die RFID-UID eingeben.
3. Speichern – Karte ist sofort aktiv.

### Weg 2 – Nachträglich über die Benutzer-Detailseite

1. Admin-Panel → **Benutzer** → Benutzer anklicken
2. Im Abschnitt **RFID-Tags** eine neue UID eingeben und auf **Tag hinzufügen** klicken.
3. Ein Benutzer kann beliebig viele Tags haben (z. B. Karte + Schlüsselanhänger).

Um eine Karte zu entfernen, einfach auf **Entfernen** neben dem jeweiligen Tag klicken.

### Weg 3 – Über unbekannte Scans (empfohlen für echte Hardware)

Wenn jemand eine noch nicht angelernte Karte ans Lesegerät hält, wird sie als **Unbekannter Scan** gespeichert.

1. Admin-Panel → **Benutzer** – oben erscheint eine Liste der unbekannten Scans.
2. Pro Eintrag gibt es zwei Optionen:
   - **Neues Konto erstellen**: Führt direkt zum Formular „Neuer Benutzer" mit vorausgefüllter UID.
   - **Vorhandenem Konto zuweisen**: Karte einem bestehenden Benutzer hinzufügen.
3. Alternativ kann ein Eintrag auch **verworfen** werden.

> **Tipp im Demo-Modus:** Im Kiosk einfach eine neue (noch nicht zugewiesene) UID eingeben – sie erscheint dann in der Liste der unbekannten Scans.

---

## 5. Admin-Panel im Detail

Erreichbar unter `/admin/` (Login erforderlich).

### Dashboard

Zeigt eine Übersicht mit:
- Anzahl aktiver Benutzer und Getränke
- Summe aller Guthaben
- Die letzten 10 Transaktionen

### Benutzer

- **Übersicht** (`/admin/users`): Alle Benutzer alphabetisch + Liste unbekannter Scans
- **Detail** (`/admin/users/<id>`): Transaktionshistorie des Benutzers, alle zugewiesenen RFID-Tags
- **Anlegen** (`/admin/users/new`): Name, Startguthaben, optional RFID-UID
- **Bearbeiten**: Name und Aktiv-Status ändern
- **Guthaben aufladen**: Betrag in Cent + optionaler Kommentar

### Getränke

- **Übersicht** (`/admin/drinks`): Alle Getränke mit Preis und Status
- **Anlegen / Bearbeiten**: Name, Preis (in Cent), aktiv/inaktiv
- Inaktive Getränke erscheinen nicht im Kiosk

### Transaktionen

- **Alle Transaktionen** (`/admin/transactions`): Paginierte Gesamtübersicht aller Käufe und Aufladungen

### Admins

- **Übersicht** (`/admin/admins`): Alle Admin-Konten
- **Neuer Admin**: Weitere Admin-Konten anlegen
- **Passwort ändern**: Eigenes Passwort ändern
- **Löschen**: Admin-Konto löschen (eigener Account und letzter verbliebener Admin sind geschützt)

---

## 6. Kiosk-Modus im Detail

Erreichbar unter `/` (kein Login nötig).

### Ablauf

```
Startseite  →  RFID scannen  →  Getränk wählen  →  Bestätigung
```

1. **Startseite**: Wartet auf einen RFID-Scan (Demo: Eingabefeld für UID).
2. **Scan**: UID wird geprüft.
   - Bekannte, aktive Karte → Getränkeauswahl
   - Inaktives Konto → Fehlermeldung, zurück zur Startseite
   - Unbekannte Karte → wird als unbekannter Scan gespeichert, Fehlermeldung
3. **Getränkeauswahl**: Zeigt alle aktiven Getränke, sortiert nach Kaufhäufigkeit des Benutzers.
4. **Kauf**: Betrag wird vom Guthaben abgezogen, Transaktion gespeichert, Bestätigungsseite.
5. **Abbrechen**: Jederzeit über `/cancel` möglich.

---

## 7. Konfiguration (Umgebungsvariablen)

Eine vollständig kommentierte Vorlage ist in [`.env.example`](.env.example) enthalten.  
Kopiere sie nach `.env` und passe die Werte an, oder setze die Variablen direkt in der Shell.

| Variable | Standard | Beschreibung |
|---|---|---|
| `SECRET_KEY` | *(zufällig, nicht persistent)* | Flask-Session-Schlüssel. **In Produktion immer setzen!** |
| `DATABASE_URL` | `sqlite:///getraenke.db` | Datenbank-URL (SQLite oder PostgreSQL) |
| `ADMIN_USERNAME` | `admin` | Benutzername des initialen Admin-Accounts |
| `ADMIN_PASSWORD` | *(zufällig, wird in Konsole ausgegeben)* | Passwort des initialen Admins |
| `RFID_ENABLED` | `false` | `true` → echte RC522-Hardware; `false` → Demo-Modus |
| `RFID_DEMO_UID` | *(leer)* | Im Demo-Modus automatisch verwendete UID (leer = manuelle Eingabe) |
| `MINIMUM_BALANCE_CENTS` | `0` | Mindestkontostand nach Kauf in Cent. `0` = kein negativer Saldo; z. B. `-500` = bis zu 5 € Schulden erlaubt |

> **Wichtig:** `SECRET_KEY` und `ADMIN_PASSWORD` sollten in Produktion immer als Umgebungsvariablen gesetzt werden – niemals fest im Code hinterlegen.

---

## 8. Raspberry Pi Setup

> 📖 **Vollständige Anleitung:** [`docs/raspberry-pi-setup.md`](docs/raspberry-pi-setup.md) enthält alle Details inklusive OS-Installation, Verdrahtungsplan, systemd-Dienst und Fehlersuche.

### Kurzübersicht

#### Voraussetzungen

- Raspberry Pi 3B / 4 / Zero 2 W (40-poliger GPIO, SPI)
- RC522 RFID-Modul (SPI, 3,3 V)
- Raspberry Pi OS (Bookworm, 64-bit empfohlen)

#### RC522 Verdrahtung

> ⚠️ Das RC522-Modul wird mit **3,3 V** betrieben – niemals 5 V anschließen!

| RC522-Pin | Raspberry Pi Pin | GPIO |
|---|---|---|
| VCC | Pin 1 | 3,3 V |
| GND | Pin 6 | GND |
| SDA (CS) | Pin 24 | GPIO 8 (CE0) |
| SCK | Pin 23 | GPIO 11 |
| MOSI | Pin 19 | GPIO 10 |
| MISO | Pin 21 | GPIO 9 |
| RST | Pin 22 | GPIO 25 |
| IRQ | – | nicht anschließen |

```
RC522-Modul                        Raspberry Pi GPIO
┌─────────────┐                    ┌──────────────────────────┐
│  [VCC ] ───────────────────────► Pin  1  (3,3 V)            │
│  [GND ] ───────────────────────► Pin  6  (GND)              │
│  [SDA ] ───────────────────────► Pin 24  (GPIO  8 / CE0)    │
│  [SCK ] ───────────────────────► Pin 23  (GPIO 11 / SCLK)   │
│  [MOSI] ───────────────────────► Pin 19  (GPIO 10 / MOSI)   │
│  [MISO] ◄──────────────────────  Pin 21  (GPIO  9 / MISO)   │
│  [RST ] ───────────────────────► Pin 22  (GPIO 25)          │
└─────────────┘                    └──────────────────────────┘
```

#### Schritte

1. **SPI aktivieren:**
   ```bash
   sudo raspi-config
   # → Interface Options → SPI → Enable
   sudo reboot
   ```

2. **Repository klonen und Abhängigkeiten installieren:**
   ```bash
   git clone https://github.com/ursxf/FSGetraenkeSystem.git
   cd FSGetraenkeSystem
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   pip install mfrc522
   ```

3. **Konfiguration anlegen:**
   ```bash
   cp .env.example .env
   # .env bearbeiten: SECRET_KEY, ADMIN_PASSWORD, RFID_ENABLED=true
   ```

4. **Anwendung starten:**
   ```bash
   source venv/bin/activate
   python run.py
   ```

#### Dauerhaft als systemd-Dienst einrichten

```ini
# /etc/systemd/system/getraenke.service
[Unit]
Description=FSGetraenkeSystem
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/FSGetraenkeSystem
EnvironmentFile=/home/pi/FSGetraenkeSystem/.env
ExecStart=/home/pi/FSGetraenkeSystem/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable getraenke
sudo systemctl start getraenke
```

---

## 9. JSON-API

Der Kiosk stellt einen JSON-Endpunkt bereit, der von externer Hardware oder Skripten genutzt werden kann.

### `POST /api/identify`

Identifiziert einen Benutzer anhand seiner RFID-UID und startet eine Kiosk-Session.

**Request:**
```json
{ "uid": "1234567890" }
```

**Response (200):**
```json
{
  "id": 3,
  "name": "Max Mustermann",
  "balance_euro": 12.50
}
```

**Response (404):**
```json
{ "error": "not_found" }
```

**Response (400):**
```json
{ "error": "uid required" }
```

---

## 10. Tests

```bash
pip install pytest pytest-flask
python -m pytest tests/ -v
```

Die Tests verwenden eine In-Memory-SQLite-Datenbank und benötigen keine Hardware.

