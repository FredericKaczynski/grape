# Graped

Grape**d** is the **d**aemon that runs on the Master RPi and that manages the Grape stacks. It is capable of detecting the connected Grape stacks, reading the sensors if they are available (temperature and power) and power up and down the Worker RPi through the power switches.

## Architecture

:construction: TODO :constructor:

## How to use

The daemon is normally automatically installed as a service on the Master RPi by the `.sh` scripts located in the folder `master_setup` of this repository.

To stop or restart the daemon, the `systemctl` command can be used:

```bash
# To stop graped
sudo systemctl stop graped
# To restart graped
sudo systemctl restart graped
```

Logs of the daemon can be found by using the standard unix command `journalctl`, for example:

```bash
journalctl -u graped -f
```