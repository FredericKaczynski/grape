# Master setup

This folder contains the `.sh` that must be run on a fresh ins

## Architecture

Each script sets up the RPi for a different task:

* `general.sh` updates the software and the firmware of the RPi, to make sure it is up to date, and install additional necessary packages.
* `setup_dnsmasq.sh` installs `dnsmasq` and configures it so that the Master RPi acts a `DHCP` and `DNS` on `eth0` for the network. In this network, the Master RPi will have the static address `192.168.2.1/24` and will lease IP addresses to the Slave RPi in the range.
* `install_overlay.sh` installs the device tree overlay that will allow the RPi to use I2C to communicate with the different sensors & actuators on the PCB.

## How to use

Assuming you are connected via SSH to a RPi with a freshly installed Raspbian OS that contains a clone of the present repository, you can simply do:

```sh
cd master_setup
make
```