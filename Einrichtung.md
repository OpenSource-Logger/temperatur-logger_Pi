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
. .venv/bin/activate
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
sudo nano /etc/grafana/grafana.ini
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
```bash
sudo chmod 755 /home/pi
```
```bash
sudo chmod 755 /home/pi/temperatur-logger_Pi
```
```bash
sudo chmod 755 /home/pi/temperatur-logger_Pi/Backend
```
```bash
sudo chmod 644 /home/pi/temperatur-logger_Pi/Backend/measurements.db
```

# Frontend Build
Node installieren:
```bash
sudo apt install -y nodejs npm
```
```bash
cd
```
```bash
cd temperatur-logger_Pi/react/frontend
```
```bash
npm install
```
```bash
npm run build
```
```bash
sudo mkdir -p /var/www/temp-logger
```
```bash
sudo rsync -a --delete dist/ /var/www/temp-logger/
```

# Nginx konfigurieren
```bash
sudo nano /etc/nginx/sites-available/temp-logger
```
```Nginx
server {
    listen 80;
    server_name _;

    root /var/www/temp-logger;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location = /grafana {
        return 301 /grafana/;
    }

    location /grafana/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /grafana;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/temp-logger /etc/nginx/sites-enabled/
```
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```
Die Konfiguration auf Syntax überprüfen:
```bash
sudo nginx -t
```

# Mosquitto konfigurieren
```bash
sudo nano /etc/mosquitto/conf.d/temp-logger.conf
```
```INI
listener 1883
allow_anonymous true
```

# Alles aktivieren:
```bash
sudo systemctl daemon-reload
```
```bash
sudo systemctl enable temp-logger-backend
```
```bash
sudo systemctl start temp-logger-backend
```
```bash
sudo systemctl enable mosquitto
```
```bash
sudo systemctl start mosquitto
```
```bash
sudo systemctl enable grafana-server
```
```bash
sudo systemctl start grafana-server
```
```bash
sudo systemctl restart nginx
```

# Überprüfen
```bash
systemctl status mosquitto
```
```bash
systemctl status temp-logger-backend
```
```bash
systemctl status grafana-server
```
```bash
systemctl status nginx
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

# Optional:
IP vom Ethernet-Port festlegen, damit man auch ohne DHCP-Server direkt von seinem PC per SSH auf den Pi zugreifen kann:
```bash
nmcli connection show
```
Hier jetzt den Namen der Ethernet-Schnittstelle merken, meistens "netplan-eth0"
```bash
sudo nmcli connection modify "netplan-eth0" \
ipv4.method manual \
ipv4.address <IP>/<CIDR> \
ipv4.gateway "" \
ipv4.dns "" \
ipv6.method ignore
```
CIDR bezieht sich auf die Subnetzmaske und bezieht sich auf die Anzahl der freien Adressen. Bei 192.168.0.15 wäre die Subnetzmaske 255.255.255.0 und die CIDR damit 24. Bei 255.255.0.0 wäre die CIDR 16. Ein Gateway und einen DNS-Server braucht man hier nicht, man ist ja direkt mit dem PC verbunden. 
Danach die Schnittstelle noch einmal neu starten:
```bash
sudo nmcli connection down "netplan-eth0"
```
```bash
sudo nmcli connection up "netplan-eth0"
```
Falls nichts an Ethernet angeschlossen war bekommt man bei "down" einen Fehler, dann muss nicht neugestartet werden.

# Logs ausgeben lassen
z.B. für grafana:
```bash
journalctl -u grafana-server --no-pager
```
