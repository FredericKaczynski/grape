#!/usr/bin/env bash

###############
# Compiles and installes the overlay on the Slave RPi
###############

echo "Compile overlay"

dtc -@ -I dts -O dtb -o overlay/i2cslave-bcm2708.dtbo overlay/i2cslave-bcm2708.dts

echo "Move overlay to /boot/overlays"

cp /overlay/i2cslave-bcm2708.dtbo /boot/overlays/

echo "Change /boot/config.txt to add overlay"

cat << "EOF" >> /boot/config.txt

# Added by install_overlay.sh
dt-overlay=i2cslave-bcm2708
dtparam=i2c=on
dtparam=i2c0=on
EOF