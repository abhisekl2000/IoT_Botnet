"""Evaluate the MQTTset-trained Random Forest on simulated MQTT traffic."""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

from feature_extractor import extract_features


MODEL_PATH = Path(
    "results/random_forest/random_forest.joblib"
)


def main():

    parser = argparse.ArgumentParser(
        description="Evaluate Random Forest on simulated MQTT traffic"
    )

    parser.add_argument(
        "--run-id",
        required=True
    )

    args = parser.parse_args()

    run_dir = Path("data/simulation") / args.run_id

    traffic_path = run_dir / "captured_traffic.csv"
    truth_path = run_dir / "ground_truth.csv"

    output_dir = (
        Path("results/simulation_evaluation") / args.run_id
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing trained model
    bundle = joblib.load(MODEL_PATH)

    model = bundle["model"]
    features = bundle["features"]
    label_mapping = bundle["label_mapping"]

    normal_label = label_mapping["legitimate"]
    attack_label = label_mapping["attack"]

    print("\nExisting Random Forest loaded.")
    print("Required features:", len(features))

    # Load simulation traffic and ground truth
    traffic = pd.read_csv(
        traffic_path,
        low_memory=False
    )

    ground_truth = pd.read_csv(truth_path)

    print("Captured MQTT records:", len(traffic))
    print("Ground-truth events:", len(ground_truth))

    # Convert fields required for evaluation
    numeric_columns = [
        "frame.time_epoch",
        "tcp.stream",
        "tcp.srcport",
        "tcp.dstport",
        "mqtt.msgtype",
    ]

    for column in numeric_columns:
        traffic[column] = pd.to_numeric(
            traffic[column],
            errors="coerce"
        )

    ground_truth["timestamp"] = pd.to_numeric(
        ground_truth["timestamp"],
        errors="coerce"
    )

    ground_truth["state"] = pd.to_numeric(
        ground_truth["state"],
        errors="coerce"
    )

    # Map MQTT CONNECT messages to device identifiers
    connections = traffic[
        (traffic["mqtt.msgtype"] == 1)
        & traffic["mqtt.clientid"].notna()
    ]

    stream_mapping = {}

    for _, row in connections.iterrows():

        stream = row["tcp.stream"]
        device = row["mqtt.clientid"]

        if stream in stream_mapping:
            if stream_mapping[stream] != device:
                raise ValueError(
                    f"Conflicting device IDs for stream {stream}"
                )

        stream_mapping[stream] = device

    print("\nTCP stream mapping:")

    for stream, device in stream_mapping.items():
        print(f"Stream {stream}: {device}")

    traffic["device_id"] = (
        traffic["tcp.stream"].map(stream_mapping)
    )

    # Evaluate outgoing MQTT PUBLISH traffic only
    publish = traffic[
        (traffic["mqtt.msgtype"] == 3)
        & (traffic["tcp.dstport"] == 1883)
    ].copy()

    print("\nOutgoing PUBLISH records:", len(publish))

    if publish.empty:
        raise ValueError("No outgoing PUBLISH traffic found.")

    if publish["device_id"].isna().any():
        raise ValueError(
            "Some PUBLISH records have unidentified devices."
        )

    if publish["frame.time_epoch"].isna().any():
        raise ValueError(
            "Some PUBLISH records have missing timestamps."
        )

    # Assign ground-truth state using event timestamps
    labeled_groups = []

    for device_id, packets in publish.groupby("device_id"):

        events = ground_truth[
            ground_truth["device_id"] == device_id
        ].sort_values("timestamp")

        if events.empty:
            raise ValueError(
                f"No ground truth for device {device_id}"
            )

        packets = packets.sort_values(
            "frame.time_epoch"
        ).copy()

        # Match each packet with the latest state event
        labeled = pd.merge_asof(
            packets,
            events[["timestamp", "state"]],
            left_on="frame.time_epoch",
            right_on="timestamp",
            direction="backward",
        )

        labeled_groups.append(labeled)

    evaluated = pd.concat(
        labeled_groups,
        ignore_index=True
    )

    # Exclude packets without a valid ground-truth state.
    # This can include packets sent just before the
    # simulation's recorded start timestamp.
    missing_labels = evaluated["state"].isna().sum()

    print("Packets without ground truth:", missing_labels)

    evaluated = evaluated.dropna(
        subset=["state"]
    ).copy()

    if evaluated.empty:
        raise ValueError(
            "No packets could be matched to ground truth."
        )

    evaluated["actual_label"] = (
        evaluated["state"].astype(int)
    )

    # Apply the original MQTTset preprocessing
    X = extract_features(evaluated)
    X = X[features]

    print("\nPreprocessing completed.")
    print("Feature matrix shape:", X.shape)

    # Predict using the existing Random Forest
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    attack_index = list(model.classes_).index(
        attack_label
    )

    evaluated["prediction"] = predictions

    evaluated["attack_probability"] = (
        probabilities[:, attack_index]
    )

    evaluated["actual_state"] = evaluated[
        "actual_label"
    ].map({
        normal_label: "legitimate",
        attack_label: "attack",
    })

    evaluated["predicted_state"] = evaluated[
        "prediction"
    ].map({
        normal_label: "legitimate",
        attack_label: "attack",
    })

    # Evaluate model performance
    y_true = evaluated["actual_label"]
    y_pred = evaluated["prediction"]

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=[normal_label, attack_label]
    )

    tn, fp, fn, tp = cm.ravel()

    accuracy = accuracy_score(y_true, y_pred)

    precision = precision_score(
        y_true,
        y_pred,
        pos_label=attack_label,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        pos_label=attack_label,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        pos_label=attack_label,
        zero_division=0
    )

    false_positive_rate = (
        fp / (fp + tn)
        if fp + tn > 0
        else float("nan")
    )

    print("\n========== EVALUATION RESULTS ==========")

    print("Evaluated PUBLISH records:", len(evaluated))

    print("\nGround-truth distribution:")
    print(evaluated["actual_state"].value_counts())

    print("\nPrediction distribution:")
    print(evaluated["predicted_state"].value_counts())

    print("\nConfusion Matrix:")
    print("                 Predicted")
    print("                 Normal  Attack")
    print(f"Actual Normal    {tn:6}  {fp:6}")
    print(f"Actual Attack    {fn:6}  {tp:6}")

    print("\nPerformance Metrics:")

    print(f"Accuracy:            {accuracy:.4f}")
    print(f"Precision:           {precision:.4f}")
    print(f"Recall:              {recall:.4f}")
    print(f"F1-score:            {f1:.4f}")
    print(f"False-positive rate: {false_positive_rate:.4f}")

    print("\nClassification Report:")

    print(
        classification_report(
            y_true,
            y_pred,
            labels=[normal_label, attack_label],
            target_names=["legitimate", "attack"],
            zero_division=0,
        )
    )

    # Report performance for each device
    print("\n========== DEVICE-LEVEL SUMMARY ==========")

    for device_id, group in evaluated.groupby("device_id"):

        print(f"\nDevice: {device_id}")
        print("Packets evaluated:", len(group))

        print("Actual states:")
        print(group["actual_state"].value_counts())

        print("Predictions:")
        print(group["predicted_state"].value_counts())

        print(
            "Average attack probability:",
            round(group["attack_probability"].mean(), 4)
        )

    # Save packet-level evaluation
    predictions_path = (
        output_dir / "packet_predictions.csv"
    )

    evaluated.to_csv(
        predictions_path,
        index=False
    )

    # Save summary metrics
    metrics = pd.DataFrame([{
        "run_id": args.run_id,
        "evaluated_packets": len(evaluated),
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": false_positive_rate,
    }])

    metrics_path = output_dir / "metrics.csv"

    metrics.to_csv(
        metrics_path,
        index=False
    )

    print("\nResults saved to:")
    print(predictions_path)
    print(metrics_path)


if __name__ == "__main__":
    main()