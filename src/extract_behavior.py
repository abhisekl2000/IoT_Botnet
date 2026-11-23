"""Extract device-level behavioral features from MQTT traffic."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BEHAVIOR_FEATURES = [
    "message_count",
    "messages_per_second",
    "total_bytes",
    "avg_packet_size",
    "std_packet_size",
    "avg_interarrival_time",
    "std_interarrival_time"
]


# Associate TCP streams with MQTT devices
def identify_devices(traffic):

    connections = traffic[
        (traffic["mqtt.msgtype"] == 1)
        & traffic["mqtt.clientid"].notna()
    ]

    stream_mapping = dict(
        zip(
            connections["tcp.stream"],
            connections["mqtt.clientid"]
        )
    )

    print("\nTCP stream mapping:")

    for stream, device in stream_mapping.items():
        print(f"Stream {stream}: {device}")

    traffic = traffic.copy()

    traffic["device_id"] = (
        traffic["tcp.stream"].map(stream_mapping)
    )

    return traffic


# Determine the ground-truth label for a window
def get_window_label(
    ground_truth,
    device_id,
    window_start,
    window_end
):

    states = ground_truth[
        ground_truth["device_id"] == device_id
    ].sort_values("timestamp")

    previous_states = states[
        states["timestamp"] <= window_start
    ]

    if previous_states.empty:
        return None

    # State at the beginning of the window
    label = int(
        previous_states.iloc[-1]["state"]
    )

    # Check for state changes inside the window
    transitions = states[
        (states["timestamp"] > window_start)
        & (states["timestamp"] < window_end)
    ]

    if not transitions.empty:
        return None

    return label


# Calculate features for one observation window
def calculate_features(packets, window_size):

    packets = packets.sort_values(
        "frame.time_epoch"
    )

    message_count = len(packets)

    packet_sizes = packets["tcp.len"].to_numpy(
        dtype=float
    )

    timestamps = packets[
        "frame.time_epoch"
    ].to_numpy(dtype=float)

    # Time between successive messages
    intervals = np.diff(timestamps)

    features = {

        "message_count": message_count,

        "messages_per_second": (
            message_count / window_size
        ),

        "total_bytes": packet_sizes.sum(),

        "avg_packet_size": (
            packet_sizes.mean()
            if message_count > 0 else 0
        ),

        "std_packet_size": (
            packet_sizes.std()
            if message_count > 0 else 0
        ),

        "avg_interarrival_time": (
            intervals.mean()
            if len(intervals) > 0 else 0
        ),

        "std_interarrival_time": (
            intervals.std()
            if len(intervals) > 0 else 0
        )
    }

    return features


def main():

    parser = argparse.ArgumentParser(
        description="Extract MQTT behavioral features"
    )

    parser.add_argument(
        "--run-id",
        required=True
    )

    parser.add_argument(
        "--duration",
        required=True,
        type=int
    )

    parser.add_argument(
        "--window-size",
        type=int,
        default=10
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1883
    )

    args = parser.parse_args()

    if args.duration <= 0:
        parser.error("Duration must be positive")

    if args.window_size <= 0:
        parser.error("Window size must be positive")

    run_dir = (
        Path("data/simulation") / args.run_id
    )

    traffic_path = (
        run_dir / "captured_traffic.csv"
    )

    ground_truth_path = (
        run_dir / "ground_truth.csv"
    )

    output_path = (
        run_dir / "behavioral_features.csv"
    )

    # Load captured traffic and ground truth
    traffic = pd.read_csv(traffic_path)

    ground_truth = pd.read_csv(
        ground_truth_path
    )

    print("Run ID:", args.run_id)
    print("Captured records:", len(traffic))
    print("Ground-truth records:", len(ground_truth))

    # Convert required fields to numerical values
    numeric_columns = [
        "frame.time_epoch",
        "tcp.stream",
        "tcp.len",
        "tcp.dstport",
        "mqtt.msgtype"
    ]

    for column in numeric_columns:

        traffic[column] = pd.to_numeric(
            traffic[column],
            errors="coerce"
        )

    # Identify individual devices
    traffic = identify_devices(traffic)

    # Keep outgoing MQTT PUBLISH records only
    publish = traffic[
        (traffic["mqtt.msgtype"] == 3)
        & (traffic["tcp.dstport"] == args.port)
    ].copy()

    unknown_count = publish["device_id"].isna().sum()

    print(
        "\nUnidentified PUBLISH records:",
        unknown_count
    )

    if unknown_count > 0:
        raise ValueError(
            "Some PUBLISH records could not be "
            "associated with a device."
        )

    if publish.empty:
        raise ValueError(
            "No outgoing PUBLISH records found."
        )

    publish = publish.dropna(
        subset=["frame.time_epoch", "tcp.len"]
    )

    print("\nPUBLISH records:", len(publish))

    print("\nMessages per device:")

    print(
        publish["device_id"].value_counts()
    )

    # Determine simulation time boundaries
    start_time = ground_truth["timestamp"].min()

    end_time = start_time + args.duration

    devices = (
        ground_truth["device_id"]
        .unique()
        .tolist()
    )

    rows = []

    skipped_windows = 0

    # Only use complete observation windows
    number_of_windows = (
        args.duration // args.window_size
    )

    print("\nObservation window:", args.window_size)
    print("Windows per device:", number_of_windows)

    # Process each device independently
    for device_id in devices:

        device_packets = publish[
            publish["device_id"] == device_id
        ]

        for window_number in range(
            number_of_windows
        ):

            window_start = (
                start_time
                + window_number * args.window_size
            )

            window_end = (
                window_start + args.window_size
            )

            if window_end > end_time:
                continue

            # Select traffic inside this window
            packets = device_packets[
                (device_packets["frame.time_epoch"]
                 >= window_start)
                & (device_packets["frame.time_epoch"]
                   < window_end)
            ]

            # Determine the ground-truth label
            label = get_window_label(
                ground_truth,
                device_id,
                window_start,
                window_end
            )

            # Exclude mixed-state windows
            if label is None:

                skipped_windows += 1

                print(
                    f"Skipping mixed-state window: "
                    f"{device_id}, "
                    f"window {window_number}"
                )

                continue

            # Calculate behavioral features
            features = calculate_features(
                packets,
                args.window_size
            )

            row = {
                "run_id": args.run_id,
                "device_id": device_id,
                "window_start": window_start,
                "window_end": window_end,
                **features,
                "label": label
            }

            rows.append(row)

    # Construct the behavioral dataset
    result = pd.DataFrame(rows)

    if result.empty:
        raise ValueError(
            "No labeled observation windows generated."
        )

    result.to_csv(
        output_path,
        index=False
    )

    print("\nBehavioral feature extraction completed.")

    print("Observation windows:", len(result))

    print("Skipped windows:", skipped_windows)

    print("\nLabel distribution:")

    print(result["label"].value_counts())

    display_columns = [
        "device_id",
        "message_count",
        "messages_per_second",
        "total_bytes",
        "avg_interarrival_time",
        "label"
    ]

    print("\nBehavioral dataset:")

    print(
        result[display_columns].to_string(
            index=False
        )
    )

    print("\nSaved to:", output_path)


if __name__ == "__main__":
    main()