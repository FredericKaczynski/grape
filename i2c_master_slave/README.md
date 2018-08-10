# I2C Master Slave

This folder contains the files to enable communications between master and slaves

## How to setup

* Plug two cables between the slave RPi and the SMBus on the board (the one that is not near the printed `BRIDGE`.
  * A cable should connect the `sda` row of the SMBus (any of the 5 pins) and the BCM 18 pin of the RPi (refer to [Pinout](https://pinout.xyz/#) to find which pin it is).
  * A cable should connect the `sdl` row of the SMBus (any of the 5 pins) and the BCM 19 pin of the Rpi (again, use Pinout).
* On the slave RPi, download this repository and execute the script to install everything. You can do this by executing this on the slave (this may take some time):
  ```bash
  wget https://github.com/FredericKaczynski/grape/archive/master.zip
  unzip master.zip
  mv grape-master grape
  cd grape/i2c_master_slave
  sudo ./install_overlay.sh
  ```
* Reboot the slave RPi

If everything worked, you should be able to see the I2C device at address `0x50` by doing:

```bash
i2cdetect -y 0
```

If it works and you see a device at `0x50`, you can write any program that reads the device `/dev/i2c_slave`. On master, you can send data with the command `i2cset -y 0 0x50 0xFF` (send the byte `0xFF`).

## Known issues

* The connection is not very stable. Messages sent can be modified or simply lost.