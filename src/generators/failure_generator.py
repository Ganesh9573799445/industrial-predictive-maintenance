
import sqlite3
import random
from pathlib import Path

import pandas as pd


# ==========================================
# CONFIGURATION
# ==========================================

SEED = 20261022

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data/raw/predictive_maintenance.db"

GROUND_TRUTH_DIR = BASE_DIR / "data/ground_truth"

OUTPUT_DIR = BASE_DIR / "data/raw"

FAILURE_SCHEDULE = (
    GROUND_TRUTH_DIR / "failure_schedule.csv"
)

rng = random.Random(SEED + 2)


# ==========================================
# LOAD FAILURE SCHEDULE
# ==========================================

def load_failure_schedule():

    if not FAILURE_SCHEDULE.exists():
        raise FileNotFoundError(
            f"Failure schedule not found: {FAILURE_SCHEDULE}"
        )

    failures = pd.read_csv(FAILURE_SCHEDULE)

    required_columns = [
        "failure_id",
        "machine_id",
        "failure_time",
        "failure_type",
        "severity",
        "root_cause"
    ]

    missing = set(required_columns) - set(failures.columns)

    if missing:
        raise ValueError(
            f"Missing schedule columns: {missing}"
        )

    if len(failures) != 100:
        raise ValueError(
            f"Expected 100 failures, found {len(failures)}"
        )

    if failures["failure_id"].duplicated().any():
        raise ValueError("Duplicate failure IDs found")

    return failures


# ==========================================
# VALIDATE MACHINE REFERENCES
# ==========================================

def validate_machine_ids(connection, failures):

    valid_machine_ids = {
        row[0]
        for row in connection.execute(
            "SELECT machine_id FROM Machine"
        ).fetchall()
    }

    invalid = set(failures["machine_id"]) - valid_machine_ids

    if invalid:
        raise ValueError(
            f"Unknown machine IDs: {invalid}"
        )

    print("Machine references: PASSED")


# ==========================================
# GENERATE FAILURE EVENTS
# ==========================================

def generate_failure_events(failures):

    events = []

    for _, failure in failures.iterrows():

        failure_time = pd.Timestamp(
            failure["failure_time"]
        )

        downtime = rng.randint(60, 480)

        resolution_status = "Resolved"

        recorded_at = (
            failure_time + pd.Timedelta(minutes=5)
        )

        events.append({
            "failure_id": failure["failure_id"],
            "machine_id": failure["machine_id"],
            "failure_time": failure_time.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "failure_type": failure["failure_type"],
            "severity": failure["severity"],
            "root_cause": failure["root_cause"],
            "downtime_minutes": downtime,
            "resolution_status": resolution_status,
            "recorded_at": recorded_at.strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
        })

    return events


# ==========================================
# INSERT FAILURE EVENTS
# ==========================================

def insert_failure_events(connection, events):

    columns = list(events[0].keys())

    query = (
        f"INSERT OR IGNORE INTO FailureEvent "
        f"({', '.join(columns)}) "
        f"VALUES ({', '.join(['?'] * len(columns))})"
    )

    values = [
        tuple(event[column] for column in columns)
        for event in events
    ]

    connection.executemany(query, values)

    connection.commit()


# ==========================================
# VALIDATE INSERTED EVENTS
# ==========================================

def validate_failure_events(connection):

    total = connection.execute(
        "SELECT COUNT(*) FROM FailureEvent"
    ).fetchone()[0]

    print("\nFAILURE EVENT COUNTS")

    print("Total failure events:", total)

    if total != 100:
        raise ValueError(
            f"Expected 100 failure events, found {total}"
        )

    invalid_machine_refs = connection.execute("""
        SELECT COUNT(*)
        FROM FailureEvent f
        LEFT JOIN Machine m
          ON f.machine_id = m.machine_id
        WHERE m.machine_id IS NULL
    """).fetchone()[0]

    if invalid_machine_refs:
        raise ValueError(
            "Invalid machine references detected"
        )

    invalid_dates = connection.execute("""
        SELECT COUNT(*)
        FROM FailureEvent
        WHERE failure_time > recorded_at
    """).fetchone()[0]

    if invalid_dates:
        raise ValueError(
            "Failure recorded before its occurrence"
        )

    print("Failure-machine relationships: PASSED")
    print("Failure timestamp validation: PASSED")

    return total


# ==========================================
# MAIN
# ==========================================

def main():

    print("\nStarting failure event generation...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    failures = load_failure_schedule()

    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    try:

        telemetry_count = connection.execute(
            "SELECT COUNT(*) FROM TelemetryEvent"
        ).fetchone()[0]

        if telemetry_count != 2_160_000:
            raise ValueError(
                "Telemetry generation must complete before "
                "failure generation."
            )

        validate_machine_ids(connection, failures)

        events = generate_failure_events(failures)

        insert_failure_events(connection, events)

        # Export generated failure events
        pd.DataFrame(events).to_csv(
            OUTPUT_DIR / "failure_events.csv",
            index=False
        )

        validate_failure_events(connection)

        fk_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise ValueError(
                f"Foreign key errors: {fk_errors}"
            )

        print("\n===================================")
        print("FAILURE GENERATION COMPLETED")
        print("===================================")

        print("Generated failures:", len(events))
        print("Foreign key validation: PASSED")

    finally:

        connection.close()


if __name__ == "__main__":
    main()
