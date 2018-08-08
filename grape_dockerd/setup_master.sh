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

mkdir keys/

# Setup grape_dockerd as a service
GRAPE_DOCKERD_PATH="/home/pi/grape/grape_dockerd"

chmod +x ${GRAPE_DOCKERD_PATH}/grape_dockerd.py

if [ ! -f "${GRAPE_DOCKERD_PATH}/grape_dockerd.py" ]
then
    echo "File ${GRAPE_DOCKERD_PATH}/grape_dockerd.py should exists"
    echo "Are you sure you cloned at the right position ?"
    exit
fi

PATH_SERVICE="/etc/systemd/system/grape_dockerd.service"

echo "Creating ${PATH_SERVICE}"
cat << EOF > ${PATH_SERVICE}
[Unit]
Description=Grape Docker daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=${GRAPE_DOCKERD_PATH}
ExecStart=${GRAPE_DOCKERD_PATH}/grape_dockerd.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF


echo "Enabling graped"
systemctl enable grape_dockerd
systemctl start grape_dockerd