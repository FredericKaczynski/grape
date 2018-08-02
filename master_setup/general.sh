#!/bin/bash

###############
# Updates the raspberry and the installed packages
###############

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

apt-get upgrade
rpi-update

# Install additional packages
apt-get install -y i2c-tools
apt-get install -y python-smbus
apt-get install -y python-pip
# Packages for Paramiko
apt-get install -y libffi-dev
