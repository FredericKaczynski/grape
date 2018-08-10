# GrapeCLI

GrapeCLI is a small python command line program that queries the REST API of `graped` and outputs the result of the request.

## How to use

First install the dependencies:

```bash
pip install -r requirements.txt
```

To get the list of available commands, execute:

```bash
./grapecli.py
```

To get the status of the Grape cluster that is reachable at the IP `10.42.0.128`, you can do:

```bash
./grapecli.py -h 10.42.0.128:4000 status
```