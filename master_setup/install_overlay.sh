#!/bin/bash

###############
# Compiles and installes the overlay on the RPi master
###############

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

echo "Compile overlay"

dtc -@ -O dtb -o overlay/grape.dtbo overlay/grape.dts

echo "Install overlay to /boot/overlays/grape.dtbo"

cp overlay/grape.dtbo /boot/overlays/

echo "Change /boot/config.txt to add overlay"

cat << "EOF" >> /boot/config.txt

# Added by install_overlay.sh
dtoverlay=grape
dtparam=i2c=on
dtparam=i2c0=on
dtparam=i2c_arm=on
dt-overlay=i2c0-bcm2708
enable_uart=1
EOF
