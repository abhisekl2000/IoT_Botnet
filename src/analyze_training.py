"""Compare legitimate and attack traffic characteristics."""

import pandas as pd
import joblib

TRAIN_PATH = "data/processed/train_binary.csv"

MODEL_PATH = (
    "results/random_forest/random_forest.joblib"
)


def main():

    df = pd.read_csv(TRAIN_PATH)

    bundle = joblib.load(MODEL_PATH)

    model = bundle["model"]
    features = bundle["features"]

    # Feature importance
    importance = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    })

    importance = importance.sort_values(
        "importance",
        ascending=False
    )

    print("\nFEATURE IMPORTANCE")
    print(importance.to_string(index=False))

    # Focus on MQTT PUBLISH packets
    publish = df[df["mqtt.msgtype"] == 3]

    selected_features = [
        "tcp.time_delta",
        "tcp.len",
        "mqtt.len"
    ]

    # Compare normal and malicious traffic
    for feature in selected_features:

        print(f"\nFEATURE: {feature}")

        for label in [0, 1]:

            traffic = publish[
                publish["label"] == label
            ][feature]

            name = (
                "Legitimate"
                if label == 0
                else "Attack"
            )

            print(f"\n{name} traffic:")

            print(
                traffic.describe(
                    percentiles=[
                        0.01,
                        0.25,
                        0.50,
                        0.75,
                        0.99
                    ]
                )
            )


if __name__ == "__main__":
    main()