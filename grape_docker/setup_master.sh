#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

apt install sshpass

pip install -r requirements.txt

# Install docker
curl -sSL https://get.docker.com | sh

# Install docker-machine
curl -L https://github.com/docker/machine/releases/download/v0.14.0/docker-machine-Linux-armhf >/tmp/docker-machine
sudo install /tmp/docker-machine /usr/local/bin/docker-machine

# Add user pi as being able to use docker
sudo gpasswd -a pi docker

# Generating a key that will be used for all transactions
mkdir keys/
ssh-keygen -f keys/id_rsa -N ""