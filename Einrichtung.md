# Raspberry Pi Inbetriebnahme

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
```INI
[Unit]
Description=Temp Logger Backend
After=network-online.target mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/temperatur-logger/Backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/temperatur-logger/Backend/.venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
