#!/usr/bin/env bash

if [ -z $1 ]; then
	ADDRESS=$1
else
	ADDRESS=80 # 0x50
fi

apt-get install -y git sysstat libncurses5-dev bc build-essential

git clone --depth=1 https://github.com/raspberrypi/linux
cd linux

KERNEL=kernel
make bcm2709_defconfig

make -j4 zImage modules dtbs
make modules_install

cp arch/arm/boot/dts/*.dtb /boot/
cp arch/arm/boot/dts/overlays/*.dtb* /boot/overlays/
cp arch/arm/boot/dts/overlays/README /boot/overlays/
scripts/mkknlimg arch/arm/boot/zImage /boot/$KERNEL.img
cd ../

git clone https://github.com/marilafo/raspberry_slave_i2c.git

cd raspberry_slave_i2c
dtc -@ -I dts -O dtb i2cslave-bcm2708-overlay.dts -o i2cslave-bcm2708.dtbo
cp i2cslave-bcm2708.dtbo /boot/overlays/

make CFLAGS=-DSLV_ADDRESS=$ADDRESS all
sudo cp bcm2835_slave_mod.ko /lib/modules/$(uname -r)/kernel/drivers/
sudo depmod -a
cd ../

echo "bcm2835_slave_mod slave_add=$ADDRESS" >> /etc/modprobe.d/i2c.conf
echo "dtoverlay=i2cslave-bcm2708" >> /boot/config.txt