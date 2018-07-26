#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
from colorama import Fore, Style


def handle_exception():
    pass


def status(options):
    r = requests.get("http://%s/" % (options.url))

    if r.status_code == 200:
        data = r.json()
        print("%sGrape Cluster%s" % (Style.BRIGHT, Style.RESET_ALL))

        for stack in data["stacks"]:
            print("  %s⬤%s  %sStack%s %s0x%02X%s" % (
                Fore.GREEN, Style.RESET_ALL, Style.BRIGHT, Style.RESET_ALL,
                Style.DIM, stack["address"], Style.RESET_ALL
            ))

            print("      %sDevices%s" % (Style.BRIGHT, Style.RESET_ALL))
            for device in stack["devices"]:
                if device is not None:
                    print("        %s⬤  Pi%s" % (
                        Fore.GREEN, Style.RESET_ALL
                    ))
                    print("          IP: %s%s%s" % (
                        Style.DIM, device["ip"], Style.RESET_ALL
                    ))
                else:
                    print("        %s⬤  None%s" % (Fore.RED, Style.RESET_ALL))

            meters = stack["meters"]

            print("      %sPower Meter%s" % (Style.BRIGHT, Style.RESET_ALL))
            power = meters["power"]

            if power["available"]:
                print("        Current: %s%.02f%s [mA]" % (
                    Style.DIM, power["current"] / 1000, Style.RESET_ALL
                ))
                print("        Voltage: %s%.01f%s [V]" % (
                    Style.DIM, power["voltage"] / 1000, Style.RESET_ALL
                ))
                print("        Power: %s%.02f%s [W]" % (
                    Style.DIM, power["power"] / 1000, Style.RESET_ALL
                ))
            else:
                print("        %sNot available%s" % (
                    Fore.RED, Style.RESET_ALL
                ))

            print("      %sPower Meter%s" % (Style.BRIGHT, Style.RESET_ALL))
            temperature = meters["temperature"]

            if temperature["available"]:
                print("        Temperature: %s%.01f%s [°C]" % (
                    Style.DIM, temperature["temperature"], Style.RESET_ALL
                ))
            else:
                print("        %sNot available%s" % (
                    Fore.RED, Style.RESET_ALL
                ))

        display = data["display"]
        if display["available"]:
            print("  %s⬤  Display available%s" % (Fore.GREEN, Style.RESET_ALL))
        else:
            print("  %s⬤  Display not available%s" % (Fore.RED, Style.RESET_ALL))


def power_all(options):
    requests.put("http://%s/stack/%d/power" % (options.url, options.stack), data={
        "power": True if options.power == "on" else False
    })


def power(options):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grape client to interact with graped")
    parser.add_argument("-u", "--url", default="localhost:5000", help="URL to the Master RPi")

    subparsers = parser.add_subparsers(title="command", help="command", dest="command")
    subparsers.required = True

    status_parser = subparsers.add_parser("status", help="Display the status of the grape")

    power_parser = subparsers.add_parser("power", help="Turn on or off the power of Pi")
    power_parser.add_argument("stack", help="Address of the stack", type=int)
    power_parser.add_argument("pi", help="Slot of the Pi", type=int)
    power_parser.add_argument("power", help="Whether to turn on or off", choices=["on", "off"])

    power_parser = subparsers.add_parser("powerall", help="Turn on or off the power of all Pis of a stack")
    power_parser.add_argument("stack", help="Address of the stack", type=int)
    power_parser.add_argument("power", help="Whether to turn on or off", choices=["on", "off"])

    read_meters_parser = subparsers.add_parser("read_meters", help="Force a read of the meters")

    options = parser.parse_args()

    if options.command == "status":
        status(options)
    elif options.command == "power":
        power(options)
    elif options.command == "powerall":
        power_all(options)
    elif options.command == "read_meters":
        pass
