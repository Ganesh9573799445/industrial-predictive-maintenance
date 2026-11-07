
from pathlib import Path

import joblib
import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = BASE_DIR / "data" / "processed" / "feature_dataset.csv"
MODEL_FILE = BASE_DIR / "data" / "processed" / "models" / "best_model.joblib"
METADATA_FILE = BASE_DIR / "data" / "processed" / "models" / "model_metadata.json"

OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "predictions.csv"

PREDICTION_THRESHOLD = 0.50


# --------------------------------------------------
# STEP 1: LOAD MODEL AND DATA
# --------------------------------------------------

def load_resources():

    for path in [DATA_FILE, MODEL_FILE, METADATA_FILE]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    import json

    with open(METADATA_FILE, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    model = joblib.load(MODEL_FILE)

    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if df.empty:
        raise ValueError("Feature dataset is empty.")

    if df["date"].isna().any():
        raise ValueError("Invalid dates found in feature dataset.")

    feature_columns = metadata["feature_columns"]

    missing_columns = [
        column for column in feature_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing model input columns: {missing_columns}"
        )

    return df, model, metadata, feature_columns


# --------------------------------------------------
# STEP 2: GET LATEST RECORD PER MACHINE
# --------------------------------------------------

def get_latest_machine_records(df):

    latest = (
        df.sort_values(["machine_id", "date"])
        .groupby("machine_id", as_index=False)
        .tail(1)
        .copy()
    )

    if latest["machine_id"].duplicated().any():
        raise ValueError("Duplicate machine records found.")

    print("Latest machine records:", len(latest))

    return latest


# --------------------------------------------------
# STEP 3: PREDICT FAILURE PROBABILITY
# --------------------------------------------------


def predict_failure(latest, model, feature_columns):

    X = latest[feature_columns].copy()

    probabilities = model.predict_proba(X)[:, 1]

    latest["failure_probability"] = probabilities

    latest["failure_probability_percent"] = (
        probabilities * 100
    ).round(4)

    print("\nRaw probability distribution:")
    print(latest["failure_probability"].describe())

    print("\nHighest raw probabilities:")
    print(
        latest[
            ["machine_id", "failure_probability"]
        ]
        .sort_values(
            "failure_probability",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )

    latest["predicted_failure"] = (
        probabilities >= PREDICTION_THRESHOLD
    ).astype(int)

    return latest



# --------------------------------------------------
# STEP 4: ASSIGN RISK CATEGORY
# --------------------------------------------------

def assign_risk_category(df):

    def get_category(probability):

        if probability >= 0.60:
            return "High"

        elif probability >= 0.30:
            return "Medium"

        return "Low"

    df["risk_category"] = (
        df["failure_probability"].apply(get_category)
    )

    return df


# --------------------------------------------------
# STEP 5: SAVE PREDICTIONS
# --------------------------------------------------

def save_predictions(df, metadata):

    output_columns = [
        "machine_id",
        "date",
        "failure_probability_percent",
        "predicted_failure",
        "risk_category"
    ]

    predictions = df[output_columns].copy()

    predictions = predictions.sort_values(
        "failure_probability_percent",
        ascending=False
    )

    predictions.to_csv(OUTPUT_FILE, index=False)

    print("\nPrediction summary")
    print("-" * 45)

    print("Total machines:", len(predictions))

    print(
        "High risk:",
        (predictions["risk_category"] == "High").sum()
    )

    print(
        "Medium risk:",
        (predictions["risk_category"] == "Medium").sum()
    )

    print(
        "Low risk:",
        (predictions["risk_category"] == "Low").sum()
    )

    print(
        "Predicted failures:",
        predictions["predicted_failure"].sum()
    )

    print("\nTop 10 machines by failure probability:")

    print(
        predictions.head(10).to_string(index=False)
    )

    print("\nModel used:", metadata["best_model"])
    print("Prediction horizon: Next 7 days")
    print("Classification threshold:", PREDICTION_THRESHOLD)
    print("Output file:", OUTPUT_FILE)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("=" * 55)
    print("PREDICTIVE MAINTENANCE - FAILURE RISK PREDICTION")
    print("=" * 55)

    df, model, metadata, feature_columns = load_resources()

    latest = get_latest_machine_records(df)

    predictions = predict_failure(
        latest,
        model,
        feature_columns
    )

    predictions = assign_risk_category(predictions)

    save_predictions(predictions, metadata)

    print("\nStep 17 completed successfully.")


if __name__ == "__main__":
    main()
