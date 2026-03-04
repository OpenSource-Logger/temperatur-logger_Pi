# Raspberry Pi Inbetriebnahme
## Betriebssystem: RaspberryPi OS Lite 64bit -> Debian Trixie 13.3

## Basis
```bash
sudo apt update
```
```bash
sudo apt upgrade -y
```
```bash
sudo apt install -y git curl nginx mosquitto mosquitto-clients python3 python3-venv python3-pip
```
```bash
sudo hostnamectl set-hostname temp-logger
```
```bash
sudo reboot
```

# SSH-Key erstellen
```bash
ssh-keygen -t ed25519 -C "<github-email>"
```
Bei Filepath und Passphrase einfach Enter drücken um es am Default-Speicherplatz (~/.ssh) ohne Passwort zu speichern. Dann den public-Key anzeigen lassen und bei Github einfügen.
```bash
cat ~/.ssh/id_ed25519.pub
```

# Git-Repo klonen
```bash
cd ~
```
```bash
git clone git@github.com:OpenSource-Logger/temperatur-logger_Pi.git
```
```bash
cd temperatur-logger_Pi
```

# Python Backend Setup
```bash
cd Backend
```
```bash
python3 -m venv .venv
```
```bash
pip install -U pip
```
```bash
pip install -r requirements.txt
```
Testen und danach mit Strg+C wieder beenden:
```bash
python main.py
```

# Backend als systemd-Service
```bash
sudo nano /etc/systemd/system/temp-logger-backend.service
```
Diesen Inhalt einfügen:
```INI
[Unit]
Description=Temp Logger Backend
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/temperatur-logger_Pi/Backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/temperatur-logger_Pi/Backend/.venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

# Grafana installieren
```bash
sudo mkdir -p /etc/apt/keyrings
```
```bash
curl -fsSL https://packages.grafana.com/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
```
```bash
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
 ```
```bash
sudo apt update
```
```bash
sudo apt install -y grafana
```

# Grafana für Reverse-Proxy über Nginx vorbereiten
```bash
sudo nano /etc/grafana/grafana/grafana.ini
```
Hier folgende Zeilen ändern:
```INI
[server]
protocol = http
http_port = 3000
domain = localhost
root_url = %(protocol)s://%(domain)s/grafana/
serve_from_sub_path = true
[security]
allow_embedding = true
cookie_samesite = none
[auth.anonymous]
enabled = true
org_role = Admin
[plugins]
allow_loading_unsigned_plugins = frser-sqlite-datasource
```
Und ganz unten noch folgenden Block einfügen:
```INI
[plugin.frser-sqlite-datasource]
allowed_paths = /home/pi/temperatur-logger_Pi/Backend/
```
Dann noch die Berechtigung für home-Pfade erteilen:
```bash
sudo systemctl edit grafana-server
```
Hier im beschriebenen Bereich zwischen den Comments folgendes eintragen:
```INI
[Service]
ProtectHome=false
```
