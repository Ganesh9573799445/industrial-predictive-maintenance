
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
GROUND_TRUTH_DIR = BASE_DIR / "data" / "ground_truth"
RAW_DIR = BASE_DIR / "data" / "raw"


def load_exception(filename):
    path = GROUND_TRUTH_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing exception file: {filename}")

    return pd.read_csv(path)


def validate_unknown_sensor():
    df = load_exception("exception_unknown_sensor.csv")

    assert len(df) == 1
    assert df.iloc[0]["sensor_id"] == "SNS-UNKNOWN-999"
    assert df.iloc[0]["issue_type"] == "UNKNOWN_SENSOR"
    assert df.iloc[0]["ground_truth"] == 1

    print("PASS: Unknown sensor exception detected.")


def validate_invalid_sensor_data():
    df = load_exception("exception_invalid_sensor_data.csv")

    assert len(df) == 2

    invalid_unit = df[df["issue_type"] == "INVALID_SENSOR_UNIT"]
    invalid_range = df[df["issue_type"] == "OUT_OF_RANGE_READING"]

    assert len(invalid_unit) == 1
    assert invalid_unit.iloc[0]["unit"] == "INVALID_UNIT"

    assert len(invalid_range) == 1
    assert float(invalid_range.iloc[0]["reading_value"]) == 999999

    assert (df["ground_truth"] == 1).all()

    print("PASS: Invalid unit and out-of-range exceptions detected.")


def validate_failure_timeline():
    df = load_exception("exception_failure_timeline.csv")

    assert len(df) == 1

    failure_time = pd.to_datetime(df.iloc[0]["failure_time"])
    symptom_time = pd.to_datetime(df.iloc[0]["symptom_time"])

    assert symptom_time > failure_time
    assert df.iloc[0]["issue_type"] == "SYMPTOM_AFTER_FAILURE"
    assert df.iloc[0]["ground_truth"] == 1

    print("PASS: Failure/symptom timeline exception detected.")


def validate_maintenance_timeline():
    df = load_exception("exception_maintenance_timeline.csv")

    assert len(df) == 1

    start_time = pd.to_datetime(df.iloc[0]["start_time"])
    end_time = pd.to_datetime(df.iloc[0]["end_time"])

    assert end_time < start_time
    assert (
        df.iloc[0]["issue_type"]
        == "MAINTENANCE_END_BEFORE_START"
    )
    assert df.iloc[0]["ground_truth"] == 1

    print("PASS: Invalid maintenance timeline detected.")


def validate_missing_gap_zero():
    df = load_exception("exception_missing_gap_zero.csv")

    assert len(df) == 1
    assert float(df.iloc[0]["reading_value"]) == 0
    assert (
        df.iloc[0]["issue_type"]
        == "MISSING_GAP_FILLED_WITH_ZERO"
    )
    assert df.iloc[0]["ground_truth"] == 1

    # Verify that the synthetic timestamp is between
    # the first two source readings for the same sensor.
    telemetry_path = RAW_DIR / "telemetry_events.csv"

    sensor_id = df.iloc[0]["sensor_id"]

    source = pd.read_csv(
        telemetry_path,
        usecols=["sensor_id", "timestamp"],
        nrows=1000
    )

    source = source[source["sensor_id"] == sensor_id].copy()
    source["timestamp"] = pd.to_datetime(source["timestamp"])
    source = source.sort_values("timestamp")

    assert len(source) >= 2

    synthetic_time = pd.to_datetime(df.iloc[0]["timestamp"])

    first_time = source.iloc[0]["timestamp"]
    second_time = source.iloc[1]["timestamp"]

    assert first_time < synthetic_time < second_time

    print("PASS: Zero-filled missing-gap exception detected.")


def main():

    print("=" * 55)
    print("EXCEPTION DATA VALIDATION")
    print("=" * 55)

    validate_unknown_sensor()
    validate_invalid_sensor_data()
    validate_failure_timeline()
    validate_maintenance_timeline()
    validate_missing_gap_zero()

    print("\n" + "=" * 55)
    print("ALL 5 EXCEPTION SCENARIOS PASSED")
    print("Total exception records validated: 6")
    print("=" * 55)


if __name__ == "__main__":
    main()
