"""Prepare captured MQTT traffic for model inference."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from preprocess_mqttset import HEX_FEATURES, parse_hex


DEFAULT_METADATA = Path(
    "data/processed/preprocessing_metadata.json"
)


def extract_features(raw_df, metadata_path=DEFAULT_METADATA):

    # Load original preprocessing metadata
    metadata = json.loads(
        Path(metadata_path).read_text()
    )

    features = metadata["features"]
    medians = metadata["training_medians"]

    df = raw_df.copy()
    df.columns = df.columns.str.strip()

    # Verify that all required features exist
    missing = [
        c for c in features
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required features: {missing}"
        )

    # Select features in the original training order
    X = df[features].copy()

    # Apply original hexadecimal conversion
    for c in HEX_FEATURES:
        if c in X.columns:
            X[c] = X[c].map(parse_hex)

    # Convert features to numerical values
    for c in X.columns:
        X[c] = pd.to_numeric(
            X[c],
            errors="coerce"
        )

    # Replace infinite values
    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Apply original training medians
    X = X.fillna(medians).fillna(0)

    return X


if __name__ == "__main__":

    raw_df = pd.read_csv(
        "data/live/captured_traffic.csv",
        low_memory=False
    )

    X = extract_features(raw_df)

    output = Path(
        "data/live/processed_traffic.csv"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    X.to_csv(output, index=False)

    print("Feature extraction completed.")
    print("Packets processed:", len(X))
    print("Number of features:", len(X.columns))
    print("Missing values:", X.isna().sum().sum())
    print("Saved to:", output)

    print("\nProcessed traffic:")
    print(X.head().to_string(index=False))