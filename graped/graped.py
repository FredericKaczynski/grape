#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import logging
import os
import subprocess
from datetime import datetime
from time import sleep
from colorama import Fore, Style
from threading import Thread
import toml
import socket
import grapelib
import sys
import rest_server
from utils.ColorFormatter import ColoredFormatter

IP_LEASED_FILE = "/var/lib/misc/dnsmasq.leases"
CONFIG = None

log_setup = logging.getLogger("setup")
log_scan_ip = logging.getLogger("scan")
log_read_meters = logging.getLogger("meters")
log_execute_ssh = logging.getLogger("exec_ssh")
log_shell = logging.getLogger("log_shell")


def get_leased_ip_for_mac(mac_address):
    try:
        with open(IP_LEASED_FILE, "r") as ip_leased_file:
            ip_by_mac = {}
            for line in ip_leased_file:
                # Lines are in the form:
                # expiration_date mac_address ip_address hostname client_id
                data = line.split(' ')
                ip_address = data[2]
                line_mac_address = data[1].upper()
                ip_by_mac[line_mac_address] = ip_address

            if mac_address in ip_by_mac:
                return ip_by_mac[mac_address]
            else:
                return None
    except Exception as error:
        log_scan_ip.warning("Couldn't read %s%s%s to find leased_ip" % (Fore.YELLOW, IP_LEASED_FILE, Style.RESET_ALL))
    return None


# Execute a shell command locally
def execute_command(command):
    log_shell.debug("Executing %s\"%s\"%s:" % (Fore.YELLOW, ' '.join(command), Style.RESET_ALL))
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stderr = []
    for line in p.stderr:
        line = line.rstrip()
        log_shell.debug("  %s" % line)
        stderr.append(line)

    stdout = []
    for line in p.stdout:
        line = line.rstrip()
        log_shell.debug("  %s" % line)
        stdout.append(line)

    return_code = p.wait()

    log_shell.debug("Return code: %s%d%s" % (Fore.GREEN if return_code == 0 else Fore.RED, return_code, Style.RESET_ALL))

    return return_code, stdout, stderr


# Convert a mac address of the form "B8:27:EB:2C:C0:04" to "b8-27-eb-2c-c0-04"
def to_dashed_mac_address(mac):
    return mac.replace(":", "-").lower()


class Grape(object):
    def __init__(self, config, grapelib_stacks, grapelib_display):
        self.config = config
        self.grapelib_stacks = grapelib_stacks
        self.display_available = grapelib_display is not None
        self.grapelib_display = grapelib_display
        self.stacks = {}

        self.scan_thread = None

    def start(self):
        # Launch scan thread
        self.scan_thread = Thread(target=self.scan_thread_function)
        # Running in daemon makes the thread stops when SINGINT is sent
        self.scan_thread.daemon = True
        self.scan_thread.start()

        for stack_add, stack in self.stacks.items():
            stack.start()

    def scan_thread_function(self):
        while True:
            self.scan()
            sleep(5)

    def scan(self):
        for stack_add, stack in self.stacks.items():
            stack.scan()


class Stack(object):
    MAX_PI_DEVICES_PER_STACK = 6

    def __init__(self, address, grapelib_stack):
        self.address = address
        self.grapelib_stack = grapelib_stack
        self.pi_devices = [None] * self.MAX_PI_DEVICES_PER_STACK

        self.time_last_reading = 0
        self.temperature_available = grapelib.Temperature in self.grapelib_stack.devices
        self.temperature = 0 # In °C
        self.power_available = grapelib.PowerMeter in self.grapelib_stack.devices
        self.current = 0 # In mA
        self.voltage = 0 # In V
        self.power = 0 # In mW

        self.read_meters_thread = None

    def start(self):
        self.read_meters_thread = Thread(target=self.read_meters_thread_function)
        # Running in daemon makes the thread stops when SINGINT is sent
        self.read_meters_thread.daemon = True
        self.read_meters_thread.start()

        # Power on all the switches
        self.grapelib_stack[grapelib.PowerSwitch].start_all()

    def read_meters_thread_function(self):
        while True:
            self.read_meters()
            sleep(1)

    def read_meters(self):
        log_read_meters.info("Reading meters on Stack %s#%d%s" % (Fore.WHITE, self.address, Style.RESET_ALL))

        try:
            new_temperature = self.temperature
            if self.temperature_available:
                new_temperature = self.grapelib_stack[grapelib.Temperature].get()

            new_power = self.power
            new_current = self.current
            new_voltage = self.voltage
            if self.power_available:
                power_meter = self.grapelib_stack[grapelib.PowerMeter]
                new_power = power_meter.power()
                new_current = power_meter.current()
                new_voltage = power_meter.voltage()
            
            self.time_last_reading = datetime.now()

            self.temperature = new_temperature
            self.power = new_power
            self.current = new_current
            self.voltage = new_voltage
        except IOError as e:
            log_read_meters.warning("Error while reading meters")

    def scan(self):
        for i, pi_device in enumerate(self.pi_devices):
            if pi_device is not None:
                # Check if an Ip address has been leased to the MAC address of this device
                # The next block of code will take care of checking if it is possible to connect to the device
                ip_address = get_leased_ip_for_mac(pi_device.mac)
                if ip_address is not None:
                    log_scan_ip.info("Found IP address %s%s%s for %s%s%s" % (
                        Fore.WHITE, ip_address, Style.RESET_ALL, Fore.WHITE, pi_device.mac, Style.RESET_ALL
                    ))

                    if pi_device.ip is None:
                        log_scan_ip.info("IP address assigned")
                        pi_device.ip = ip_address
                    else:
                        if pi_device.ip == ip_address:
                            log_scan_ip.info("IP address already assigned")
                        else:
                            log_scan_ip.info("IP address differed from old one")
                            log_scan_ip.info("Reassigning new IP")
                            pi_device.ip = ip_address
                else:
                    log_scan_ip.info("Couldn't find Ip address leased to %s%s%s" % (
                        Fore.WHITE, pi_device.mac, Style.RESET_ALL
                    ))

                # Check if the port 22 of the Pi device is reachable
                if pi_device.ip is not None:
                    log_scan_ip.info("Attempting to connect to %s%d-%d%s (%s%s%s)" % (
                        Fore.WHITE, self.address, i, Style.RESET_ALL, Fore.WHITE, pi_device.ip, Style.RESET_ALL
                    ))

                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    res = s.connect_ex((pi_device.ip, 22))

                    if res == 0:
                        log_scan_ip.info("%sConnection successful !%s" % (Fore.GREEN, Style.RESET_ALL))
                        pi_device.connected = True
                    else:
                        log_scan_ip.info("%sConnection failed%s" % (Fore.YELLOW, Style.RESET_ALL))
                        pi_device.connected = False
                else:
                    log_scan_ip.info("Pi device %s%d-%d%s has no attributed Ip address" % (
                        Fore.WHITE, self.address, i, Style.RESET_ALL
                    ))


class PiDevice(object):
    def __init__(self, mac):
        pass
        self.connected = False
        self.mac = mac
        self.ip = None

    def execute_ssh(self, command, timeout=None):
        if not self.connected:
            return None, None, None

        log_execute_ssh.info("Executing %s\"%s\"%s" % (Fore.YELLOW, command, Style.RESET_ALL))

        r, stdout, stderr = execute_command([
            "sshpass",
            "-p", config["cluster"]["ssh_password"],
            "ssh",
            # The following options are not ideal, but make sure that ssh doesn't prompt anything
            "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
            "-o", "LogLevel=QUIET",
            "%s@%s" % (config["cluster"]["ssh_username"], self.ip),
            command
        ])

        return r, stdout, stderr


def parse_ip(str_ip):
    parts = str_ip.split('.')
    if len(parts) != 4:
        log_scan_ip.error("IP in config should in the form X.X.X.X, but was %s" % str_ip)
        raise Exception()

    return [int(part) for part in parts]


def to_ip(parts):
    return '.'.join([str(part) for part in parts])


if __name__ == "__main__":
    # Setting up the log format
    FORMAT = "[%(levelname)s][%(name)s] %(message)s"
    DATE_FORMAT = "%m/%d %H:%M:%S"
    logging.basicConfig(
        level=logging.DEBUG,
        datefmt=DATE_FORMAT,
        format=FORMAT
    )
    logging.root.handlers[0].setFormatter(ColoredFormatter(FORMAT, DATE_FORMAT))

    # Loading the configuration file
    log_setup.info("Loading %sconfig.toml%s" % (Fore.YELLOW, Style.RESET_ALL))
    config = toml.load("config.toml")
    CONFIG = config

    total_stacks_in_conf = len(config["cluster"]["stacks"])
    total_devices_in_conf = sum([len(stack["devices"]) for add, stack in config["cluster"]["stacks"].items()])

    log_setup.info("Configuration contains %s%d%s stack(s), for a total of %s%d%s device(s)" % (
        Fore.YELLOW, total_stacks_in_conf, Style.RESET_ALL, Fore.YELLOW, total_devices_in_conf, Style.RESET_ALL
    ))

    # Scanning the I2C buses to see which stacks are connected
    log_setup.info("Scanning the I2C buses")
    buses, grapelib_stacks, grapelib_display = grapelib.get_stacks()

    cluster_config = config["cluster"]

    GRAPE = Grape(config, grapelib_stacks, grapelib_display)

    for stack_add, stack_config in cluster_config["stacks"].items():
        stack_add = int(stack_add)
        if stack_add not in grapelib_stacks:
            log_setup.error("Configuration set for a stack at %s%d%s but no such stack found on the bus" % (
                Fore.YELLOW, stack_add, Style.RESET_ALL
            ))
            if grapelib_display is not None:
                grapelib_display.clear_screen()
                grapelib_display.print_str("Bad configuration")
            sys.exit(1)

        stack = Stack(stack_add, grapelib_stacks[stack_add])
        GRAPE.stacks[stack_add] = stack

        for pidevice_add, pidevice_config in stack_config["devices"].items():
            pidevice_add = int(pidevice_add)

            stack.pi_devices[pidevice_add] = PiDevice(pidevice_config["mac"])

    # Simple check to see if there were additional stacks found on the bus that weren't specified in
    # the config file
    for stack_add, bus_stack in grapelib_stacks.items():
        if str(stack_add) not in cluster_config["stacks"]:
            log_setup.warning("Stack %s%d%s found on the bus, but not specified in the config file" % (
                Fore.YELLOW, stack_add, Style.RESET_ALL
            ))
            log_setup.warning("Stack will be ignored")

    log_setup.info("I2C Bus contains %s%d%s stack(s)" % (Fore.YELLOW, len(grapelib_stacks), Style.RESET_ALL))

    # Print the found I2C topology
    for address, stack in GRAPE.stacks.items():
        log_setup.info("Stack %s#%d%s found" % (Fore.WHITE, address, Style.RESET_ALL))

        log_setup.info("  %sMeters%s" % (Style.BRIGHT, Style.RESET_ALL))
        for device_class in grapelib.STACK_DEVICES:
            device_name = grapelib.get_device_name(device_class)
            if device_class in stack.grapelib_stack.devices:
                device = stack.grapelib_stack.devices[device_class]
                log_setup.info(
                    "    Detected %s%s%s at address %s0x%02X%s" % (
                        Fore.LIGHTBLUE_EX, device_name, Style.RESET_ALL, Fore.YELLOW, device._address, Style.RESET_ALL
                    )
                )
            else:
                log_setup.info(
                    "    %s%s%s not found" % (
                        Fore.LIGHTBLUE_EX, device_name, Style.RESET_ALL
                    )
                )

        log_setup.info("  %sPi devices%s" % (Style.BRIGHT, Style.RESET_ALL))

        for pidevice_add, pidevice in enumerate(stack.pi_devices):
            log_setup.info("    Slot %s#%d%s" % (
                Fore.WHITE, pidevice_add, Style.RESET_ALL
            ))
            if pidevice is not None:
                log_setup.info("      MAC: %s%s%s" % (
                    Fore.WHITE, pidevice.mac, Style.RESET_ALL
                ))
            else:
                log_setup.info("      Closed")

    if grapelib_display is not None:
        log_setup.info(
            "Detected %sDisplay%s at address %s0x%02X%s" % (
                Fore.LIGHTBLUE_EX, Style.RESET_ALL, Fore.YELLOW, grapelib_display._address, Style.RESET_ALL
            )
        )
    else:
        log_setup.warn("No %sDisplay%s detected" % (
            Fore.LIGHTBLUE_EX, Style.RESET_ALL
        ))

    # Setup the filesystems for netbooting
    if config["netboot"]["active"]:
        log_setup.info("Netboot is activated")

        log_setup.info("Creating folders for NFS and OverlayFS")
        for stack_add, stack in GRAPE.stacks.items():
            for device_add, device in enumerate(stack.pi_devices):
                if device is not None:
                    mac = device.mac
                    dashed_mad = to_dashed_mac_address(mac)

                    tftpboot_dir = "%s/%s" % (config["netboot"]["boot_dir"], dashed_mad)
                    netboot_dir = "%s/%s" % (config["netboot"]["nfs_dir"], dashed_mad)

                    if not os.path.exists(netboot_dir):
                        log_setup.info("  Creating %s\"%s\"%s" % (Fore.YELLOW, netboot_dir, Style.RESET_ALL))
                        os.makedirs(netboot_dir)
                    else:
                        log_setup.info("  %s\"%s\"%s already exists" % (Fore.YELLOW, netboot_dir, Style.RESET_ALL))

                    # Setting up the boot directory
                    execute_command([
                        "cp", "-r", config["netboot"]["base_boot_dir"] + "/.", tftpboot_dir
                    ])

                    # Change cmdline.txt so that it netboots.
                    # It contains one line, and we change everything after `root=...` by `to_replace`
                    to_replace = "root=/dev/nfs nfsroot=%s:%s,vers=3 rw ip=dhcp rootwait elevator=deadline" % (
                        config["netboot"]["netboot_ip"], netboot_dir
                    )
                    with open("%s/cmdline.txt" % tftpboot_dir, "r") as file:
                        line = file.readline().rstrip()

                    line_parts = line.split("root=")
                    to_write = line_parts[0] + to_replace

                    with open("%s/cmdline.txt" % tftpboot_dir, "w") as file:
                        file.write(to_write)

                    # Setting up the filesystem
                    execute_command([
                        "rsync", "-xa", "--progress", config["netboot"]["base_nfs_dir"] + "/", netboot_dir
                    ])
    else:
        log_setup.info("Netboot has been deactivated in the config file")

    # Start the management of the Grape cluster.
    # This will launch the different threads (scanning, reading meters, ...)
    GRAPE.start()

    # Launch the REST server thread
    rest_server_thread = rest_server.RestServerThread(GRAPE)
    # Running in daemon makes the thread stops when SINGINT is sent
    rest_server_thread.daemon = True
    rest_server_thread.start()

    while True:
        try:
            grapelib_display.clear_screen()
            grapelib_display.print_str("Welcome grape !")
            grapelib_display.position(1, 0)
            stack = grapelib_stacks[0]
            if grapelib.PowerMeter in stack.devices:
                grapelib_display.print_str("%dC %dmW %dmA" % (
                    GRAPE.stacks[0].temperature, GRAPE.stacks[0].power, GRAPE.stacks[0].current
                ))
            else:
                grapelib_display.print_str("%dC" % GRAPE.stacks[0].temperature)
        except IOError as e:
            log_setup.warning("Couldn't write on display")

        sleep(1)
