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
Dann noch die Berechtigung für home-Pfade erteilen, hier im beschriebenen Bereich zwischen den Comments folgendes eintragen:
```bash
sudo systemctl edit grafana-server
```
```INI
[Service]
ProtectHome=false
```

# Grafana-Dashboard bauen
Unter <Pi-IP>/grafana/ muss man unter Administration -> Plugins & Data -> Plugins das Plugin SQLite von frser installieren, dann ein neues Dashboard erstellen und dafür eine Datenquelle aus diesem Plugin und diesem Pfad anlegen `/home/pi/temperatur-logger_Pi/Backend/measurements.db`. 
Dann muss man noch den Visualisierungsstil festlegen:
```json
SELECT
  datetime(m.ts, 'unixepoch') AS time,
  m.temp_c AS value,
  COALESCE(d.device_id, m.device_id) AS metric
FROM measurements m
LEFT JOIN devices d ON d.device_id = m.device_id
WHERE $__timeFilter(datetime(m.ts, 'unixepoch'))
ORDER BY m.ts;
```
Das Dashboard wird dann gespeichert und wenn man das Dashboard dann auswählt sieht man in der url /grafana/d/`uid`/temp-logger/...
Diese UID trägt man dan in der App.tsx anstatt von `Replace with UID` in Zeile 148 ein.
Dann geht man nochmal in den Ordner
```bash
cd /home/pi/temperatur-logger_Pi/
```
und führt nochmal
```bash
git pull
```
aus, um die Änderungen wirksam zu machen.

# Frontend Build
