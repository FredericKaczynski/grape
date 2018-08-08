# Master setup

This folder contains the `.sh` that must be run on a fresh ins

## Architecture

Each script sets up the RPi for a different task:

* `general.sh` updates the software and the firmware of the RPi, to make sure it is up to date, and install additional necessary packages.
* `setup_dnsmasq.sh`:
  * Installs `dnsmasq` and configures it so that the Master RPi acts a `DHCP` and `DNS` on `eth0` for the network. In this network, the Master RPi will have the static address `192.168.2.1/24` and will lease IP addresses to the Slave RPi in the range between `192.168.2.2` and `192.168.2.15`.
  * Configures `iptables` so that the Internet connection from `eth1` is shared to the network on `eth0`, allowing the slave RPi an access to the internet.
* `install_overlay.sh` installs the device tree overlay that will allow the RPi to use I2C to communicate with the different sensors & actuators on the PCB.
* `install_graped.sh` installs and configures `graped` as UNIX service, which makes it start on boot, reloadable with `systemctl reload graped`, etc...
* `setup_nfs.sh` installs and configure `nfs-kernel-server`, which allows slave RPi to netboot on the master.

## How to use

Assuming you are connected via SSH to a RPi with a freshly installed Raspbian OS, you can simply do:

```bash
wget https://github.com/FredericKaczynski/grape/archive/master.zip
unzip master.zip
mv grape-master grape
cd grape/master_setup
sudo make
```

Once finished, reboot the RPi once for all the changes to take effect.

You may also want to make `.img` file of the SD card to have a backup, or to quickly re-flash an other SD card. To do this, plug the SD card on your computer, and execute:

```bash
sudo dd if=/dev/mmcblk0 of=master-rpi.img bs=64M status=progress
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x pishrink.sh
sudo ./pishrink.sh -s master-rpi.img
zip master-rpi.img.zip master-rpi.img
``` 