from flask import Flask, jsonify, request
import grapelib
import logging

app = Flask(__name__)
grape = None
rest_logger = logging.getLogger("rest")


@app.route("/")
def test():
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
                        "ip": device.ip
                    } if device is not None else None for device in stack.pi_devices
                ]
            } for stack in grape.stacks.itervalues()
        ],
        "display": {
            "available": grape.display_available
        }
    }
    return jsonify(data)


@app.route("/stack/<int:stack_id>/pi/<int:pi_id>/power", methods=["PUT"])
def power(stack_id, pi_id):
    rest_logger.info("Data: %s" % request.form)
    if stack_id not in grape.stacks:
        return "", 400

    stack = grape.stacks[stack_id]

    if pi_id < 0 or pi_id >= len(stack.pi_devices):
        return "", 400

    # Does nothing for the moment

    return "Power switched !"


@app.route("/stack/<int:stack_id>/power", methods=["PUT"])
def power_all(stack_id):
    rest_logger.info("Data: %s" % request.form)
    if stack_id not in grape.stacks:
        return "", 400

    stack = grape.stacks[stack_id]

    if grapelib.PowerSwitch not in stack.grapelib_stack.devices:
        return "", 400

    on_or_off = request.form["power"]

    if on_or_off:
        stack.grapelib_stack.devices[grapelib.PowerSwitch].start_all()
    else:
        stack.grapelib_stack.devices[grapelib.PowerSwitch].stop_all()

    return "OK!", 200


def start_rest_server(grape_given):
    global grape
    grape = grape_given

    app.run(host="0.0.0.0")
