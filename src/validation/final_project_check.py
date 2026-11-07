
from pathlib import Path
import json
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    "data/raw/plants.csv",
    "data/raw/production_lines.csv",
    "data/raw/machines.csv",
    "data/raw/sensors.csv",
    "data/raw/technicians.csv",
    "data/raw/parts.csv",
    "data/raw/telemetry_events.csv",
    "data/raw/failure_events.csv",
    "data/raw/maintenance_work_orders.csv",
    "data/processed/feature_dataset.csv",
    "data/processed/predictions.csv",
    "data/processed/models/best_model.joblib",
    "data/processed/models/model_metadata.json",
    "docs/data_dictionary.md",
    "src/database/schema.sql",
    "dashboard/app.py",
    "README.md",
]

def check_files():
    print("\n1. FILE AVAILABILITY CHECK")

    missing = []

    for file in REQUIRED_FILES:
        path = BASE_DIR / file

        if path.exists():
            print(f"[PASS] {file}")
        else:
            print(f"[FAIL] {file}")
            missing.append(file)

    return missing


def check_csv_records():
    print("\n2. DATASET RECORD COUNTS")

    datasets = {
        "plants.csv": "data/raw/plants.csv",
        "production_lines.csv": "data/raw/production_lines.csv",
        "machines.csv": "data/raw/machines.csv",
        "sensors.csv": "data/raw/sensors.csv",
        "telemetry_events.csv": "data/raw/telemetry_events.csv",
        "failure_events.csv": "data/raw/failure_events.csv",
        "maintenance_work_orders.csv": "data/raw/maintenance_work_orders.csv",
        "feature_dataset.csv": "data/processed/feature_dataset.csv",
        "predictions.csv": "data/processed/predictions.csv",
    }

    for name, relative_path in datasets.items():
        path = BASE_DIR / relative_path

        if not path.exists():
            print(f"[SKIP] {name} - file missing")
            continue

        try:
            df = pd.read_csv(
                path,
                usecols=lambda col: True,
                low_memory=False
            )
            print(f"[PASS] {name}: {len(df):,} records")

        except Exception as error:
            print(f"[FAIL] {name}: {error}")

def check_predictions():
    print("\n3. PREDICTION CHECK")

    path = BASE_DIR / "data/processed/predictions.csv"

    if not path.exists():
        print("[FAIL] Predictions file missing")
        return

    df = pd.read_csv(path)

    print("Total predictions:", len(df))

    if "machine_id" in df.columns:
        print("Unique machines:", df["machine_id"].nunique())

    probability_column = next(
        (
            col for col in [
                "failure_probability",
                "probability",
                "failure_probability_percent"
            ]
            if col in df.columns
        ),
        None
    )

    if probability_column:
        probabilities = pd.to_numeric(
            df[probability_column], errors="coerce"
        )

        print("Probability range:",
              probabilities.min(), "to", probabilities.max())

        if probabilities.isna().any():
            print("[FAIL] Invalid probabilities detected")
        elif (
            probabilities.min() < 0
            or probabilities.max() > 100
        ):
            print("[FAIL] Probability values outside expected range")
        else:
            print("[PASS] Probability values are valid")

    else:
        print("[WARNING] Probability column not identified")


def check_model_metadata():
    print("\n4. MODEL METADATA CHECK")

    path = BASE_DIR / "data/processed/models/model_metadata.json"

    if not path.exists():
        print("[FAIL] Model metadata missing")
        return

    with open(path, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    print("Selected model:", metadata.get("best_model"))
    print("Target:", metadata.get("target"))
    print("Training rows:", metadata.get("training_rows"))
    print("Testing rows:", metadata.get("testing_rows"))
    print("Features:", len(metadata.get("feature_columns", [])))

    print("[PASS] Model metadata loaded successfully")


def main():
    print("=" * 60)
    print("PREDICTIVE MAINTENANCE - FINAL PROJECT CHECK")
    print("=" * 60)

    missing_files = check_files()

    check_csv_records()
    check_predictions()
    check_model_metadata()

    print("\n5. FINAL STATUS")

    if missing_files:
        print("Missing files:", len(missing_files))
        print("Please resolve missing files before submission.")
    else:
        print("[PASS] All required files are present.")

    print("\nValidation script completed.")


if __name__ == "__main__":
    main()
