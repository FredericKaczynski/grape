# Grape Dockerd

`grape_dockerd` is a Python daemon that is built on top of `graped`. It polls `graped`'s REST API to retrieve the list of connected hosts and use `docker-machine` to install Docker on the slaves RPis and make them join the swarm as worker.

## How to use

`docker_graped` is installed by the scripts in `master_setup` along with its dependencies. You can start or stop the daemon by executing:

```bash
sudo systemctl stop grape_dockerd # To stop
sudo systemctl start grape_dockerd # To start
```
**Note:** When using Raspbian, you must change the ID of the system `/etc/os-release` (`ID=raspbian` to `ID=debian`). Otherwise, `docker-machine` will complain that it doesn't know the OS of the slaves and will not install Docker on them.