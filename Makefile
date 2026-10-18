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
	sudo systemctl enable --now mosquitto

# create virtual environment and install python libraries
python:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt

# check the MQTT broker
broker-status:
	systemctl is-active mosquitto

# verify python imports
test:
	$(VENV)/bin/python -c "import paho.mqtt.client, pandas, numpy, sklearn, joblib, matplotlib; print('Dependencies OK')"

# remove only the project's virtual environment
clean:
	rm -rf $(VENV)