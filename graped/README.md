# Graped

Grape**d** is the **d**aemon that runs on the Master RPi and that manages the Grape stacks. It is capable of detecting the connected Grape stacks, reading the sensors if they are available (temperature and power) and power up and down the Worker RPi through the power switches.

## Architecture

:construction: TODO :constructor:

## How to use

The daemon is normally automatically installed as a service on the Master RPi via the `.sh` scripts located in the folder `master_setup` of this repository.

## Netboot

Netboot can be activated by changing the config `active` to `true` in `config.toml`. When the daemon boots, it will setup the necessary folders and filesystems for the slaves RPi. Nonetheless, a working installation must be provided for the slaves RPi to boot. The following commands guides you on how to setup a fresh Raspbian system for the slaves RPi to boot:

```sh
wget https://downloads.raspberrypi.org/raspbian_lite_latest
unzip raspbian_lite_latest
# The name of the extracted file may differ, change accordingly
# `fdisk` is used to get the start sectors of the different partitions
fdisk -l 2018-06-27-raspbian-stretch-lite.img
# Mount the two partitions (`offset` must be changed depending on the output
# of `fdisk`) and extract the file of the .img file
sudo mkdir /mnt/boot /mnt/system
sudo mount -o loop,offset=$((512*8192)) 2018-06-27-raspbian-stretch-lite.img /mnt/boot
sudo cp -r /mnt/boot/. /tftpboot/base/
sudo umount /mnt/boot
sudo mount -o loop,offset=$((512*98304)) 2018-06-27-raspbian-stretch-lite.img /mnt/system
sudo cp -r /mnt/system/. /nfs/base/
sudo umount /mnt/system

# Important !
# By default, Raspbian doesn't open SSH port, unless an empty-file called ssh is created
sudo touch /nfs/base/boot/ssh

# One last thing:
# The file `/nfs/base/etc/fstab` must be edited to remove the 2 lines that contains
# `/dev/mmcblkp1` and `/dev/mmcblkp2`. At the end, only a line with `proc` should be left
sudo nano /nfs/base/etc/fstab
```