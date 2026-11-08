
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]


def test_machine_ids_are_unique():
    df = pd.read_csv(BASE_DIR / "data/raw/machines.csv")
    assert df["machine_id"].is_unique
    assert df["machine_id"].notna().all()


def test_sensor_ids_are_unique():
    df = pd.read_csv(BASE_DIR / "data/raw/sensors.csv")
    assert df["sensor_id"].is_unique
    assert df["sensor_id"].notna().all()


def test_telemetry_ids_are_unique():
    df = pd.read_csv(
        BASE_DIR / "data/raw/telemetry_events.csv",
        usecols=["telemetry_id"]
    )
    assert df["telemetry_id"].is_unique
    assert df["telemetry_id"].notna().all()


def test_failure_ids_are_unique():
    df = pd.read_csv(BASE_DIR / "data/raw/failure_events.csv")
    assert df["failure_id"].is_unique
