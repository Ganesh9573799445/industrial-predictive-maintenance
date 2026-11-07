
import json
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
CHUNK_SIZE = 200_000
ROLLING_DAYS = 7
PREDICTION_HORIZON_DAYS = 7

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

TELEMETRY_FILE = RAW_DIR / "telemetry_events.csv"
FAILURE_FILE = RAW_DIR / "failure_events.csv"

OUTPUT_FILE = PROCESSED_DIR / "feature_dataset.csv"

UNIT_MAPPING = {
    "C": "temperature",
    "mm/s": "vibration",
    "bar": "pressure",
    "A": "current",
    "RPM": "speed"
}


# --------------------------------------------------
# STEP 1: AGGREGATE TELEMETRY IN CHUNKS
# --------------------------------------------------

def aggregate_telemetry():

    if not TELEMETRY_FILE.exists():
        raise FileNotFoundError(TELEMETRY_FILE)

    partial_results = []

    print("Reading telemetry in chunks...")

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            TELEMETRY_FILE,
            chunksize=CHUNK_SIZE,
            usecols=[
                "machine_id",
                "timestamp",
                "reading_value",
                "unit"
            ]
        ),
        start=1
    ):

        chunk["timestamp"] = pd.to_datetime(
            chunk["timestamp"],
            errors="coerce"
        )

        chunk["reading_value"] = pd.to_numeric(
            chunk["reading_value"],
            errors="coerce"
        )

        chunk = chunk.dropna(
            subset=[
                "machine_id",
                "timestamp",
                "reading_value",
                "unit"
            ]
        )

        chunk["date"] = chunk["timestamp"].dt.normalize()

        chunk["sum_squared"] = (
            chunk["reading_value"] ** 2
        )

        grouped = chunk.groupby(
            ["machine_id", "date", "unit"],
            as_index=False
        ).agg(
            reading_count=("reading_value", "count"),
            reading_sum=("reading_value", "sum"),
            sum_squared=("sum_squared", "sum"),
            reading_min=("reading_value", "min"),
            reading_max=("reading_value", "max"),
            reading_last=("reading_value", "last")
        )

        partial_results.append(grouped)

        if chunk_number % 2 == 0:
            print(f"Processed chunks: {chunk_number}")

    if not partial_results:
        raise ValueError("No valid telemetry readings found.")

    print("Combining daily aggregates...")

    combined = pd.concat(
        partial_results,
        ignore_index=True
    )

    daily = combined.groupby(
        ["machine_id", "date", "unit"],
        as_index=False
    ).agg(
        reading_count=("reading_count", "sum"),
        reading_sum=("reading_sum", "sum"),
        sum_squared=("sum_squared", "sum"),
        reading_min=("reading_min", "min"),
        reading_max=("reading_max", "max"),
        reading_last=("reading_last", "last")
    )

    daily["mean"] = (
        daily["reading_sum"] / daily["reading_count"]
    )

    variance = (
        daily["sum_squared"] / daily["reading_count"]
        - daily["mean"] ** 2
    )

    daily["std"] = np.sqrt(
        variance.clip(lower=0)
    )

    daily["feature_name"] = daily["unit"].map(
        UNIT_MAPPING
    )

    if daily["feature_name"].isna().any():
        unknown_units = daily.loc[
            daily["feature_name"].isna(), "unit"
        ].unique()

        raise ValueError(
            f"Unknown sensor units found: {unknown_units}"
        )

    print("Daily telemetry aggregation completed.")

    return daily


# --------------------------------------------------
# STEP 2: CREATE MACHINE-LEVEL FEATURE TABLE
# --------------------------------------------------

def create_machine_features(daily):

    print("Creating machine-level features...")

    feature_tables = []

    metrics = [
        "mean",
        "std",
        "reading_min",
        "reading_max",
        "reading_last",
        "reading_count"
    ]

    for metric in metrics:

        pivot = daily.pivot_table(
            index=["machine_id", "date"],
            columns="feature_name",
            values=metric,
            aggfunc="first"
        )

        pivot.columns = [
            f"{column}_{metric}"
            for column in pivot.columns
        ]

        feature_tables.append(pivot)

    features = pd.concat(
        feature_tables,
        axis=1
    ).reset_index()

    features = features.sort_values(
        ["machine_id", "date"]
    ).reset_index(drop=True)

    # --------------------------------------------------
    # STEP 3: ADD SEVEN-DAY ROLLING FEATURES
    # --------------------------------------------------

    print("Calculating rolling trends...")

    sensor_types = [
        "temperature",
        "vibration",
        "pressure",
        "current",
        "speed"
    ]

    for sensor_type in sensor_types:

        mean_column = f"{sensor_type}_mean"

        if mean_column not in features.columns:
            continue

        features[f"{sensor_type}_mean_7d_avg"] = (
            features.groupby("machine_id")[mean_column]
            .transform(
                lambda values: values.rolling(
                    window=ROLLING_DAYS,
                    min_periods=3
                ).mean()
            )
        )

        features[f"{sensor_type}_mean_7d_std"] = (
            features.groupby("machine_id")[mean_column]
            .transform(
                lambda values: values.rolling(
                    window=ROLLING_DAYS,
                    min_periods=3
                ).std()
            )
        )

    return features


# --------------------------------------------------
# STEP 4: CREATE FAILURE TARGET LABEL
# --------------------------------------------------

def add_failure_labels(features):

    print("Creating seven-day failure labels...")

    failures = pd.read_csv(FAILURE_FILE)

    required_columns = {
        "machine_id",
        "failure_time"
    }

    missing = required_columns - set(failures.columns)

    if missing:
        raise ValueError(
            f"Missing failure columns: {missing}"
        )

    failures["failure_time"] = pd.to_datetime(
        failures["failure_time"],
        errors="coerce"
    )

    failures = failures.dropna(
        subset=["machine_id", "failure_time"]
    )

    failure_map = {
        machine_id: group["failure_time"].to_numpy(
            dtype="datetime64[ns]"
        )
        for machine_id, group in failures.groupby("machine_id")
    }

    labels = np.zeros(len(features), dtype=np.int8)

    for machine_id, indexes in features.groupby(
        "machine_id"
    ).groups.items():

        machine_failures = failure_map.get(machine_id)

        if machine_failures is None:
            continue

        observation_end = (
            features.loc[indexes, "date"].to_numpy(
                dtype="datetime64[ns]"
            )
            + np.timedelta64(1, "D")
            - np.timedelta64(1, "ns")
        )

        horizon_end = (
            observation_end
            + np.timedelta64(
                PREDICTION_HORIZON_DAYS,
                "D"
            )
        )

        future_failure = (
            (machine_failures[None, :] > observation_end[:, None])
            & (machine_failures[None, :] <= horizon_end[:, None])
        )

        labels[np.asarray(list(indexes))] = (
            future_failure.any(axis=1).astype(np.int8)
        )

    features["target_failure_next_7d"] = labels

    return features


# --------------------------------------------------
# STEP 5: VALIDATE AND SAVE
# --------------------------------------------------

def save_features(features):

    print("Validating feature dataset...")

    if features.empty:
        raise ValueError("Feature dataset is empty.")

    if features.duplicated(
        subset=["machine_id", "date"]
    ).any():
        raise ValueError(
            "Duplicate machine-date feature records found."
        )

    if not features["target_failure_next_7d"].isin(
        [0, 1]
    ).all():
        raise ValueError("Invalid target labels found.")

    if features["machine_id"].isna().any():
        raise ValueError("Missing machine IDs found.")

    if features["date"].isna().any():
        raise ValueError("Missing observation dates found.")

    features.to_csv(
        OUTPUT_FILE,
        index=False
    )

    positive = int(
        features["target_failure_next_7d"].sum()
    )

    negative = len(features) - positive

    manifest = {
        "seed": SEED,
        "input_telemetry": "data/raw/telemetry_events.csv",
        "input_failures": "data/raw/failure_events.csv",
        "output": "data/processed/feature_dataset.csv",
        "aggregation_level": "machine_daily",
        "rolling_window_days": ROLLING_DAYS,
        "prediction_horizon_days": PREDICTION_HORIZON_DAYS,
        "total_feature_rows": len(features),
        "unique_machines": int(
            features["machine_id"].nunique()
        ),
        "positive_labels": positive,
        "negative_labels": negative,
        "target": "target_failure_next_7d",
        "excluded_from_features": [
            "failure_id",
            "failure_time",
            "recorded_at",
            "ground_truth",
            "issue_type",
            "quality_status"
        ]
    }

    manifest_path = (
        PROCESSED_DIR / "feature_manifest.json"
    )

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    print("\nFeature engineering completed.")
    print("Output:", OUTPUT_FILE)
    print("Total rows:", len(features))
    print("Unique machines:", features["machine_id"].nunique())
    print("Positive labels:", positive)
    print("Negative labels:", negative)
    print("Feature columns:", len(features.columns))


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 55)
    print("PREDICTIVE MAINTENANCE - FEATURE ENGINEERING")
    print("=" * 55)

    daily = aggregate_telemetry()

    features = create_machine_features(daily)

    features = add_failure_labels(features)

    save_features(features)

    print("\nStep 15 completed successfully.")


if __name__ == "__main__":
    main()
