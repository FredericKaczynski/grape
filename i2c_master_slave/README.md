# I2C Master Slave

This folder contains the files to enable communications between master and slaves

## How to setup

* Plug two cables between the slave RPi and the SMBus on the board (the one that is not near the printed `BRIDGE`.
  * A cable should connect the `sda` row of the SMBus (any of the 5 pins) and the BCM 18 pin of the RPi (refer to [Pinout](https://pinout.xyz/#) to find which pin it is).
  * A cable should connect the `sdl` row of the SMBus (any of the 5 pins) and the BCM 19 pin of the Rpi (again, use Pinout).
* On the slave RPi, download this repository and execute the script to install everything. You can do this by executing this on the slave:
  ```bash
  wget https://github.com/FredericKaczynski/grape/archive/master.zip
  unzip master.zip
  mv grape-master grape
  cd grape/i2c_master_slave
  ./install_overlay.sh
  ```

## Known issues

* The connection is not very stable. Messages sent can be modified or simply lost.
* Only 2 bytes can be read at a time