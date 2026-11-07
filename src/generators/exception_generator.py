
import random
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
rng = random.Random(SEED)

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"

GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)


def save_exceptions(filename, records):
    output_path = GROUND_TRUTH_DIR / filename
    pd.DataFrame(records).to_csv(output_path, index=False)
    print(f"Created: {filename} ({len(records)} records)")


def main():

    print("Loading baseline records...")

    telemetry_path = RAW_DIR / "telemetry_events.csv"
    failure_path = RAW_DIR / "failure_events.csv"
    maintenance_path = RAW_DIR / "maintenance_work_orders.csv"

    for path in [telemetry_path, failure_path, maintenance_path]:
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    # Read only a few telemetry records.
    telemetry_sample = pd.read_csv(
        telemetry_path,
        nrows=10,
        low_memory=False
    )

    failures = pd.read_csv(failure_path)
    maintenance = pd.read_csv(maintenance_path)

    # Check required columns.
    required_telemetry = {
        "telemetry_id", "sensor_id", "machine_id",
        "timestamp", "reading_value", "unit"
    }

    required_failure = {
        "failure_id", "machine_id", "failure_time", "recorded_at"
    }

    required_maintenance = {
        "work_order_id", "machine_id", "start_time", "end_time"
    }

    for column in required_telemetry:
        if column not in telemetry_sample.columns:
            raise ValueError(f"Missing telemetry column: {column}")

    for column in required_failure:
        if column not in failures.columns:
            raise ValueError(f"Missing failure column: {column}")

    for column in required_maintenance:
        if column not in maintenance.columns:
            raise ValueError(f"Missing maintenance column: {column}")

    if telemetry_sample.empty or failures.empty or maintenance.empty:
        raise ValueError("One or more baseline datasets are empty.")

    # --------------------------------------------------
    # 1. UNKNOWN SENSOR
    # --------------------------------------------------

    source = telemetry_sample.iloc[0].to_dict()

    unknown_sensor = source.copy()
    unknown_sensor["telemetry_id"] = "EXC-TEL-UNKNOWN-001"
    unknown_sensor["sensor_id"] = "SNS-UNKNOWN-999"
    unknown_sensor["issue_type"] = "UNKNOWN_SENSOR"
    unknown_sensor["ground_truth"] = 1

    save_exceptions(
        "exception_unknown_sensor.csv",
        [unknown_sensor]
    )

    # --------------------------------------------------
    # 2. INVALID UNIT AND OUT-OF-RANGE READING
    # --------------------------------------------------

    source = telemetry_sample.iloc[1].to_dict()

    invalid_unit = source.copy()
    invalid_unit["telemetry_id"] = "EXC-TEL-UNIT-001"
    invalid_unit["unit"] = "INVALID_UNIT"
    invalid_unit["issue_type"] = "INVALID_SENSOR_UNIT"
    invalid_unit["ground_truth"] = 1

    invalid_range = source.copy()
    invalid_range["telemetry_id"] = "EXC-TEL-RANGE-001"
    invalid_range["reading_value"] = 999999
    invalid_range["issue_type"] = "OUT_OF_RANGE_READING"
    invalid_range["ground_truth"] = 1

    save_exceptions(
        "exception_invalid_sensor_data.csv",
        [invalid_unit, invalid_range]
    )

    # --------------------------------------------------
    # 3. FAILURE BEFORE REPORTED SYMPTOM
    # --------------------------------------------------

    source = failures.iloc[0]

    failure_time = pd.to_datetime(source["failure_time"])
    symptom_time = failure_time + pd.Timedelta(hours=2)

    failure_exception = {
        "exception_id": "EXC-FAIL-001",
        "failure_id": source["failure_id"],
        "machine_id": source["machine_id"],
        "failure_time": failure_time,
        "symptom_time": symptom_time,
        "issue_type": "SYMPTOM_AFTER_FAILURE",
        "ground_truth": 1,
        "description": (
            "Reported symptom occurs after the failure timestamp."
        )
    }

    save_exceptions(
        "exception_failure_timeline.csv",
        [failure_exception]
    )

    # --------------------------------------------------
    # 4. MAINTENANCE END BEFORE START
    # --------------------------------------------------

    source = maintenance.iloc[0]

    start_time = pd.to_datetime(source["start_time"])
    invalid_end_time = start_time - pd.Timedelta(hours=1)

    maintenance_exception = {
        "exception_id": "EXC-WO-001",
        "work_order_id": source["work_order_id"],
        "machine_id": source["machine_id"],
        "start_time": start_time,
        "end_time": invalid_end_time,
        "issue_type": "MAINTENANCE_END_BEFORE_START",
        "ground_truth": 1,
        "description": (
            "Maintenance end timestamp is earlier than start timestamp."
        )
    }

    save_exceptions(
        "exception_maintenance_timeline.csv",
        [maintenance_exception]
    )

    # --------------------------------------------------
    # 5. MISSING SENSOR GAP HIDDEN AS ZERO
    # --------------------------------------------------

    # Read only the first 1000 records to locate
    # two consecutive readings for the same sensor.
    telemetry_chunk = pd.read_csv(
        telemetry_path,
        nrows=1000,
        low_memory=False
    )

    sensor_id = telemetry_chunk.iloc[0]["sensor_id"]

    sensor_rows = telemetry_chunk[
        telemetry_chunk["sensor_id"] == sensor_id
    ].copy()

    sensor_rows["timestamp"] = pd.to_datetime(
        sensor_rows["timestamp"]
    )

    sensor_rows = sensor_rows.sort_values("timestamp")

    if len(sensor_rows) < 2:
        raise ValueError(
            "Could not find two readings for the selected sensor."
        )

    first = sensor_rows.iloc[0]
    second = sensor_rows.iloc[1]

    first_time = first["timestamp"]
    second_time = second["timestamp"]

    if second_time <= first_time:
        raise ValueError("Sensor timestamps are not increasing.")

    # Synthetic zero reading inside the interval.
    hidden_gap_time = first_time + (second_time - first_time) / 2

    gap_exception = first.to_dict()
    gap_exception["telemetry_id"] = "EXC-TEL-GAP-001"
    gap_exception["timestamp"] = hidden_gap_time
    gap_exception["reading_value"] = 0
    gap_exception["issue_type"] = "MISSING_GAP_FILLED_WITH_ZERO"
    gap_exception["ground_truth"] = 1
    gap_exception["description"] = (
        "A missing sensor interval is incorrectly represented as zero."
    )

    save_exceptions(
        "exception_missing_gap_zero.csv",
        [gap_exception]
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print("\nException generation completed.")
    print("Random seed:", SEED)
    print("Exception scenarios: 5")
    print("Exception records: 6")
    print("Baseline database was not modified.")
    print("Output folder:", GROUND_TRUTH_DIR)


if __name__ == "__main__":
    main()
