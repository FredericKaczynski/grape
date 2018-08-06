#!/usr/bin/env bash

###############
# Install graped as Unix service
###############

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

# Install Python packages for graped
pip install -r ../graped/requirements.txt


GRAPE_PATH="/home/pi/grape/graped"

chmod +x ${GRAPEPATH}/graped.py

if [ ! -f "$GRAPE_PATH/graped.py" ]
then
    echo "File $GRAPE_PATH/graped.py should exists"
    echo "Are you sure you cloned at the right position ?"
    exit
fi

PATH_SERVICE="/etc/systemd/system/graped.service"

echo "Creating ${PATH_SERVICE}"
cat << EOF > ${PATH_SERVICE}
[Unit]
Description=Grape daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=${GRAPE_PATH}
ExecStart=${GRAPE_PATH}/graped.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF


echo "Enabling graped"
systemctl start graped