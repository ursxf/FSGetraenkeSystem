# Raspberry Pi Setup-Anleitung – FSGetraenkeSystem

Diese Anleitung führt dich Schritt für Schritt durch die vollständige Einrichtung des FSGetraenkeSystems auf einem Raspberry Pi mit RC522 RFID-Lesegerät.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Betriebssystem installieren](#2-betriebssystem-installieren)
3. [Raspberry Pi konfigurieren](#3-raspberry-pi-konfigurieren)
4. [RC522 RFID-Modul anschließen – Verdrahtungsplan](#4-rc522-rfid-modul-anschließen--verdrahtungsplan)
5. [Software installieren](#5-software-installieren)
6. [Anwendung konfigurieren](#6-anwendung-konfigurieren)
7. [Anwendung starten und testen](#7-anwendung-starten-und-testen)
8. [Dauerhaft als Dienst einrichten (systemd)](#8-dauerhaft-als-dienst-einrichten-systemd)
9. [Autostart des Browsers im Kiosk-Modus](#9-autostart-des-browsers-im-kiosk-modus)
10. [Fehlerbehebung](#10-fehlerbehebung)

---

## 1. Voraussetzungen

### Hardware

| Komponente | Hinweis |
|---|---|
| Raspberry Pi 3B / 3B+ / 4 / Zero 2 W | Jedes Modell mit 40-poligem GPIO-Header und SPI |
| RC522 RFID-Modul | Weit verbreitet, günstig, SPI-Schnittstelle |
| RFID-Karten / -Anhänger (13,56 MHz, ISO 14443A) | Standard-Mifare-Karten funktionieren |
| MicroSD-Karte (≥ 8 GB, Class 10) | |
| Stromversorgung (5 V / 3 A) | Offizielles Netzteil empfohlen |
| Netzwerkzugang (LAN oder WLAN) | Für den ersten Setup |
| Optional: Touchscreen oder Monitor + Keyboard | Für den Kiosk-Betrieb |

### Software

- Raspberry Pi OS Lite oder Desktop (64-bit empfohlen, Bookworm)
- Python 3.11 oder neuer
- Git

---

## 2. Betriebssystem installieren

1. Lade den **Raspberry Pi Imager** herunter: <https://www.raspberrypi.com/software/>
2. Wähle als Betriebssystem: **Raspberry Pi OS (64-bit)** – Lite reicht für Headless-Betrieb.
3. Klicke auf das Zahnrad-Symbol ⚙️ und konfiguriere vorab:
   - Hostname: z. B. `getraenke`
   - SSH aktivieren
   - WLAN-Zugangsdaten (SSID + Passwort)
   - Benutzername / Passwort (Standard: `pi` / `raspberry`)
4. Schreibe das Image auf die MicroSD-Karte.
5. Karte einlegen, Raspberry Pi starten.

> **Headless verbinden:** `ssh pi@getraenke.local` (oder IP-Adresse aus dem Router-DHCP)

---

## 3. Raspberry Pi konfigurieren

### 3.1 System aktualisieren

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 SPI-Schnittstelle aktivieren

Das RC522-Modul kommuniziert über SPI. SPI muss explizit aktiviert werden:

```bash
sudo raspi-config
```

Navigiere zu:

```
Interface Options → SPI → Yes (Enable) → OK → Finish
```

Alternativ direkt über die Kommandozeile:

```bash
sudo raspi-config nonint do_spi 0
```

Anschließend neu starten:

```bash
sudo reboot
```

### 3.3 SPI-Aktivierung prüfen

Nach dem Neustart:

```bash
ls /dev/spi*
# Erwartete Ausgabe:
# /dev/spidev0.0  /dev/spidev0.1
```

```bash
lsmod | grep spi
# Erwartete Ausgabe enthält: spi_bcm2835
```

---

## 4. RC522 RFID-Modul anschließen – Verdrahtungsplan

> ⚠️ **Wichtig:** Das RC522-Modul wird mit **3,3 V** betrieben. Schließe es **niemals** an 5 V an – das beschädigt das Modul dauerhaft.

### Pinbelegung

| RC522-Pin | Raspberry Pi GPIO | Raspberry Pi Pin # | Beschreibung |
|---|---|---|---|
| VCC | 3,3 V | Pin 1 | Versorgungsspannung |
| GND | GND | Pin 6 | Masse |
| SDA (NSS/CS) | GPIO 8 (CE0) | Pin 24 | Chip Select |
| SCK | GPIO 11 | Pin 23 | SPI Clock |
| MOSI | GPIO 10 | Pin 19 | Master Out Slave In |
| MISO | GPIO 9 | Pin 21 | Master In Slave Out |
| RST | GPIO 25 | Pin 22 | Reset |
| IRQ | – | – | Nicht angeschlossen (optional) |

### ASCII-Verdrahtungsdiagramm

```
RC522-Modul                        Raspberry Pi 40-Pin GPIO
┌─────────────┐                    ┌─────────────────────────┐
│             │                    │  (Vorderseite des Pi)   │
│  [VCC ] ───────────────────────► Pin  1  (3,3 V)           │
│  [GND ] ───────────────────────► Pin  6  (GND)             │
│  [SDA ] ───────────────────────► Pin 24  (GPIO  8 / CE0)   │
│  [SCK ] ───────────────────────► Pin 23  (GPIO 11 / SCLK)  │
│  [MOSI] ───────────────────────► Pin 19  (GPIO 10 / MOSI)  │
│  [MISO] ◄──────────────────────  Pin 21  (GPIO  9 / MISO)  │
│  [RST ] ───────────────────────► Pin 22  (GPIO 25)         │
│  [IRQ ] ── (nicht anschließen)   │                         │
│             │                    └─────────────────────────┘
└─────────────┘
```

### GPIO-Pinout des Raspberry Pi (relevanter Ausschnitt)

```
RC522 VCC ►  3,3 V  [1] [2]  5 V
                GPIO 2  [3] [4]  5 V
                GPIO 3  [5] [6]  GND  ◄── RC522 GND
                GPIO 4  [7] [8]  GPIO 14
                   GND  [9][10]  GPIO 15
               GPIO 17 [11][12]  GPIO 18
               GPIO 27 [13][14]  GND
               GPIO 22 [15][16]  GPIO 23
                3,3 V  [17][18]  GPIO 24
RC522 MOSI ► GPIO 10 [19][20]  GND
RC522 MISO ◄ GPIO  9 [21][22]  GPIO 25 ◄── RC522 RST
RC522 SCK  ► GPIO 11 [23][24]  GPIO  8 ◄── RC522 SDA
                   GND [25][26]  GPIO  7
               GPIO  0 [27][28]  GPIO  1
               GPIO  5 [29][30]  GND
               GPIO  6 [31][32]  GPIO 12
               GPIO 13 [33][34]  GND
               GPIO 19 [35][36]  GPIO 16
               GPIO 26 [37][38]  GPIO 20
                   GND [39][40]  GPIO 21
```

> **Vollständiges Pinout:** <https://pinout.xyz>

### Foto-Referenz der Kabelfarben (Empfehlung)

| Kabel | Farbe |
|---|---|
| VCC (3,3 V) | Rot |
| GND | Schwarz |
| SDA | Gelb |
| SCK | Orange |
| MOSI | Grün |
| MISO | Blau |
| RST | Weiß |

---

## 5. Software installieren

### 5.1 Python 3 und Git sicherstellen

```bash
sudo apt install -y python3 python3-pip python3-venv git
python3 --version   # sollte 3.11+ ausgeben
```

### 5.2 Repository klonen

```bash
cd ~
git clone https://github.com/ursxf/FSGetraenkeSystem.git
cd FSGetraenkeSystem
```

### 5.3 Virtuelle Python-Umgebung anlegen und Abhängigkeiten installieren

```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install mfrc522
```

> **Hinweis:** `mfrc522` ist die Python-Bibliothek für den RC522 und wird nur auf dem Raspberry Pi benötigt. Auf anderen Systemen (Demo-Modus) kann sie weggelassen werden.

---

## 6. Anwendung konfigurieren

### 6.1 `.env`-Datei anlegen

```bash
cp .env.example .env
nano .env
```

Mindestinhalt für den Produktivbetrieb:

```dotenv
SECRET_KEY=ersetze-mich-durch-einen-langen-zufaelligen-string
ADMIN_PASSWORD=dein-sicheres-passwort
RFID_ENABLED=true
# Optional: Datenbankpfad anpassen
# DATABASE_URL=sqlite:////home/pi/FSGetraenkeSystem/getraenke.db
```

Einen sicheren `SECRET_KEY` generieren:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 6.2 Konfigurationsübersicht

| Variable | Wert für Produktivbetrieb | Beschreibung |
|---|---|---|
| `SECRET_KEY` | Zufälliger Hex-String (64 Zeichen) | Flask-Session-Schlüssel |
| `ADMIN_PASSWORD` | Sicheres Passwort | Passwort des ersten Admin-Accounts |
| `RFID_ENABLED` | `true` | Aktiviert das RC522-Lesegerät |
| `DATABASE_URL` | `sqlite:///getraenke.db` | Kann absoluter Pfad sein |

---

## 7. Anwendung starten und testen

### 7.1 Ersten Start durchführen

```bash
source venv/bin/activate
python run.py
```

Erwartete Ausgabe:

```
INFO  RFID-Modus: PRODUKTIV – echtes RC522-Lesegerät wird verwendet.
 * Running on http://0.0.0.0:5000
```

### 7.2 Im Browser öffnen

Auf einem anderen Gerät im selben Netzwerk:

```
http://getraenke.local:5000/       ← Kiosk
http://getraenke.local:5000/admin/ ← Admin-Panel
```

### 7.3 RC522-Verbindung testen

Kurzer Hardware-Test ohne die Hauptanwendung:

```bash
source venv/bin/activate
python3 - <<'EOF'
from mfrc522 import SimpleMFRC522
reader = SimpleMFRC522()
print("Halte eine RFID-Karte ans Lesegerät ...")
uid, text = reader.read()
print(f"UID gelesen: {uid}")
EOF
```

Wird eine UID ausgegeben, ist die Verdrahtung korrekt.

---

## 8. Dauerhaft als Dienst einrichten (systemd)

Damit die Anwendung automatisch beim Start des Raspberry Pi hochfährt und bei einem Absturz neu startet, richtest du einen systemd-Dienst ein.

### 8.1 Dienst-Datei erstellen

```bash
sudo nano /etc/systemd/system/getraenke.service
```

Inhalt (Pfade ggf. anpassen):

```ini
[Unit]
Description=FSGetraenkeSystem – Digitale Getränkestrichliste
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/FSGetraenkeSystem
EnvironmentFile=/home/pi/FSGetraenkeSystem/.env
ExecStart=/home/pi/FSGetraenkeSystem/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 8.2 Dienst aktivieren und starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable getraenke
sudo systemctl start getraenke
```

### 8.3 Status prüfen

```bash
sudo systemctl status getraenke
# oder Live-Log verfolgen:
sudo journalctl -u getraenke -f
```

---

## 9. Autostart des Browsers im Kiosk-Modus

Optional: Startet den Browser automatisch im Vollbild auf dem angeschlossenen Touchscreen/Monitor.

### 9.1 Chromium im Kiosk-Modus autostart

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/kiosk.desktop
```

Inhalt:

```ini
[Desktop Entry]
Type=Application
Name=Getraenke Kiosk
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:5000/
X-GNOME-Autostart-enabled=true
```

> **Hinweis:** Benötigt Raspberry Pi OS Desktop (nicht Lite) und einen angeschlossenen Bildschirm.

### 9.2 Bildschirmschoner deaktivieren

```bash
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Folgende Zeilen hinzufügen:

```
@xset s off
@xset -dpms
@xset s noblank
```

---

## 10. Fehlerbehebung

### SPI-Geräte werden nicht gefunden (`/dev/spidev*` fehlt)

```bash
# SPI erneut aktivieren
sudo raspi-config nonint do_spi 0
sudo reboot
```

### `mfrc522` lässt sich nicht importieren

```bash
source venv/bin/activate
pip install mfrc522
# Falls Fehler mit spidev:
pip install spidev
```

### RFID-Karte wird nicht erkannt

1. Verdrahtung anhand der Tabelle in [Abschnitt 4](#4-rc522-rfid-modul-anschließen--verdrahtungsplan) überprüfen.
2. Sicherstellen, dass **3,3 V** verwendet wird (nicht 5 V!).
3. SPI-Modul laden: `lsmod | grep spi_bcm2835`
4. Tipp: Kabel einzeln durchmessen, besonders SDA (CS) und RST.

### `Permission denied` beim Zugriff auf SPI

```bash
sudo usermod -a -G spi pi
# Danach neu einloggen
```

### Port 5000 ist bereits belegt

```bash
# Prozess auf Port 5000 anzeigen
sudo lsof -i :5000
# .env anpassen oder anderen Port in run.py konfigurieren
```

### Dienst startet nicht (systemd)

```bash
sudo journalctl -u getraenke -n 50 --no-pager
```

Häufige Ursachen: falscher Pfad in `WorkingDirectory` oder `ExecStart`, fehlende `.env`-Datei.

---

*Letzte Aktualisierung: März 2026*
