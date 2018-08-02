#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import requests
from colorama import Fore, Style


def print_status_400(r):
    data = r.json()
    print("Status: %s" % data["status"])
    print("Error message: %s" % data["error"])


def status(options):
    r = requests.get("http://%s/" % (options.url))

    if r.status_code == 200:
        data = r.json()
        print("%sGrape Cluster%s" % (Style.BRIGHT, Style.RESET_ALL))

        for stack in data["stacks"]:
            print("  %s⬤%s %sStack%s %s0x%02X%s" % (
                Fore.GREEN, Style.RESET_ALL, Style.BRIGHT, Style.RESET_ALL,
                Style.DIM, stack["address"], Style.RESET_ALL
            ))

            print("    %sDevices%s" % (Style.BRIGHT, Style.RESET_ALL))
            for device in stack["devices"]:
                if device is not None:
                    if device["connected"]:
                        print("      %s⬤ Pi%s" % (
                            Fore.GREEN, Style.RESET_ALL
                        ))
                    else:
                        print("      %s⬤ Down%s" % (
                            Fore.RED, Style.RESET_ALL
                        ))

                    print("        MAC: %s%s%s" % (
                        Style.DIM, device["mac"], Style.RESET_ALL
                    ))
                    if device["ip"] is not None:
                        print("        IP: %s%s%s" % (
                            Style.DIM, device["ip"], Style.RESET_ALL
                        ))

                else:
                    print("      %s⬤ None%s" % (Style.DIM, Style.RESET_ALL))

            meters = stack["meters"]

            print("    %sPower Meter%s" % (Style.BRIGHT, Style.RESET_ALL))
            power = meters["power"]

            if power["available"]:
                print("      Current: %s%.02f%s [mA]" % (
                    Style.DIM, power["current"] / 1000, Style.RESET_ALL
                ))
                print("      Voltage: %s%.01f%s [V]" % (
                    Style.DIM, power["voltage"] / 1000, Style.RESET_ALL
                ))
                print("      Power: %s%.02f%s [W]" % (
                    Style.DIM, power["power"] / 1000, Style.RESET_ALL
                ))
            else:
                print("      %sNot available%s" % (
                    Fore.RED, Style.RESET_ALL
                ))

            print("    %sTemperature%s" % (Style.BRIGHT, Style.RESET_ALL))
            temperature = meters["temperature"]

            if temperature["available"]:
                print("      Temperature: %s%.01f%s [°C]" % (
                    Style.DIM, temperature["temperature"], Style.RESET_ALL
                ))
            else:
                print("        %sNot available%s" % (
                    Fore.RED, Style.RESET_ALL
                ))

        display = data["display"]
        if display["available"]:
            print("  %s⬤ Display available%s" % (Fore.GREEN, Style.RESET_ALL))
        else:
            print("  %s⬤ Display not available%s" % (Fore.RED, Style.RESET_ALL))


def power_all(options):
    r = requests.put("http://%s/stack/%d/power" % (options.url, options.stack), data={
        "power": options.power
    })

    if r.status_code == 200:
        print("OK")
    elif r.status_code == 400:
        print_status_400(r)
    else:
        print("Status code: %d" % r.status_code)
        print(r.raw)


def power(options):
    r = requests.put("http://%s/stack/%d/pi/%d/power" % (options.url, options.stack, options.pi), data={
        "power": options.power
    })

    if r.status_code == 200:
        print("OK")
    elif r.status_code == 400:
        print_status_400(r)


def ssh(options):
    r = requests.post("http://%s/stack/%d/pi/%d/ssh" % (options.url, options.stack, options.pi), data={
        "command": options.ssh_command,
        "timeout": options.timeout
    })

    print(r.json())


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

    power_all_parser = subparsers.add_parser("powerall", help="Turn on or off the power of all Pis of a stack")
    power_all_parser.add_argument("stack", help="Address of the stack", type=int)
    power_all_parser.add_argument("power", help="Whether to turn on or off", choices=["on", "off"])

    ssh_parser = subparsers.add_parser("ssh", help="Execute an SSH command on a Pi device")
    ssh_parser.add_argument("stack", help="Address of the stack", type=int)
    ssh_parser.add_argument("pi", help="Slot of the Pi", type=int)
    ssh_parser.add_argument("ssh_command", help="Command to execute")
    ssh_parser.add_argument("--timeout", default=None, required=False)

    options = parser.parse_args()

    if options.command == "status":
        status(options)
    elif options.command == "power":
        power(options)
    elif options.command == "powerall":
        power_all(options)
    elif options.command == "ssh":
        ssh(options)
