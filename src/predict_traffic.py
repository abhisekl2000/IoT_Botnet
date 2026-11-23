"""Classify captured MQTT traffic using Random Forest."""

from pathlib import Path

import joblib
import pandas as pd

from feature_extractor import extract_features


MODEL_PATH = Path(
    "results/random_forest/random_forest.joblib"
)

INPUT_PATH = Path(
    "data/live/captured_traffic.csv"
)

OUTPUT_PATH = Path(
    "results/live_detection/predictions.csv"
)


def main():

    # Load trained model
    bundle = joblib.load(MODEL_PATH)

    model = bundle["model"]
    features = bundle["features"]
    label_mapping = bundle["label_mapping"]

    print("[INFO] Random Forest loaded.")
    print("[INFO] Required features:", len(features))

    # Load captured traffic
    raw_df = pd.read_csv(
        INPUT_PATH,
        low_memory=False
    )

    print("[INFO] Captured packets:", len(raw_df))

    # Prepare traffic for prediction
    X = extract_features(raw_df)

    X = X[features]

    print("[INFO] Preprocessing completed.")

    # Classify captured traffic
    predictions = model.predict(X)

    probabilities = model.predict_proba(X)

    attack_index = list(model.classes_).index(
        label_mapping["attack"]
    )

    # Convert numerical labels to readable names
    reverse_mapping = {
        value: key
        for key, value in label_mapping.items()
    }

    # Preserve original captured traffic
    results = raw_df.copy()

    results["prediction"] = predictions

    results["predicted_label"] = (
        results["prediction"].map(reverse_mapping)
    )

    results["attack_probability"] = (
        probabilities[:, attack_index]
    )

    # Add packet number
    results.insert(
        0,
        "packet",
        range(1, len(results) + 1)
    )

    # Display selected results
    display_columns = [
        "packet",
        "tcp.time_delta",
        "tcp.len",
        "mqtt.msgtype",
        "predicted_label",
        "attack_probability"
    ]

    print("\nPacket classification results:\n")

    print(
        results[display_columns].to_string(
            index=False
        )
    )

    # Display prediction summary
    print("\nClassification summary:")

    print(
        results["predicted_label"].value_counts()
    )

    # Save predictions
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print("\n[INFO] Results saved to:", OUTPUT_PATH)


if __name__ == "__main__":
    main()