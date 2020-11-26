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

######
# script
######

if [ "x$EUID" != "x0" ]; then
    error 'This script must be run as root'
    exit 1
fi

if [ ! -f "/usr/bin/apt-get" ]; then
    error 'This script is intended to be ran on a Debian-based system'
    exit 1
fi

set -e

# ensure packages are installed
for package in ${DEB_PACKAGES[@]}; do
    if ! dpkg -s "$package" >/dev/null 2>&1; then
        error 'Package "%s" is required, installing...' "$package"
        apt-get install "$package"
    fi
done

./setup.py install

mkdir -p /usr/share/cryptobot
cp -n config.yml.example /usr/share/cryptobot/config.yml
cp -u cryptobot.service cryptobot.timer /usr/lib/systemd/system/
cp -u cryptobot-check-price.service cryptobot-check-price.timer /usr/lib/systemd/system/

/usr/local/bin/cryptobot status

systemctl daemon-reload
systemctl enable cryptobot.timer
systemctl start cryptobot.timer
systemctl enable cryptobot-check-price.timer
systemctl start cryptobot-check-price.timer
