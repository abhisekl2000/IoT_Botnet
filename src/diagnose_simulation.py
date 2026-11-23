"""Diagnose feature distributions in simulated MQTT traffic."""

import argparse
from pathlib import Path

import joblib
import pandas as pd

from feature_extractor import extract_features


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-id",
        required=True
    )

    args = parser.parse_args()

    model_path = Path(
        "results/random_forest/random_forest.joblib"
    )

    predictions_path = (
        Path("results/simulation_evaluation")
        / args.run_id
        / "packet_predictions.csv"
    )

    bundle = joblib.load(model_path)

    model = bundle["model"]
    features = bundle["features"]

    df = pd.read_csv(
        predictions_path,
        low_memory=False
    )

    X = extract_features(df)
    X = X[features]

    # Display feature importance
    importance = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    })

    importance = importance.sort_values(
        "importance",
        ascending=False
    )

    print("\n========== FEATURE IMPORTANCE ==========")

    print(
        importance.to_string(index=False)
    )

    # Compare legitimate and attack packets
    X["actual_state"] = df["actual_state"].values

    important_features = importance.head(8)["feature"].tolist()

    print("\n========== FEATURE DISTRIBUTIONS ==========")

    for feature in important_features:

        print(f"\nFeature: {feature}")

        print(
            X.groupby("actual_state")[feature].agg(
                ["count", "mean", "median", "min", "max"]
            ).to_string()
        )

    # Examine attack probabilities
    print("\n========== ATTACK PROBABILITIES ==========")

    print(
        df.groupby("actual_state")[
            "attack_probability"
        ].agg(
            ["count", "mean", "min", "max"]
        ).to_string()
    )


if __name__ == "__main__":
    main()