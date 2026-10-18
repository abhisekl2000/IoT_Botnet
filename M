.PHONY: setup system python broker-status test clean

PYTHON := python3
VENV := .VENV
PIP := $(VENV)/bin/pip

# install system dependeincies and configure Python
setup: system python

#install ubuntu packages
system: 
	sudo apt update
	sudo apt install -y mosquitto mosquitto-clients python3-venv python3-pip
	sudo systemtl enable --now mosquitto

# create virtual environment and install python libraries
python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt