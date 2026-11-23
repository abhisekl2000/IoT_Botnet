"""Automate MQTT simulation, packet capture, and feature extraction."""

import argparse
import csv
import signal
import subprocess
import sys
import time
from pathlib import Path


FIELDS = [
    # Packet identification and device mapping
    "frame.number",
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "tcp.srcport",
    "tcp.dstport",
    "tcp.stream",
    "mqtt.clientid",
    "mqtt.topic",

    # Original MQTTset Random Forest features
    "tcp.flags",
    "tcp.time_delta",
    "tcp.len",
    "mqtt.conack.flags",
    "mqtt.conack.val",
    "mqtt.conflag.cleansess",
    "mqtt.conflag.passwd",
    "mqtt.conflag.uname",
    "mqtt.conflags",
    "mqtt.dupflag",
    "mqtt.hdrflags",
    "mqtt.kalive",
    "mqtt.len",
    "mqtt.msgtype",
    "mqtt.proto_len",
    "mqtt.protoname",
    "mqtt.qos",
    "mqtt.retain",
    "mqtt.ver",
]


def run_experiment(
    run_id,
    duration,
    compromise_time,
    compromised_device,
    seed,
    window_size,
):
    output_dir = Path("data/simulation") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    traffic_path = output_dir / "captured_traffic.csv"
    ground_truth_path = output_dir / "ground_truth.csv"
    features_path = output_dir / "behavioral_features.csv"
    log_path = output_dir / "tshark.log"

    # Prevent accidental mixing with an earlier experiment.
    for path in (traffic_path, ground_truth_path, features_path):
        if path.exists():
            raise FileExistsError(
                f"{path} already exists. Use a new run ID."
            )

    capture_command = [
        "tshark",
        "-i", "lo",
        "-l",
        "-f", "tcp port 1883",
        "-Y", "mqtt",
        "-T", "fields",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d",
        "-E", "occurrence=f",
    ]

    for field in FIELDS:
        capture_command.extend(["-e", field])

    simulation_command = [
        sys.executable,
        "src/simulation.py",
        "--run-id", run_id,
        "--duration", str(duration),
        "--compromise-time", str(compromise_time),
        "--compromised-device", compromised_device,
        "--seed", str(seed),
    ]

    extraction_command = [
        sys.executable,
        "src/extract_behavior.py",
        "--run-id", run_id,
        "--duration", str(duration),
        "--window-size", str(window_size),
    ]

    print(f"\nStarting experiment: {run_id}", flush=True)

    # Capture must start before devices connect.
    with (
        traffic_path.open("w") as traffic_file,
        log_path.open("w") as log_file,
    ):
        capture = subprocess.Popen(
            capture_command,
            stdout=traffic_file,
            stderr=log_file,
        )

        try:
            # Allow TShark time to initialize.
            time.sleep(3)

            if capture.poll() is not None:
                raise RuntimeError(
                    f"TShark exited early. Check {log_path}"
                )

            print("Running IoT simulation...", flush=True)

            subprocess.run(
                simulation_command,
                check=True,
            )

            # Allow final packets to reach the capture process.
            time.sleep(1)

        finally:
            if capture.poll() is None:
                capture.send_signal(signal.SIGINT)

                try:
                    capture.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    capture.terminate()
                    capture.wait(timeout=5)

    if capture.returncode != 0:
        raise RuntimeError(
            f"TShark failed. Check {log_path}"
        )

    # Verify the capture contains usable MQTT records.
    with traffic_path.open(newline="") as file:
        reader = csv.DictReader(file)
        records = list(reader)

    if not records:
        raise RuntimeError(
            f"No MQTT records captured. Check {log_path}"
        )

    if not ground_truth_path.exists():
        raise RuntimeError(
            "Simulation did not generate ground truth."
        )

    print(
        f"Captured MQTT records: {len(records)}",
        flush=True,
    )

    print("Extracting behavioral features...", flush=True)

    subprocess.run(
        extraction_command,
        check=True,
    )

    if not features_path.exists():
        raise RuntimeError(
            "Behavioral feature extraction produced no file."
        )

    print(f"\nExperiment completed: {run_id}")
    print(f"Traffic: {traffic_path}")
    print(f"Ground truth: {ground_truth_path}")
    print(f"Features: {features_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--run-id", required=True)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--compromise-time", type=int, default=30)

    parser.add_argument(
        "--compromised-device",
        choices=[
            "thermostat_01",
            "camera_01",
            "sensor_01",
            "none",
        ],
        default="sensor_01",
    )

    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--window-size", type=int, default=10)

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("--duration must be positive")

    if args.window_size <= 0:
        parser.error("--window-size must be positive")

    if args.duration % args.window_size != 0:
        parser.error(
            "--duration must be divisible by --window-size"
        )

    if (
        args.compromised_device != "none"
        and not 0 < args.compromise_time < args.duration
    ):
        parser.error(
            "--compromise-time must be between 0 and duration"
        )

    run_experiment(
        run_id=args.run_id,
        duration=args.duration,
        compromise_time=args.compromise_time,
        compromised_device=args.compromised_device,
        seed=args.seed,
        window_size=args.window_size,
    )


if __name__ == "__main__":
    main()