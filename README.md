# Grape

## Architecture

Each folder of this repository contains a component of the project:

* `master_setup` contains the necessary `.sh` scripts to create a working Master RPi from a fresh Raspbian installation.
* `graped` contains the source code of the Python daemon that runs on the Master RPi.
* `grapecli` contains the source code of the small Python utility that can query the Python daemon on the Master RPi for informations about the state of the cluster.
* `grape_docker` contains the source code of an other daemon that runs on the Master RPi and that takes care of installing docker on slaves RPi and making them join a docker swarm manager by the masterpylo. This daemon relies on `graped`

The following component is not used in the final project, and is there to present the work that has been done to make it work

* `i2c_master_slave` contains the files to setup a I2C communication channel between the Master RPi and the Slaves RPi. It is not used in the final solution as it was too unstable.

## How to setup a working cluster

This guide assumes that you have a powered Cluster of Grape Stacks and that you know how to SSH to a remote RPi through an Ethernet cable.

### Put the shunters on the stacks

There are 3 groups of shunt that must be placed on each stack:

* On the back of the board (that is, the side with the slaves RPi micro USB connectors), you have 2 shunters to place: `SDA` and `SDL`. They determine which of the 2 I2C Bus the stack will use (either 0 or 1). In practice, this doesn't have any impact on `graped`, so you can choose any of the 2 buses. The 2 shunters must be connected with the same bus.
* On the front of the board (that is, the side with the master RPi), you have 2 groups of shunters:
  * 3 shunters `A0`, `A1` and `A2` must be placed to form the address of the stack. Each stack of the cluster must have a different address. Additionaly, if the Power Meter is activated (via the shunters explained below) `A1` **must** be set to 0.
  * 2 shunters `PWR METER` must be placed to enable or disable the Power Meter. The 2 shunters should be placed in the same way.

### Setup a master RPi

The SD card on the master must be flashed with a special system image ([master-rpi.img.zip](http://google.com)) with the necessary packages installed and configured. To do so, you can do:

Once done, you can unmount the SD card and plug it to the master RPi of your Grape cluster.

**Note:** If the link above is down, or if you want to build an `.img` of the master RPi yourself, the instructions to do so are available in `master_setup`.

### Configure the master RPi

Some configuration must be done on the master RPi (mainly specifying the MAC address of the slave RPi).

SSH to the master RPi, and modify the file `/home/pi/grape/graped/config.toml` (using for example `nano /home/pi/grape/graped/config.toml`).
The part that must be changed is the structure of the cluster. By default, it is:

```toml
[cluster.stacks.0]
    [cluster.stacks.0.devices.0]
        mac = "B8:27:EB:2C:C0:04"
    [cluster.stacks.0.devices.1]
        mac = "B8:27:EB:EF:37:6E"
    [cluster.stacks.0.devices.5]
        mac = "B8:27:EB:07:8A:E7"
[cluster.stacks.1]
    [cluster.stacks.1.devices]
```

This configuration describes a cluster that is composed of 2 stacks:

* One stack configured with the address `0` (`000` in binary, as defined with the shunters `A0`, `A1`, `A2`), with 6 devices:
  * A Pi device on slot `0` with the MAC address `B8:27:EB:2C:C0:04`
  * A Pi device on slot `1` with the MAC address `B8:27:EB:EF:37:6E`
  * A Pi device on slot `5` with the MAC address `B8:27:EB:07:8A:E7`
* One stack configured with the address `1` (`001`), with no Pi devices.

The default value for the rest of the configuration file should suffice for a first start with the Grape cluster (by default, netbooting is disabled). Documentation on the other configuration values is available in `graped/README.md`.

### Configure the slaves RPi

Depending on whether you enabled netbooting, setting up the slaves RPi will be different:

#### Without netbooting

Each slaves will require an SD card with a working operating system. Any system can be used and no `graped`-specific modifications must be made on the slaves RPi, although some modifications might have to be made depending on the distribution.

A image with a working Raspbian Stretch is available here: [slave-rpi.img.zip](http://google.com). Download this image, unzip it and flash the SD cards using a program like [Etcher](https://etcher.io/) or the unix command `dd`.

**Note** If the link above is down or if you want to recreate the `.img` file, here are the instructions:  
The following commands will download a Raspbian Stretch installation and build `slave-rpi.img`:

```bash
wget https://downloads.raspberrypi.org/raspbian_lite_latest
unzip raspbian_lite_latest
# The name of the file extracted may change (specially the date)
# Depending on your SD card reader, you may need to change `/dev/mmcblk0` to the correct location
sudo dd if=2018-06-27-raspbian-stretch-lite.img of=/dev/mmcblk0 bs=16M status=progress

# Mount the SD card
sudo mkdir /mnt /mnt/boot /mnt/rootfs
sudo mount /dev/mmcblk0p1 /mnt/boot
sudo mount /dev/mmcblk0p2 /mnt/rootfs

# Create the empty ssh file to tell Raspbian to open port 22 of the RPi.
sudo touch /mnt/boot/ssh
# Change the described OS to not confuse docker-machine
sudo sed -i 's|ID=raspbian|ID=debian|' /mnt/rootfs/etc/os-release
sudo umount /mnt/boot
sudo umount /mnt/rootfs

# Copy the content of the SD card, will create a file of the size of the SD card
sudo dd if=/dev/mmcblk0 of=slave-rpi.img bs=16M status=progress
# Shrink the file to the minimum
wget https://raw.githubusercontent.com/Drewsif/PiShrink/master/pishrink.sh
chmod +x ./pishrink.sh
sudo ./pishrink.sh slave-rpi.img
zip slave-rpi.img.zip slave-rpi.img

```

#### With netbooting

Netbooting is only usable when using RPi 3 B or above.

You can remove the SD cards off the slaves RPi, since they will boot on a filesystem situated on the master.

Two things must be done in order to use netbooting:

##### One Time Programmable bit

If you're using a RPi 3B, you must activate an One Time Programmable (OTP) bit (With RPi 3B+, it is not necessary) to make the RPi try to netboot if an SD card is not plugged.

To activate this bit, the RPi has to boot once with a SD card containing a Raspbian system with the line `program_usb_boot_mode=1` in `/boot/config.txt`. Once a RPi has its OTP set, you can remove the line added before (You can mark the RPi with a colored spot to distinguish them)

To check if an RPi has its OTP set, you can use the following command:
```bash
$ vcgencmd otp_dump | grep 17:
17:3020000a
```

If the RPi has not its OTP set, the output should be different: `17:1020000a`.

##### Netbootable system on the master

You must prepare a single working filesystem for the slaves RPi to boot on the master. The following commands, which must be executed on the master, describe how to setup a fresh Raspbian Stretch system:

```bash
wget https://downloads.raspberrypi.org/raspbian_lite_latest
unzip raspbian_lite_latest
# The name of the extracted file may differ, change accordingly
# `fdisk` is used to get the start sector of the different partitions
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
# By default, Raspbian doesn't open SSH port, unless an empty-file
# called ssh is created
sudo touch /nfs/base/boot/ssh

# To use docker-machine, the OS described on `/etc/os-release` must be
# changed otherwise, docker-machine will say that it doesn't support "raspbian".
sudo sed -i 's|ID=raspbian|ID=debian|' /nfs/base/etc/os-release

# One last thing:
# The file `/nfs/base/etc/fstab` must be edited to remove the
# 2 lines that contains `/dev/mmcblkp1` and `/dev/mmcblkp2`.
# At the end, only a line with `proc` should be left
sed -i.old -n -e "/proc/{p;}" fstab
```

**Note** `graped` will copy this base filesystem for each slaves RPi. Depending on the available space on the SD card you used and the size of the system you want to use, it may simply run out of available space.
If it happens, either give the master RPi a bigger SD card, or use a smaller system for the slaves RPi (such as [DietPi](https://dietpi.com/)).

## Possible issues

Some networks (such as `eduroam`) filters NTP packet, preventing the RPi from synchronizing their internal clock. This can provoke many errors such as SSL certificate validation error due to expired or not-valid-yet certificates (happens frequently when using Docker Swarm).
The solution is to switch to a network that doesn't filter these kind of packets.

## Possible improvements

Multiple improvements could be done:

* At the moment, if you want to allow slaves RPi to neeboot on the master RPi, a unique entire system must be available for each slaves RPi (resulting in a lot of duplicated files and wasted space). An idea to solve this would be to:
  * Keep a single entire system in the folder `/nfs/base/`.
  * Create an `overlay` filesystem for each slaves RPi, allowing each slave RPi to access the folder `/nfs/base` through `/nfs/worker-0-1/overlay` but storing any modifications in a separate folder (for example `/nfs/worker-0-1/upper`) to make sure that the slaves RPi don't interfer with each other's filesystem. This can be done with:
    ```bash
    sudo mount -t overlay -o lowerdir=/nfs/base,upperdir=/nfs/worker-0-1/upper/,workdir=/nfs/worker-0-1/work/ /nfs/worker-0-1/overlay/
    ```
  * `graped` should mount the necessary filesystems at boot for the slaves RPi.
  * **Problem** NFS doesn't support exporting `overlay` filesystem. Something like `aufs` should be used, but Raspbian doesn't support this filesystem.
* The documentation describes the step to setup the slaves with Raspbian Stretch Lite, but it is a quite heavy distribution (~1.9G unzipped). Using something like [DietPi](https://dietpi.com/) or [Hypriot](https://blog.hypriot.com/downloads/) (both below 500 MB unzipped) could make the different processes faster (flashing, copying, ..) and the slaves RPi lighter.
* To make the cluster more self-contained, we could remove all the processes that require an Internet connection. For exampl:
  * When deploying a Stack on the Docker Swarm with `grape_dockerd`, the nodes will download the images from the official Docker repository.
    `grape_dockerd` could install and setup a private Docker registry so that the nodes can still fetch images without any Internet connection;
  * When `grape_dockerd` uses `docker-machine` to install `docker` to a new node, the node will need an Internet connection to fetch the files. `docker-machine` seems to support installing `docker` from a local source rather the official remote repository.