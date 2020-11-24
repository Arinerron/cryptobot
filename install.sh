#!/bin/sh

error() {
    printf '\E[31m' >&2
    printf "$@" >&2
    printf '\E[0m\n' >&2
}

######
# configuration
######

DEB_PACKAGES=(python3 pip3 sqlite3)

######
# script
######

if [[ $EUID -neq 0 ]]; then
    error 'This script must be run as root'
    exit 1
fi

if [ ! -f "/usr/bin/apt-get" ]; then
    error 'This script is intended to be ran on a Debian-based system'
    exit 1

# ensure packages are installed
for package in "${DEB_PACKAGES[@]}"; do
    if ! dpkg -s "$package" >/dev/null 2>&1; then
        error 'Package "%s" is required, installing...' "$package"
    fi
done

