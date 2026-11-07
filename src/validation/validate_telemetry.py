
import sqlite3
import csv
from pathlib import Path


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data/raw/predictive_maintenance.db"
RAW_DIR = BASE_DIR / "data/raw"
GROUND_TRUTH_DIR = BASE_DIR / "data/ground_truth"

EXPECTED_SENSORS = 500
EXPECTED_READINGS_PER_SENSOR = 4320
EXPECTED_TOTAL_READINGS = 2_160_000

EXPECTED_FAILURES = 100
EXPECTED_SENSOR_FAULTS = 10

INTERVAL_SECONDS = 1800

passed = 0
failed = 0


# ==========================================
# REPORT FUNCTION
# ==========================================

def report(message, condition):

    global passed, failed

    if condition:
        passed += 1
        print(f"[PASS] {message}")
    else:
        failed += 1
        print(f"[FAIL] {message}")


# ==========================================
# CSV ROW COUNT
# ==========================================

def csv_row_count(path):

    if not path.exists():
        return -1

    with open(path, "r", encoding="utf-8", newline="") as file:
        return sum(1 for _ in csv.reader(file)) - 1


# ==========================================
# 1. DATABASE CONNECTION
# ==========================================

def connect_database():

    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# 2. RECORD COUNT VALIDATION
# ==========================================

def validate_record_counts(connection):

    print("\n1. RECORD COUNT VALIDATION")

    total = connection.execute(
        "SELECT COUNT(*) FROM TelemetryEvent"
    ).fetchone()[0]

    report(
        f"Total telemetry readings: {total:,}",
        total == EXPECTED_TOTAL_READINGS
    )

    sensors = connection.execute(
        "SELECT COUNT(*) FROM Sensor"
    ).fetchone()[0]

    report(
        f"Total sensors: {sensors}",
        sensors == EXPECTED_SENSORS
    )

    incorrect_counts = connection.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT sensor_id
            FROM TelemetryEvent
            GROUP BY sensor_id
            HAVING COUNT(*) != ?
        )
    """, (EXPECTED_READINGS_PER_SENSOR,)).fetchone()[0]

    report(
        "Every sensor has exactly 4,320 readings",
        incorrect_counts == 0
    )


# ==========================================
# 3. PRIMARY KEY VALIDATION
# ==========================================

def validate_telemetry_ids(connection):

    print("\n2. TELEMETRY ID VALIDATION")

    duplicates = connection.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT telemetry_id
            FROM TelemetryEvent
            GROUP BY telemetry_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    report(
        "No duplicate telemetry IDs",
        duplicates == 0
    )

    null_ids = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE telemetry_id IS NULL
           OR telemetry_id = ''
    """).fetchone()[0]

    report(
        "No missing telemetry IDs",
        null_ids == 0
    )


# ==========================================
# 4. SENSOR-MACHINE RELATIONSHIPS
# ==========================================

def validate_relationships(connection):

    print("\n3. RELATIONSHIP VALIDATION")

    mismatches = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent t
        JOIN Sensor s
          ON t.sensor_id = s.sensor_id
        WHERE t.machine_id != s.machine_id
    """).fetchone()[0]

    report(
        "Telemetry sensor-machine relationships valid",
        mismatches == 0
    )

    missing_sensors = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent t
        LEFT JOIN Sensor s
          ON t.sensor_id = s.sensor_id
        WHERE s.sensor_id IS NULL
    """).fetchone()[0]

    report(
        "No unknown sensors in baseline telemetry",
        missing_sensors == 0
    )

    unit_mismatches = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent t
        JOIN Sensor s
          ON t.sensor_id = s.sensor_id
        WHERE t.unit != s.unit
    """).fetchone()[0]

    report(
        "Telemetry units match sensor units",
        unit_mismatches == 0
    )


# ==========================================
# 5. MEASUREMENT RANGE VALIDATION
# ==========================================

def validate_measurements(connection):

    print("\n4. MEASUREMENT VALIDATION")

    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent t
        JOIN Sensor s
          ON t.sensor_id = s.sensor_id
        WHERE t.reading_value < s.min_range
           OR t.reading_value > s.max_range
    """).fetchone()[0]

    report(
        "All baseline readings are within sensor ranges",
        invalid == 0
    )

    null_values = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE reading_value IS NULL
    """).fetchone()[0]

    report(
        "No missing telemetry values",
        null_values == 0
    )


# ==========================================
# 6. OPERATING STATE VALIDATION
# ==========================================

def validate_operating_states(connection):

    print("\n5. OPERATING STATE VALIDATION")

    invalid = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE operating_state NOT IN (
            'Running', 'Idle', 'Shutdown', 'Maintenance'
        )
    """).fetchone()[0]

    report(
        "All operating states are valid",
        invalid == 0
    )

    state_counts = connection.execute("""
        SELECT operating_state, COUNT(*)
        FROM TelemetryEvent
        GROUP BY operating_state
    """).fetchall()

    for state, count in state_counts:
        print(f"  {state}: {count:,}")

    running = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE operating_state = 'Running'
    """).fetchone()[0]

    report(
        "Running-state readings exist",
        running > 0
    )

    idle = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE operating_state = 'Idle'
    """).fetchone()[0]

    report(
        "Idle-state readings exist",
        idle > 0
    )

    shutdown = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE operating_state = 'Shutdown'
    """).fetchone()[0]

    report(
        "Shutdown-state readings exist",
        shutdown > 0
    )


# ==========================================
# 7. TIME SERIES VALIDATION
# ==========================================

def validate_timestamps(connection):

    print("\n6. TIME SERIES VALIDATION")

    invalid_timestamps = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE strftime('%s', timestamp) IS NULL
    """).fetchone()[0]

    report(
        "All timestamps are valid",
        invalid_timestamps == 0
    )

    duplicate_timestamps = connection.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT sensor_id, timestamp
            FROM TelemetryEvent
            GROUP BY sensor_id, timestamp
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    report(
        "No duplicate sensor timestamps",
        duplicate_timestamps == 0
    )

    # Add index to improve time-series checks
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_telemetry_sensor_timestamp
        ON TelemetryEvent(sensor_id, timestamp)
    """)

    connection.commit()

    gap_count = connection.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT
                sensor_id,
                timestamp,
                LAG(timestamp) OVER (
                    PARTITION BY sensor_id
                    ORDER BY timestamp
                ) AS previous_timestamp
            FROM TelemetryEvent
        )
        WHERE previous_timestamp IS NOT NULL
          AND (
              strftime('%s', timestamp)
              - strftime('%s', previous_timestamp)
          ) != ?
    """, (INTERVAL_SECONDS,)).fetchone()[0]

    report(
        "No unexpected time gaps in baseline telemetry",
        gap_count == 0
    )

    first_last = connection.execute("""
        SELECT
            MIN(timestamp),
            MAX(timestamp)
        FROM TelemetryEvent
    """).fetchone()

    print("  First reading:", first_last[0])
    print("  Last reading:", first_last[1])


# ==========================================
# 8. SENSOR FAULT VALIDATION
# ==========================================

def validate_sensor_faults(connection):

    print("\n7. SENSOR FAULT VALIDATION")

    fault_count = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE quality_status = 'Sensor_Fault'
    """).fetchone()[0]

    faulty_sensors = connection.execute("""
        SELECT COUNT(DISTINCT sensor_id)
        FROM TelemetryEvent
        WHERE quality_status = 'Sensor_Fault'
    """).fetchone()[0]

    print("  Faulty sensor readings:", fault_count)
    print("  Sensors with faults:", faulty_sensors)

    report(
        "Sensor fault readings were generated",
        fault_count > 0
    )

    report(
        "Faults affect exactly 10 scheduled sensors",
        faulty_sensors == EXPECTED_SENSOR_FAULTS
    )

    issue_mismatches = connection.execute("""
        SELECT COUNT(*)
        FROM TelemetryEvent
        WHERE quality_status = 'Sensor_Fault'
          AND issue_type != 'STUCK_SENSOR'
    """).fetchone()[0]

    report(
        "Sensor fault issue types are documented",
        issue_mismatches == 0
    )


# ==========================================
# 9. GROUND TRUTH VALIDATION
# ==========================================

def validate_ground_truth():

    print("\n8. GROUND TRUTH VALIDATION")

    failure_path = (
        GROUND_TRUTH_DIR / "failure_schedule.csv"
    )

    sensor_fault_path = (
        GROUND_TRUTH_DIR / "sensor_fault_schedule.csv"
    )

    failure_count = csv_row_count(failure_path)

    fault_count = csv_row_count(sensor_fault_path)

    report(
        "Failure schedule contains 100 events",
        failure_count == EXPECTED_FAILURES
    )

    report(
        "Sensor fault schedule contains 10 events",
        fault_count == EXPECTED_SENSOR_FAULTS
    )


# ==========================================
# 10. CSV / DATABASE RECONCILIATION
# ==========================================

def validate_csv(connection):

    print("\n9. CSV RECONCILIATION")

    csv_path = RAW_DIR / "telemetry_events.csv"

    csv_count = csv_row_count(csv_path)

    database_count = connection.execute(
        "SELECT COUNT(*) FROM TelemetryEvent"
    ).fetchone()[0]

    report(
        "Telemetry CSV record count matches database",
        csv_count == database_count
    )

    print(f"  CSV records: {csv_count:,}")
    print(f"  Database records: {database_count:,}")


# ==========================================
# MAIN
# ==========================================

def main():

    global passed, failed

    print("=" * 60)
    print("PREDICTIVE MAINTENANCE TELEMETRY VALIDATION")
    print("=" * 60)

    connection = connect_database()

    try:

        validate_record_counts(connection)
        validate_telemetry_ids(connection)
        validate_relationships(connection)
        validate_measurements(connection)
        validate_operating_states(connection)
        validate_timestamps(connection)
        validate_sensor_faults(connection)
        validate_ground_truth()
        validate_csv(connection)

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        report(
            "Database foreign key integrity",
            len(foreign_key_errors) == 0
        )

    finally:

        connection.close()

    print("\n" + "=" * 60)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 60)

    print("Passed:", passed)
    print("Failed:", failed)

    if failed == 0:
        print("\nALL TELEMETRY VALIDATIONS PASSED!")
    else:
        print("\nVALIDATION ISSUES FOUND.")

    print("=" * 60)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
