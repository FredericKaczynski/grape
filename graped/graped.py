#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import logging
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

log_setup = logging.getLogger("setup")
log_scan_ip = logging.getLogger("scan")
log_read_meters = logging.getLogger("read_meters")


class Grape(object):
    def __init__(self, grapelib_stacks, grapelib_display):
        self.grapelib_stacks = grapelib_stacks
        self.stacks = {}
        for address, stack in grapelib_stacks.items():
            self.stacks[address] = Stack(address, stack)

        self.grapelib_display = grapelib_display
        self.display_available = grapelib_display is not None

        # Launch scan thread
        self.scan_thread = Thread(target=self.scan_thread_function)
        # Running in daemon makes the thread stops when SINGINT is sent
        self.scan_thread.daemon = True
        self.scan_thread.start()

    def scan_thread_function(self):
        while True:
            self.scan()
            sleep(5)

    def scan(self):
        range_begin = parse_ip(config["network"]["range_begin"])
        range_end = parse_ip(config["network"]["range_end"])
        timeout = config["network"]["ssh_test_timeout"]
        port = 22

        log_scan_ip.info("Beginning IP scan")
        for i in range(range_begin[3], range_end[3] + 1):
            ip = to_ip(range_begin[0:3] + [i])

            log_scan_ip.info("  Connecting to %s (Timeout: %.2fs)" % (ip, timeout))
            # We check if the ssh port of this host is open
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            res = sock.connect_ex((ip, port))

            if res == 0:
                log_scan_ip.info("    Connection successful")
                # Check if we already had a pi with this address
                stack = self.stacks[0]
                if any([s.ip == ip for s in filter(lambda s: s is not None, stack.pi_devices)]):
                    log_scan_ip.info("    IP was already discovered")
                else:
                    log_scan_ip.info("    New IP")

                    # Find an available slot
                    first_i = 0
                    while stack.pi_devices[first_i] is not None and first_i < len(stack.pi_devices):
                        first_i += 1

                    if first_i < len(stack.pi_devices):
                        log_scan_ip.info("    Pi Device added")
                        stack.pi_devices[first_i] = PiDevice()
                        stack.pi_devices[first_i].ip = ip
                    else:
                        log_scan_ip.info("    Not enough slot")

            else:
                log_scan_ip.info("    Failed connection")


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

        self.read_meters_thread = Thread(target=self.read_meters_thread_function)
        # Running in daemon makes the thread stops when SINGINT is sent
        self.read_meters_thread.daemon = True
        self.read_meters_thread.start()

    def read_meters_thread_function(self):
        while True:
            self.read_meters()
            sleep(1)

    def read_meters(self):
        log_read_meters.info("Begin reading meters")

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
            log_read_meters.warn("Error while reading meters")


class PiDevice(object):
    def __init__(self):
        pass
        self.ip = None


def parse_ip(str):
    parts = str.split('.')
    if len(parts) != 4:
        log_scan_ip.error("IP in config should in the form X.X.X.X, but was %s" % str)
        raise Exception()

    return [int(part) for part in parts]


def setup_host(ip):
    pass


def to_ip(parts):
    return '.'.join([str(part) for part in parts])


class RestServerThread(Thread):
    def run(self):
        rest_server.start_rest_server(grape)


if __name__ == "__main__":
    # Setting up the log format
    FORMAT = "[" + Fore.YELLOW + "%(asctime)s" + Style.RESET_ALL + "][%(levelname)s][%(name)s] %(message)s"
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

    log_setup.info("Scanning the I2C buses")
    buses, stacks, display = grapelib.get_stacks()

    if len(stacks) == 0:
        log_setup.error("No stack found")
        sys.exit(1)

    log_setup.info("%s%d%s stacks found" % (Fore.WHITE, len(stacks), Style.RESET_ALL))

    for address, stack in stacks.items():
        log_setup.info("Stack %s#%d%s found" % (Fore.WHITE, address, Style.RESET_ALL))
        for device_class in grapelib.STACK_DEVICES:
            if device_class in stack.devices:
                device = stack.devices[device_class]
                device_name = grapelib.get_device_name(device_class)
                log_setup.info(
                    "  Detected %s%s%s at address %s0x%02X%s" % (
                        Fore.LIGHTBLUE_EX, device_name, Style.RESET_ALL, Fore.WHITE, device._address, Style.RESET_ALL
                    )
                )

    if display is not None:
        log_setup.info(
            "  Detected %sDisplay%s at address %s0x%02X%s" % (
                Fore.LIGHTBLUE_EX, Style.RESET_ALL, Fore.WHITE, display._address, Style.RESET_ALL
            )
        )
    else:
        log_setup.warn("No %sDisplay%s detected" % (
            Fore.LIGHTBLUE_EX, Style.RESET_ALL
        ))

    grape = Grape(stacks, display)

    # Launch the REST server thread
    rest_server_thread = RestServerThread()
    # Running in daemon makes the thread stops when SINGINT is sent
    rest_server_thread.daemon = True
    rest_server_thread.start()

    display.clear_screen()
    display.print_str("Welcome grape !")

    while True:
        try:
            display.position(1, 0)
            stack = stacks[0]
            if grapelib.PowerMeter in stack.devices:
                display.print_str("%dC %dmW %dmA" % (
                    grape.stacks[0].temperature, grape.stacks[0].power, grape.stacks[0].current
                ))
            else:
                display.print_str("%dC" % grape.stacks[0].temperature)
        except IOError as e:
            log_setup.warn("Could write on display")

        sleep(1)
