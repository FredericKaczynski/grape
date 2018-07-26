# Grape

## Architecture

Each folder of this repository contains a component of the project:

* `master_setup` contains the necessary `.sh` scripts to create a working Master RPi.
* `graped` contains the source code of the Python daemon that will run on the Master RPi.
* `grapecli` contains the source code of the small Python utility that can query the Python daemon on the Master RPi for informations about the state of the cluster.
* `slave_i2c_daemon` :construction: TODO :construction:

## How to use