#!/bin/bash

error() {
    printf '[-] ' >&2
    printf "$@" >&2
    printf '\n' >&2
}

######
# configuration
######

export CONFIG_PATH="/usr/share/cryptobot/config.yml"

######
# script
######

if [ "x$EUID" != "x0" ]; then
    error 'This script must be run as root'
    exit 2
fi

if [ ! -f "$CONFIG_PATH" ]; then
    error 'Missing config file'
    exit 2
fi

cd "$(dirname "$0")"
set -e

for file in $(find tests -executable -type f); do
    printf "\n---------- %s\n\n" "$file"
    PYTHONPATH="." "$file"
done
