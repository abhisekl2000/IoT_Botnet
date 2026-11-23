import argparse
import csv
import random
import threading
import time

from pathlib import Path

from iot_device import IoTDevice


def main():

    parser = argparse.ArgumentParser(
        description="Simulate an IoT MQTT network"
    )

    parser.add_argument(
        "--run-id",
        default="run_001"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=120
    )

    parser.add_argument(
        "--compromise-time",
        type=int,
        default=60
    )

    parser.add_argument(
        "--compromised-device",
        choices=[
            "thermostat_01",
            "camera_01",
            "sensor_01",
            "none"
        ],
        default="sensor_01"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be positive")

    if (
        args.compromised_device != "none"
        and not 0 < args.compromise_time < args.duration
    ):
        parser.error(
            "Compromise time must be between "
            "0 and simulation duration"
        )

    rng = random.Random(args.seed)

    devices = [

        IoTDevice(
            "thermostat_01",
            "thermostat",
            seed=rng.randrange(2**32)
        ),

        IoTDevice(
            "camera_01",
            "camera",
            seed=rng.randrange(2**32)
        ),

        IoTDevice(
            "sensor_01",
            "sensor",
            seed=rng.randrange(2**32)
        )
    ]

    output_dir = (
        Path("data/simulation") / args.run_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    ground_truth_path = (
        output_dir / "ground_truth.csv"
    )

    threads = []

    try:

        # Connect all devices
        for device in devices:
            device.connect()

        with ground_truth_path.open(
            "w",
            newline=""
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "run_id",
                "device_id",
                "timestamp",
                "state"
            ])

            start_time = time.time()
            start_monotonic = time.monotonic()

            # Record initial normal states
            for device in devices:

                writer.writerow([
                    args.run_id,
                    device.device_id,
                    start_time,
                    0
                ])

            file.flush()

            print("\nStarting IoT simulation...")

            print(f"Run ID: {args.run_id}")
            print(f"Duration: {args.duration}s")
            print(f"Random seed: {args.seed}")
            print(
                f"Compromised device: "
                f"{args.compromised_device}"
            )

            # Run devices concurrently
            for device in devices:

                thread = threading.Thread(
                    target=device.run,
                    kwargs={
                        "duration": args.duration
                    },
                    name=device.device_id
                )

                threads.append(thread)
                thread.start()

            compromised = False

            # Monitor simulation duration
            while True:

                elapsed = (
                    time.monotonic() - start_monotonic
                )

                if elapsed >= args.duration:
                    break

                # Schedule simulated compromise
                if (
                    not compromised
                    and args.compromised_device != "none"
                    and elapsed >= args.compromise_time
                ):

                    for device in devices:

                        if (
                            device.device_id
                            == args.compromised_device
                        ):

                            device.set_compromised(True)

                            writer.writerow([
                                args.run_id,
                                device.device_id,
                                time.time(),
                                1
                            ])

                            file.flush()

                            compromised = True

                            break

                time.sleep(0.1)

            # Wait for devices to finish
            for thread in threads:
                thread.join()

        print("\nSimulation completed.")

        print(
            "Ground truth saved to:",
            ground_truth_path
        )

    except KeyboardInterrupt:

        print("\nSimulation interrupted.")

    finally:

        for device in devices:
            device.stop()

        for thread in threads:
            thread.join()

        for device in devices:

            if device.connected.is_set():
                device.disconnect()


if __name__ == "__main__":
    main()