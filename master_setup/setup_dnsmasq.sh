#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

echo "Installing dnsmasq"
apt-get install -y dnsmasq

systemctl start network-online.target &> /dev/null

# Setup iptables rules
echo "Setting up iptables rules"
iptables -F
iptables -t nat -F
iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
iptables -A FORWARD -i eth1 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT

# Save the rules
iptables-save > /etc/iptables.ipv4.nat

# Set up a script in /etc/rc.local so that the IP rules are loaded
# at boot
cat << "EOF" > /etc/rc.local
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.

# Print the IP address
_IP=$(hostname -I) || true
if [ "$_IP" ]; then
  printf "My IP address is %s\n" "$_IP"
fi

iptables-restore < /etc/iptables.ipv4.nat

exit 0
EOF

# Enable IPv4 forwarding
# Temporary, so that we don't have to reboot
echo 1 > /proc/sys/net/ipv4/ip_forward
# Permanent solution
echo -e "\nnet.ipv4.ip_forward=1" >> /etc/sysctl.conf


# Setup eth0 to have a static address
echo "Modifying /etc/network/interfaces to assign static IP address"
cat << "EOF" >> /etc/network/interfaces

auto eth0
iface eth0 inet static
   address 192.168.2.1
   netmask 255.255.255.0
   network 192.168.2.0
   broadcast 192.168.2.255

allow-hotplug eth1
iface eth1 inet dhcp
EOF

sudo ip route del 0/0 dev eth0 &> /dev/null

echo "Editing dnsmasq configuration"
sudo systemctl stop dnsmasq
sudo rm -rf /etc/dnsmasq.d/*
cat << "EOF" > /etc/dnsmasq.d/custom-dnsmasq.conf
interface=eth0
bind-interfaces
server=8.8.8.8
domain-needed
bogus-priv
dhcp-range=192.168.2.2,192.168.2.15,12h
log-dhcp
enable-tftp
tftp-root=/tftpboot
tftp-unique-root=mac
pxe-service=0,"Raspberry Pi Boot"
EOF

ifdown eth0
ifup eth0

mkdir /tftpboot
chmod 777 /tftpboot
mkdir /tftpboot/base

systemctl start dnsmasq
