
from pathlib import Path
import pandas as pd
import sqlite3

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data/raw"


def test_machine_production_line_relationship():
    machines = pd.read_csv(DATA_DIR / "machines.csv")
    lines = pd.read_csv(DATA_DIR / "production_lines.csv")

    assert set(machines["line_id"]).issubset(set(lines["line_id"]))


def test_sensor_machine_relationship():
    sensors = pd.read_csv(DATA_DIR / "sensors.csv")
    machines = pd.read_csv(DATA_DIR / "machines.csv")

    assert set(sensors["machine_id"]).issubset(
        set(machines["machine_id"])
    )


def test_failure_machine_relationship():
    failures = pd.read_csv(DATA_DIR / "failure_events.csv")
    machines = pd.read_csv(DATA_DIR / "machines.csv")

    assert set(failures["machine_id"]).issubset(
        set(machines["machine_id"])
    )


def test_telemetry_sensor_relationship():
    telemetry = pd.read_csv(
        DATA_DIR / "telemetry_events.csv",
        usecols=["sensor_id", "machine_id"]
    )
    sensors = pd.read_csv(DATA_DIR / "sensors.csv")

    sensor_machine = sensors.set_index("sensor_id")["machine_id"]

    assert telemetry["sensor_id"].isin(sensor_machine.index).all()

    expected_machines = telemetry["sensor_id"].map(sensor_machine)

    assert (expected_machines == telemetry["machine_id"]).all()


def test_database_foreign_keys():
    db_path = DATA_DIR / "predictive_maintenance.db"

    connection = sqlite3.connect(db_path)

    try:
        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        assert violations == []
    finally:
        connection.close()
