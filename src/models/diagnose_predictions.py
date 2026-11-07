
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = BASE_DIR / "data" / "processed" / "feature_dataset.csv"
MODEL_FILE = BASE_DIR / "data" / "processed" / "models" / "best_model.joblib"
METADATA_FILE = BASE_DIR / "data" / "processed" / "models" / "model_metadata.json"


def main():

    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"])

    with open(METADATA_FILE, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    model = joblib.load(MODEL_FILE)

    feature_columns = metadata["feature_columns"]

    # Recreate the chronological training cutoff.
    unique_dates = np.sort(df["date"].unique())

    split_index = int(len(unique_dates) * 0.80)

    test_start = pd.Timestamp(unique_dates[split_index])

    training_cutoff = test_start - pd.Timedelta(days=7)

    train_df = df[df["date"] < training_cutoff].copy()

    latest = (
        df.sort_values(["machine_id", "date"])
        .groupby("machine_id")
        .tail(1)
        .copy()
    )

    X_train = train_df[feature_columns]
    X_latest = latest[feature_columns]

    # Compare latest feature values with training ranges.
    print("\nTRAINING DATA SUMMARY")
    print("Training rows:", len(X_train))
    print("Training positive labels:", int(train_df[
        "target_failure_next_7d"
    ].sum()))

    print("\nLATEST DATA SUMMARY")
    print("Latest rows:", len(X_latest))
    print("Latest date:", latest["date"].max())
    print("Missing latest feature values:", X_latest.isna().sum().sum())

    train_min = X_train.min()
    train_max = X_train.max()

    outside_range = (
        (X_latest < train_min) |
        (X_latest > train_max)
    )

    print(
        "\nLatest feature values outside training ranges:",
        int(outside_range.sum().sum())
    )

    print("\nFEATURE RANGE COMPARISON")

    for column in feature_columns:
        print(
            f"{column}: "
            f"Train[{train_min[column]:.4f}, {train_max[column]:.4f}] "
            f"Latest[{X_latest[column].min():.4f}, "
            f"{X_latest[column].max():.4f}]"
        )

    # Inspect the model output.
    probabilities = model.predict_proba(X_latest)

    print("\nMODEL INFORMATION")
    print("Model classes:", model.classes_)
    print("Probability matrix shape:", probabilities.shape)

    print("\nPROBABILITY DISTRIBUTION")
    print(pd.Series(probabilities[:, 1]).describe())

    print("\nTOP 10 MACHINE PROBABILITIES")

    result = pd.DataFrame({
        "machine_id": latest["machine_id"].values,
        "probability": probabilities[:, 1]
    })

    print(
        result.sort_values(
            "probability",
            ascending=False
        ).head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
