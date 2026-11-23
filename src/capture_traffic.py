"""Capture MQTT traffic for behavioral analysis."""

import argparse
import subprocess
from pathlib import Path


FIELDS = [
    "frame.number",
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "tcp.srcport",
    "tcp.dstport",
    "tcp.stream",
    "tcp.len",
    "mqtt.msgtype",
    "mqtt.clientid",
    "mqtt.topic",
    "mqtt.len"
]


def main():

    parser = argparse.ArgumentParser(
        description="Capture MQTT network traffic"
    )

    parser.add_argument(
        "--run-id",
        required=True
    )

    parser.add_argument(
        "--interface",
        default="lo"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1883
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = (
        Path("data/simulation") / args.run_id
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path = (
        output_dir / "captured_traffic.csv"
    )

    # Construct TShark command
    command = [
        "tshark",
        "-i", args.interface,
        "-l",
        "-f", f"tcp port {args.port}",
        "-Y", "mqtt",
        "-T", "fields",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d",
        "-E", "occurrence=f"
    ]

    # Add required fields
    for field in FIELDS:

        command.extend([
            "-e", field
        ])

    print("Starting MQTT traffic capture...")
    print("Run ID:", args.run_id)
    print("Interface:", args.interface)
    print("Output:", output_path)
    print("Press Ctrl+C to stop capturing.\n")

    with output_path.open("w") as file:

        process = subprocess.Popen(
            command,
            stdout=file
        )

        try:

            return_code = process.wait()

            if return_code != 0:

                raise RuntimeError(
                    f"TShark exited with code "
                    f"{return_code}"
                )

        except KeyboardInterrupt:

            print("\nStopping traffic capture...")

            if process.poll() is None:

                process.terminate()
                process.wait()

    print("Capture completed.")
    print("Traffic saved to:", output_path)


if __name__ == "__main__":
    main()