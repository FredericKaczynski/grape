#!/usr/bin/env python2
import os
from time import sleep

from colorama import Fore, Style
import subprocess
import requests

LOCATION_KEY = "./keys/id_rsa"
URL_GRAPED = "http://localhost:4000"
SWARM_IP_ADDR_ADVERTISE = "192.168.2.1:2377"
SWARM_TOKEN = None


def execute_command(command, silent=False):
    if not silent:
        print("Executing %s\"%s\"%s:" % (Fore.YELLOW, ' '.join(command), Style.RESET_ALL))
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # TODO: Find a way to both display in real-time stdout and stderr instead of waiting for
    # stderr to finish before displaying stdout
    stderr = []
    for line in p.stderr:
        line = line.rstrip()
        if not silent:
            print("  %s" % line)
        stderr.append(line)

    stdout = []
    for line in p.stdout:
        line = line.rstrip()
        if not silent:
            print("  %s" % line)
        stdout.append(line)

    return_code = p.wait()

    if not silent:
        print("Return code: %s%d%s" % (Fore.GREEN if return_code == 0 else Fore.RED, return_code, Style.RESET_ALL))

    return return_code, stdout, stderr


def remove_host(name):
    execute_command([
        "docker-machine", "rm",
        "-y", "-f",
        name
    ])


def setup_host(ip, name):
    remove_host(name)

    execute_command([
        "sshpass",
        "-p", "raspberry",
        "ssh-copy-id",
        "-i", "keys/id_rsa",
        "-o", "UserKnownHostsFile=/dev/null", "-o", "StrictHostKeyChecking=no",
        "pi@%s" % ip
    ])

    execute_command([
        "docker-machine", "create",
        "--driver", "generic",
        "--generic-ssh-user", "pi",
        "--generic-ip-address", ip,
        "--generic-ssh-key", LOCATION_KEY,
        # Specifying the storage driver is important as the RPi doesn't support aufs, which is the default
        # Not specifying this can make the docker installation unusable on the target machine
        "--engine-storage-driver", "overlay",
        name
    ])


def get_list_hosts():
    r, stdout, stderr = execute_command([
        "docker", "node", "ls",
        "--format", "{{.Hostname}}"
    ], silent=True)

    return stdout


def get_ip_of_host(host):
    r, stdout, stderr = execute_command([
        "docker", "node", "inspect",
        "-f", "{{.Status.Addr}}",
        host
    ], silent=True)
    return stdout[0]


def get_list_ips():
    hosts = get_list_hosts()

    r, stdout, stderr = execute_command([
            "docker", "node", "inspect",
            "-f", "{{.Status.Addr}}"
        ] + hosts, silent=True
    )

    return stdout


def get_token_worker():
    r, stdout, stderr = execute_command(["docker", "swarm", "join-token", "-q", "worker"])

    if r != 0:
        return None

    if len(stdout) != 1:
        return None

    return stdout[0]


if __name__ == "__main__":

    # Checking if keys are present
    if not os.path.isfile(LOCATION_KEY):
        print("Generating keys")
        execute_command([
            "ssh-keygen",
            "-f", LOCATION_KEY,
            "-N", ""
        ])
    else:
        print("Keys already exists")

    hosts = get_list_hosts()

    if "master" not in hosts:
        setup_host("localhost", "master")
    else:
        print("%smaster%s already listed in docker-machine" % (Fore.YELLOW, Style.RESET_ALL))

    # Are we part of a swarm ?
    SWARM_TOKEN = get_token_worker()

    if SWARM_TOKEN is None:
        print("Master doesn't have a swarm enabled")
        print("Initing a swarm")
        execute_command([
            "docker", "swarm", "init",
            "--advertise-addr", SWARM_IP_ADDR_ADVERTISE
        ])
        SWARM_TOKEN = get_token_worker()
    else:
        print("Master already is in swarm as manager")
        print("Not changing anything to the swarm")

    while True:
        data = None
        try:
            r = requests.get("%s/" % URL_GRAPED)
            data = r.json()
        except requests.exceptions.ConnectionError as e:
            print("Couldn't request graped")

        if data is not None:
            detected_ips = [
                device["ip"]
                for stack in data["stacks"]
                for device in stack["devices"] if device is not None and device["connected"]
            ]

            hostnames_in_swarm = get_list_hosts()
            print("List of hosts in swarm: %s" % (", ".join(hostnames_in_swarm)))

            for stack in data["stacks"]:
                for device in stack["devices"]:
                    if device is not None:
                        if device["connected"]:
                            ip = device["ip"]
                            hostname = "worker-%d-%d" % (stack["address"], device["address"])

                            setup_new_host = True

                            if hostname in hostnames_in_swarm:
                                print("%s%s%s is already in swarm..." % (Fore.YELLOW, hostname, Style.RESET_ALL))

                                ip_of_hostname_in_swarm = get_ip_of_host(hostname)
                                if ip != ip_of_hostname_in_swarm:
                                    print("...but with a different IP")
                                    print("Setting up this new device")

                                    print("Removing the ancient host from docker-machine")
                                else:
                                    print("...with the same IP")
                                    print("Not changing anything")
                                    setup_new_host = False

                            if setup_new_host:
                                print("Setting up %s%s%s (%s%s%s)" % (
                                    Fore.YELLOW, hostname, Style.RESET_ALL, Fore.YELLOW, ip, Style.RESET_ALL
                                ))
                                setup_host(ip, hostname)

                                # Join the swarm
                                execute_command([
                                    "docker-machine", "ssh", hostname,
                                    "sudo docker swarm join %s --token %s" % (SWARM_IP_ADDR_ADVERTISE, SWARM_TOKEN)
                                ])

        time_sleep = 5
        print("Waiting %s%d%s seconds for next scan" % (Fore.YELLOW, time_sleep, Style.RESET_ALL))
        sleep(time_sleep)
