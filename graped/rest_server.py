from threading import Thread

from colorama import Fore, Style
from flask import Flask, jsonify, request
import grapelib
import logging

app = Flask(__name__)
GRAPE = None
rest_logger = logging.getLogger("rest")


@app.route("/")
def status():
    data = {
        "stacks": [
            {
                "address": stack.address,
                "meters": {
                    "time_last_reading": stack.time_last_reading,
                    "temperature": {
                        "available": stack.temperature_available,
                        "temperature": stack.temperature
                    },
                    "power": {
                        "available": stack.power_available,
                        "power": stack.power,
                        "current": stack.current,
                        "voltage": stack.voltage
                    }
                },
                "max_count_devices": stack.MAX_PI_DEVICES_PER_STACK,
                "devices": [
                    {
                        "address": i,
                        "connected": device.connected,
                        "mac": device.mac,
                        "ip": device.ip
                    } if device is not None else None for i, device in enumerate(stack.pi_devices)
                ]
            } for stack in GRAPE.stacks.itervalues()
        ],
        "display": {
            "available": GRAPE.display_available
        }
    }
    return jsonify(data)


@app.route("/stack/<int:stack_id>/pi/<int:pi_id>/ssh", methods=["POST"])
def ssh(stack_id, pi_id):
    command = request.form["command"]
    timeout = request.form["timeout"] if "timeout" in request.form else None

    if stack_id not in GRAPE.stacks:
        return jsonify({
            "status": "error",
            "error": "Stack %d doesn't exist" % stack_id
        }), 400

    stack = GRAPE.stacks[stack_id]

    if pi_id < 0 or pi_id >= len(stack.pi_devices):
        return jsonify({
            "status": "error",
            "error": "Device %d doesn't exist on stack %d " % (pi_id, stack_id)
        }), 400

    pi_device = stack.pi_devices[pi_id]

    if pi_device is None:
        return jsonify({
            "status": "error",
            "error": "Device %d doesn't exist on stack %d " % (pi_id, stack_id)
        }), 400

    return_code, stdout, stderr = pi_device.execute_ssh(command, timeout)

    data = {
        "status": "ok",
        "return_code": return_code,
        "stdout": stdout,
        "stderr": stderr
    }

    return jsonify(data)


@app.route("/stack/<int:stack_id>/pi/<int:pi_id>/power", methods=["PUT"])
def power(stack_id, pi_id):
    if stack_id not in GRAPE.stacks:
        return jsonify({
            "status": "error",
            "error": "Stack %d does not exist" % stack_id
        }), 400

    stack = GRAPE.stacks[stack_id]

    if pi_id < 0 or pi_id >= len(stack.pi_devices):
        return jsonify({
            "status": "error",
            "error": "Device %d doesn't exist on stack %d " % (pi_id, stack_id)
        }), 400

    pi_device = stack.pi_devices[pi_id]

    if pi_device is None:
        return jsonify({
            "status": "error",
            "error": "Device %d doesn't exist on stack %d " % (pi_id, stack_id)
        }), 400

    on_or_off = request.form["power"]

    if on_or_off not in ["on", "off"]:
        return jsonify({
            "status": "error",
            "error": "power argument must be \"on\" or \"off\""
        }), 400

    stack.grapelib_stack[grapelib.PowerSwitch][pi_id] = on_or_off == "on"

    return jsonify({
        "status": "ok"
    })


@app.route("/stack/<int:stack_id>/power", methods=["PUT"])
def power_all(stack_id):
    rest_logger.info("Data: %s" % request.form)
    if stack_id not in GRAPE.stacks:
        return jsonify({
            "status": "error",
            "error": "Stack %d does not exist" % stack_id
        }), 400

    stack = GRAPE.stacks[stack_id]

    if grapelib.PowerSwitch not in stack.grapelib_stack.devices:
        return jsonify({
            "status": "error",
            "error": "Stack %d does not have power switches" % stack_id
        }), 400

    on_or_off = request.form["power"]

    if on_or_off not in ["on", "off"]:
        return jsonify({
            "status": "error",
            "error": "power argument must be \"on\" or \"off\""
        }), 400

    if on_or_off == "on":
        stack.grapelib_stack.devices[grapelib.PowerSwitch].start_all()
    elif on_or_off == "off":
        stack.grapelib_stack.devices[grapelib.PowerSwitch].stop_all()

    return jsonify({
        "status": "ok"
    })


def start_rest_server(grape_given):
    global GRAPE
    GRAPE = grape_given

    port = GRAPE.config["rest_server"]["port"]
    rest_logger.info("Launching REST server on port %s%d%s" % (Fore.YELLOW, port, Style.RESET_ALL))
    app.run(host="0.0.0.0", port=port)


class RestServerThread(Thread):
    def __init__(self, grape):
        super(RestServerThread, self).__init__()
        self.grape = grape

    def run(self):
        start_rest_server(self.grape)
