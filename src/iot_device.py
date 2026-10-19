import json
import random
import time

import paho.mqtt.client as mqtt

class IoTDevice:
    ''' Simulates an IoT device that publishes MQTT messages '''
    def __init__(self, device_id, device_type, broker_host="localhost", broker_port=1883, compromised=False):
        self.device_id = device_id
        self.device_type = device_type
        self.compromised = compromised

        self.topic = f"iot/{self.device_id}/telemetry"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.device_id)

        self.broker_host = broker_host
        self.broker_port = broker_port

    # connect simulated device to Mosquitto
    def connect(self):
        ''' Connect this device to the MQTT broker '''
        self.client.connect(self.broker_host, self.broker_port, keepalive=60)
        self.client.loop_start()
        time.sleep(0.2)

        print(f"{self.device_id} connected to MQTT broker")
    
    def generate_message(self):
        ''' Generate telemetry for this device '''
        if self.device_type == "thermostat":
            payload = {"temperature": round(random.uniform(18, 30), 2)}
        elif self.device_type == "camera":
            payload = {"motion_detected": round(random.choice([True, False]))}
        else:
            payload = {"humidity": round(random.uniform(30, 80), 2)}
        
        payload = {
            "device_id": self.device_id,
            "timestamp": time.time()
        }

        return payload
    
    # publish telemetry to an MQTT topic
    def publish_message(self):
        ''' Publish one MQTT message '''
        payload = self.generate_message()

        result = self.client.publish(self.topic, json.dumps(payload), qos=0,)
        result.wait_for_publish()

        print(f"{self.device_id} published: {payload}")

    # repeatedly publish messages at a specified rate
    def run(self, message_count=5, interval=2):
        ''' Publish messages at a normal or abnormal rate '''
        try:
            for _ in range(message_count):
                self.publish_message()

                # simulated compromised devices publish much faster
                delay = 0.05 if self.compromised else interval
                time.sleep(delay)
        
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print(f"{self.device_id} disconnected")