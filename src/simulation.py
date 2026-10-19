import time
from iot_device import IoTDevice

def main():
    print("MAIN FUNCTION STARTED")
    devices = [
        IoTDevice("thermostat_01", "thermostat"),
        IoTDevice("camera_01", "camera"),
        IoTDevice("sensor_01", "sensor", compromised=True)
    ]

    try:
        for device in devices:
            device.connect()
        
        print("\nStarting simulated IoT traffic...\n")

        # run each devices sequentially for this initial test
        for device in devices:
            device.run(message_count=5, interval=2)
    
    except KeyboardInterrupt:
        print("Simulation interrupted.")

    finally:
        for device in devices:
            try:
                device.client.loop_stop()
                device.client.disconnect()
            except Exception:
                pass

if __name__ == "__main__":
    main()