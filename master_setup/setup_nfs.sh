#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

mkdir /nfs
mkdir /nfs/base

apt-get install nfs-kernel-server
echo "/nfs *(rw,sync,no_subtree_check,no_root_squash)" | tee -a /etc/exports
systemctl enable rpcbind
systemctl restart rpcbind
systemctl enable nfs-kernel-server
systemctl restart nfs-kernel-server