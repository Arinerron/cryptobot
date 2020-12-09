#!/bin/bash

error() {
    printf '[-] ' >&2
    printf "$@" >&2
    printf '\n' >&2
}

######
# configuration
######

export DEB_PACKAGES="python3 python3-pip sqlite3"

export BIN_PATH="/usr/local/bin/cryptobot"
export SHARE_PATH="/usr/share/cryptobot"
export LOG_FILE_PATH="/var/log/cryptobot.log"
export SYSTEMD_PATH="/usr/lib/systemd/system"

######
# script
######

if [ "x$EUID" != "x0" ]; then
    error 'This script must be run as root'
    exit 2
fi

if [ ! -f "/usr/bin/apt-get" ]; then
    error 'This script is intended to be ran on a Debian-based system'
    exit 2
fi

cd "$(dirname "$0")"
set -e

# ensure packages are installed
for package in ${DEB_PACKAGES[@]}; do
    if ! dpkg -s "$package" >/dev/null 2>&1; then
        error 'Package "%s" is required, installing...' "$package"
        apt-get install "$package"
    fi
done

pip3 install --upgrade -r requirements.txt
./setup.py install

mkdir -p "$SHARE_PATH"
cp -n config.yml.example "${SHARE_PATH}/config.yml"

useradd cryptobot || true
chown -R cryptobot:cryptobot "$SHARE_PATH" "$LOG_FILE_PATH"
chmod -R 600 "$SHARE_PATH" "$LOG_FILE_PATH"
chmod 755 "$SHARE_PATH"
chown root:cryptobot "$BIN_PATH"
chmod 750 "$BIN_PATH"

cp -u cryptobot.service cryptobot.timer "$SYSTEMD_PATH"
cp -u cryptobot-check-price.service cryptobot-check-price.timer "$SYSTEMD_PATH"

"$BIN_PATH" status

systemctl daemon-reload
systemctl enable cryptobot.timer
systemctl start cryptobot.timer
systemctl enable cryptobot-check-price.timer
systemctl start cryptobot-check-price.timer
