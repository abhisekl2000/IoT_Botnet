import json
import random
import time
import threading

import paho.mqtt.client as mqtt


class IoTDevice:
    """Simulates an IoT device that publishes MQTT messages."""

    def __init__(
        self,
        device_id,
        device_type,
        broker_host="localhost",
        broker_port=1883,
        compromised=False,
        seed=None
    ):
        self.device_id = device_id
        self.device_type = device_type
        self.compromised = compromised

        self.broker_host = broker_host
        self.broker_port = broker_port

        self.random = random.Random(seed)

        self.topic = f"iot/{self.device_id}/telemetry"

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=self.device_id
        )

        self.connected = threading.Event()
        self.stop_event = threading.Event()

        self.client.on_connect = self.on_connect

    # MQTT connection callback
    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties
    ):
        if reason_code == 0:
            self.connected.set()

    # Connect to Mosquitto
    def connect(self):
        """Connect this device to the MQTT broker."""

        self.connected.clear()

        self.client.connect(
            self.broker_host,
            self.broker_port,
            keepalive=60
        )

        self.client.loop_start()

        if not self.connected.wait(timeout=5):
            self.disconnect()
            raise ConnectionError(
                f"{self.device_id} failed to connect"
            )

        print(
            f"{self.device_id} connected to MQTT broker"
        )

    # Generate device-specific telemetry
    def generate_message(self):
        """Generate telemetry for this device."""

        if self.device_type == "thermostat":

            payload = {
                "temperature": round(
                    self.random.uniform(18, 30), 2
                )
            }

        elif self.device_type == "camera":

            payload = {
                "motion_detected": self.random.choice(
                    [True, False]
                )
            }

        else:

            payload = {
                "humidity": round(
                    self.random.uniform(30, 80), 2
                )
            }

        # Preserve device-specific telemetry
        payload.update({
            "device_id": self.device_id,
            "timestamp": time.time()
        })

        # Introduce variation in telemetry size
        if self.random.random() < 0.3:

            payload["battery"] = round(
                self.random.uniform(20, 100), 2
            )

        return payload

    # Publish telemetry
    def publish_message(self):
        """Publish one MQTT message."""

        payload = self.generate_message()

        result = self.client.publish(
            self.topic,
            json.dumps(payload),
            qos=0
        )

        result.wait_for_publish(timeout=5)

        if not result.is_published():
            raise RuntimeError(
                f"{self.device_id} failed to publish"
            )

    # Determine transmission interval
    def get_interval(self):

        if self.compromised:

            return self.random.uniform(0.05, 0.20)

        # Occasional normal traffic burst
        if self.random.random() < 0.05:

            return self.random.uniform(0.15, 0.5)

        # Normal device-specific behavior
        if self.device_type == "thermostat":

            return self.random.uniform(1, 3)

        elif self.device_type == "camera":

            return self.random.uniform(0.5, 2)

        else:

            return self.random.uniform(1, 4)

    # Change device state
    def set_compromised(self, state):

        self.compromised = state

        status = (
            "COMPROMISED"
            if state
            else "NORMAL"
        )

        print(f"{self.device_id} is now {status}")

    # Run continuously for a specified duration
    def run(self, duration=120):

        start_time = time.monotonic()
        message_count = 0

        try:

            while (
                time.monotonic() - start_time < duration
                and not self.stop_event.is_set()
            ):

                self.publish_message()

                message_count += 1

                delay = self.get_interval()

                remaining = duration - (
                    time.monotonic() - start_time
                )

                self.stop_event.wait(
                    max(0, min(delay, remaining))
                )

        finally:

            self.disconnect()

            print(
                f"{self.device_id} finished. "
                f"Messages published: {message_count}"
            )

    # Request device shutdown
    def stop(self):

        self.stop_event.set()

    # Disconnect from MQTT broker
    def disconnect(self):

        self.client.disconnect()
        self.client.loop_stop()
        self.connected.clear()