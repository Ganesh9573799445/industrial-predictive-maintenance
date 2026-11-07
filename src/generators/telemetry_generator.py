
import sqlite3
import random
from pathlib import Path

import numpy as np
import pandas as pd


# ==========================================
# 1. CONFIGURATION
# ==========================================

SEED = 20261022

DAYS = 90
INTERVAL_MINUTES = 30

READINGS_PER_SENSOR = DAYS * 24 * 60 // INTERVAL_MINUTES

TOTAL_FAILURES = 100
MACHINES_WITH_FAILURES = 80
SENSOR_FAULT_COUNT = 10

BATCH_SIZE = 4320

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data/raw/predictive_maintenance.db"
OUTPUT_DIR = BASE_DIR / "data/raw"
GROUND_TRUTH_DIR = BASE_DIR / "data/ground_truth"

START_DATE = "2026-01-01 00:00:00"

rng = np.random.default_rng(SEED)
schedule_rng = random.Random(SEED + 1)


# ==========================================
# 2. SENSOR BASELINES
# ==========================================

SENSOR_BASELINES = {
    "Temperature": {
        "running": (70, 5),
        "idle": (35, 3),
        "shutdown": (25, 2),
        "drift": 30
    },
    "Vibration": {
        "running": (5, 1),
        "idle": (1, 0.3),
        "shutdown": (0.1, 0.05),
        "drift": 12
    },
    "Pressure": {
        "running": (10, 1),
        "idle": (3, 0.5),
        "shutdown": (0.5, 0.1),
        "drift": 4
    },
    "Current": {
        "running": (40, 5),
        "idle": (5, 1),
        "shutdown": (0.2, 0.1),
        "drift": 20
    },
    "Speed": {
        "running": (1500, 100),
        "idle": (100, 20),
        "shutdown": (0, 0),
        "drift": -400
    }
}


# ==========================================
# 3. LOAD MASTER DATA
# ==========================================

def load_master_data(connection):

    machines = pd.read_sql_query(
        "SELECT machine_id FROM Machine ORDER BY machine_id",
        connection
    )

    sensors = pd.read_sql_query(
        "SELECT * FROM Sensor ORDER BY sensor_id",
        connection
    )

    if len(machines) != 100:
        raise ValueError("Expected 100 machines")

    if len(sensors) != 500:
        raise ValueError("Expected 500 sensors")

    return machines, sensors


# ==========================================
# 4. GENERATE FAILURE SCHEDULE
# ==========================================

def generate_failure_schedule(machines):

    selected = schedule_rng.sample(
        machines["machine_id"].tolist(),
        MACHINES_WITH_FAILURES
    )

    failures = []

    event_counter = 0

    for machine_index, machine_id in enumerate(selected):

        first_day = schedule_rng.randint(25, 65)

        event_counter += 1

        first_time = (
            pd.Timestamp(START_DATE)
            + pd.Timedelta(days=first_day)
            + pd.Timedelta(hours=schedule_rng.randint(6, 20))
        )

        failures.append({
            "failure_id": f"FAIL-2026-{event_counter:06d}",
            "machine_id": machine_id,
            "failure_time": first_time,
            "failure_type": schedule_rng.choice([
                "Bearing_Wear",
                "Motor_Overheating",
                "Excessive_Vibration",
                "Pressure_Failure",
                "Electrical_Failure"
            ]),
            "severity": schedule_rng.choice([
                "Medium", "High", "Critical"
            ]),
            "root_cause": "Synthetic degradation scenario"
        })

        # Twenty machines receive a second failure
        if machine_index < TOTAL_FAILURES - MACHINES_WITH_FAILURES:

            second_day = min(
                first_day + schedule_rng.randint(15, 25),
                84
            )

            event_counter += 1

            second_time = (
                pd.Timestamp(START_DATE)
                + pd.Timedelta(days=second_day)
                + pd.Timedelta(hours=schedule_rng.randint(6, 20))
            )

            failures.append({
                "failure_id": f"FAIL-2026-{event_counter:06d}",
                "machine_id": machine_id,
                "failure_time": second_time,
                "failure_type": schedule_rng.choice([
                    "Bearing_Wear",
                    "Motor_Overheating",
                    "Excessive_Vibration",
                    "Pressure_Failure",
                    "Electrical_Failure"
                ]),
                "severity": schedule_rng.choice([
                    "Medium", "High", "Critical"
                ]),
                "root_cause": "Synthetic degradation scenario"
            })

    result = pd.DataFrame(failures)

    result = result.sort_values(
        ["failure_time", "machine_id"]
    ).reset_index(drop=True)

    # Reassign IDs in chronological order
    result["failure_id"] = [
        f"FAIL-2026-{i:06d}"
        for i in range(1, len(result) + 1)
    ]

    result["failure_time"] = result[
        "failure_time"
    ].dt.strftime("%Y-%m-%dT%H:%M:%S")

    if len(result) != TOTAL_FAILURES:
        raise ValueError("Failure schedule count is incorrect")

    return result


# ==========================================
# 5. GENERATE SENSOR FAULT SCHEDULE
# ==========================================

def generate_sensor_fault_schedule(sensors, timestamps):

    selected = schedule_rng.sample(
        sensors["sensor_id"].tolist(),
        SENSOR_FAULT_COUNT
    )

    faults = []

    for sensor_id in selected:

        start_index = schedule_rng.randint(
            300, len(timestamps) - 30
        )

        start_time = timestamps[start_index]

        end_time = start_time + pd.Timedelta(hours=2)

        faults.append({
            "sensor_id": sensor_id,
            "start_time": start_time.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "end_time": end_time.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "issue_type": "STUCK_SENSOR"
        })

    return pd.DataFrame(faults)


# ==========================================
# 6. OPERATING STATE
# ==========================================


def generate_operating_states(timestamps, machine_id):

    hours = timestamps.hour.to_numpy()

    states = np.where(
        (hours >= 6) & (hours < 22),
        "Running",
        "Idle"
    ).astype(object)

    # One planned 8-hour shutdown per machine
    machine_number = int(machine_id.split("-")[-1])

    shutdown_day = (machine_number * 7) % DAYS

    shutdown_start = (
        pd.Timestamp(START_DATE)
        + pd.Timedelta(days=shutdown_day, hours=0)
    )

    shutdown_end = shutdown_start + pd.Timedelta(hours=8)

    shutdown_mask = (
        (timestamps >= shutdown_start)
        & (timestamps < shutdown_end)
    )

    states[shutdown_mask] = "Shutdown"

    return states



# ==========================================
# 7. GENERATE SENSOR READINGS
# ==========================================

def generate_readings(sensor, timestamps, failures, sensor_faults):

    sensor_type = sensor["sensor_type"]

    config = SENSOR_BASELINES[sensor_type]

    # Operating state of parent machine
    states = generate_operating_states(
        timestamps,
        sensor["machine_id"]
    )

    # Normal operating values
    values = np.zeros(len(timestamps), dtype=np.float64)

    for state in ["Running", "Idle", "Shutdown"]:

        mask = states == state

        mean, std = config[state.lower()]

        values[mask] = rng.normal(
            mean,
            std,
            mask.sum()
        )

    # Find nearest future failure for this machine
    machine_failures = failures[
        failures["machine_id"] == sensor["machine_id"]
    ]

    failure_ns = pd.to_datetime(
        machine_failures["failure_time"]
    ).sort_values().astype("int64").to_numpy()

    timestamp_ns = timestamps.asi8

    if len(failure_ns):

        positions = np.searchsorted(
            failure_ns,
            timestamp_ns,
            side="left"
        )

        valid_positions = positions < len(failure_ns)

        days_to_failure = np.full(
            len(timestamps),
            999.0
        )

        days_to_failure[valid_positions] = (
            failure_ns[positions[valid_positions]]
            - timestamp_ns[valid_positions]
        ) / (86400 * 1e9)

        # Drift starts seven days before failure
        drift_fraction = np.clip(
            (7 - days_to_failure) / 7,
            0,
            1
        )

        drift = (
            config["drift"] * drift_fraction
        )

        # Apply deterioration during operating periods
        running_mask = states == "Running"

        values[running_mask] += drift[running_mask]

    # Keep valid readings inside sensor physical ranges
    values = np.clip(
        values,
        sensor["min_range"],
        sensor["max_range"]
    )

    quality = np.full(
        len(timestamps),
        "Valid",
        dtype=object
    )

    issue_types = np.full(
        len(timestamps),
        None,
        dtype=object
    )

    # Inject stuck sensor faults
    fault = sensor_faults[
        sensor_faults["sensor_id"] == sensor["sensor_id"]
    ]

    if not fault.empty:

        fault_start = pd.Timestamp(
            fault.iloc[0]["start_time"]
        )

        fault_end = pd.Timestamp(
            fault.iloc[0]["end_time"]
        )

        fault_mask = (
            (timestamps >= fault_start)
            & (timestamps < fault_end)
        )

        if fault_mask.any():

            first_fault_index = np.where(
                fault_mask
            )[0][0]

            stuck_value = values[first_fault_index]

            values[fault_mask] = stuck_value

            quality[fault_mask] = "Sensor_Fault"

            issue_types[fault_mask] = "STUCK_SENSOR"

    return np.round(values, 3), states, quality, issue_types


# ==========================================
# 8. MAIN TELEMETRY GENERATOR
# ==========================================

def main():

    print("\nStarting telemetry generation...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    try:

        connection.execute("PRAGMA foreign_keys = ON")

        machines, sensors = load_master_data(connection)
        # Synchronize sensor sampling interval

        connection.execute(
            "UPDATE Sensor SET sampling_interval_sec = ?",
            (INTERVAL_MINUTES * 60,)
        )

        sensors["sampling_interval_sec"] = INTERVAL_MINUTES * 60

        sensors.to_csv(
            OUTPUT_DIR / "sensors.csv",
            index=False
        )

        timestamps = pd.date_range(
            start=START_DATE,
            periods=READINGS_PER_SENSOR,
            freq=f"{INTERVAL_MINUTES}min"
        )

        # Generate ground-truth schedules
        failures = generate_failure_schedule(machines)

        sensor_faults = generate_sensor_fault_schedule(
            sensors,
            timestamps
        )

        failures.to_csv(
            GROUND_TRUTH_DIR / "failure_schedule.csv",
            index=False
        )

        sensor_faults.to_csv(
            GROUND_TRUTH_DIR / "sensor_fault_schedule.csv",
            index=False
        )

        print("Failure schedule:", len(failures))
        print("Sensor fault schedule:", len(sensor_faults))

        # Reset previous telemetry for reproducibility
        connection.execute("DELETE FROM TelemetryEvent")

        telemetry_path = OUTPUT_DIR / "telemetry_events.csv"

        if telemetry_path.exists():
            telemetry_path.unlink()

        columns = [
            "telemetry_id",
            "sensor_id",
            "machine_id",
            "timestamp",
            "reading_value",
            "unit",
            "operating_state",
            "quality_status",
            "issue_type",
            "created_at"
        ]

        placeholders = ", ".join(["?"] * len(columns))

        query = (
            "INSERT INTO TelemetryEvent "
            f"({', '.join(columns)}) "
            f"VALUES ({placeholders})"
        )

        total_records = 0

        # Efficient batch processing
        for index, sensor in sensors.iterrows():

            values, states, quality, issues = generate_readings(
                sensor,
                timestamps,
                failures,
                sensor_faults
            )

            timestamp_strings = timestamps.strftime(
                "%Y-%m-%dT%H:%M:%S"
            )

            telemetry_ids = [
                f"TEL-{sensor['sensor_id']}-{ts}"
                for ts in timestamps.strftime("%Y%m%dT%H%M%S")
            ]

            dataframe = pd.DataFrame({
                "telemetry_id": telemetry_ids,
                "sensor_id": sensor["sensor_id"],
                "machine_id": sensor["machine_id"],
                "timestamp": timestamp_strings,
                "reading_value": values,
                "unit": sensor["unit"],
                "operating_state": states,
                "quality_status": quality,
                "issue_type": issues,
                "created_at": timestamp_strings
            })

            # Write CSV incrementally
            dataframe.to_csv(
                telemetry_path,
                mode="a",
                header=(index == 0),
                index=False
            )

            # Insert into SQLite in batches
            records = dataframe.itertuples(
                index=False,
                name=None
            )

            connection.executemany(
                query,
                records
            )

            total_records += len(dataframe)

            if (index + 1) % 10 == 0:

                connection.commit()

                print(
                    f"Processed {index + 1}/500 sensors | "
                    f"Readings: {total_records:,}"
                )

        connection.commit()

        # Verify total count
        db_count = connection.execute(
            "SELECT COUNT(*) FROM TelemetryEvent"
        ).fetchone()[0]

        if db_count != total_records:
            raise ValueError("Telemetry record count mismatch")

        # Verify sensor-to-machine relationships
        mismatches = connection.execute("""
            SELECT COUNT(*)
            FROM TelemetryEvent t
            JOIN Sensor s ON t.sensor_id = s.sensor_id
            WHERE t.machine_id != s.machine_id
        """).fetchone()[0]

        if mismatches:
            raise ValueError("Sensor-machine mismatch detected")

        fk_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise ValueError(f"Foreign key errors: {fk_errors[:5]}")

        print("\n======================================")
        print("TELEMETRY GENERATION COMPLETED")
        print("======================================")

        print(f"Total sensors: {len(sensors)}")
        print(f"Readings per sensor: {READINGS_PER_SENSOR:,}")
        print(f"Total readings: {db_count:,}")
        print(f"Failure scenarios: {len(failures)}")
        print(f"Sensor fault scenarios: {len(sensor_faults)}")
        print("Sensor-machine relationships: PASSED")
        print("Foreign key validation: PASSED")

    finally:

        connection.close()


if __name__ == "__main__":
    main()
