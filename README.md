# Grape

## Architecture

Each folder of this repository contains a component of the project:

* `master_setup` contains the necessary `.sh` scripts to create a working Master RPi from a fresh Raspbian installation.
* `graped` contains the source code of the Python daemon that runs on the Master RPi.
* `grapecli` contains the source code of the small Python utility that can query the Python daemon on the Master RPi for informations about the state of the cluster.
* `i2c_master_slave` contains the files to setup a I2C communication channel between the Master RPi and the Slaves RPi. It is not used in the final solution as it was too unstable. Nonetheless, the work accomplished, the scripts used and the difficulties encountered have been documented here.