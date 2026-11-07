
import sqlite3
import pandas as pd
from pathlib import Path


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "raw" / "predictive_maintenance.db"
DATA_DIR = BASE_DIR / "data" / "raw"

EXPECTED_COUNTS = {
    "Plant": 3,
    "ProductionLine": 12,
    "Machine": 100,
    "Sensor": 500,
    "Technician": 20,
    "Part": 50
}

CSV_FILES = {
    "Plant": "plants.csv",
    "ProductionLine": "production_lines.csv",
    "Machine": "machines.csv",
    "Sensor": "sensors.csv",
    "Technician": "technicians.csv",
    "Part": "parts.csv"
}

PRIMARY_KEYS = {
    "Plant": "plant_id",
    "ProductionLine": "line_id",
    "Machine": "machine_id",
    "Sensor": "sensor_id",
    "Technician": "technician_id",
    "Part": "part_id"
}

REQUIRED_COLUMNS = {
    "Plant": [
        "plant_id", "plant_name", "location",
        "country", "status", "created_at"
    ],
    "ProductionLine": [
        "line_id", "plant_id", "line_name",
        "production_type", "status", "effective_from"
    ],
    "Machine": [
        "machine_id", "line_id", "machine_name",
        "machine_type", "installation_date",
        "lifecycle_state", "criticality", "created_at"
    ],
    "Sensor": [
        "sensor_id", "machine_id", "sensor_type",
        "unit", "min_range", "max_range",
        "sampling_interval_sec", "installation_date",
        "sensor_status"
    ],
    "Technician": [
        "technician_id", "technician_name",
        "specialization", "experience_years",
        "availability_status"
    ],
    "Part": [
        "part_id", "part_name", "part_category",
        "unit_cost", "stock_quantity", "status"
    ]
}

SENSOR_UNITS = {
    "Temperature": "C",
    "Vibration": "mm/s",
    "Pressure": "bar",
    "Current": "A",
    "Speed": "RPM"
}

EXPECTED_SENSOR_RANGES = {
    "Temperature": (0, 150),
    "Vibration": (0, 50),
    "Pressure": (0, 20),
    "Current": (0, 100),
    "Speed": (0, 5000)
}


# ==========================================
# VALIDATION REPORT
# ==========================================

passed = 0
failed = 0


def report(message, success):

    global passed, failed

    if success:
        passed += 1
        print(f"[PASS] {message}")
    else:
        failed += 1
        print(f"[FAIL] {message}")


# ==========================================
# LOAD DATABASE
# ==========================================

def load_database():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==========================================
# 1. RECORD COUNT VALIDATION
# ==========================================

def validate_record_counts(connection):

    print("\n1. RECORD COUNT VALIDATION")

    for table, expected in EXPECTED_COUNTS.items():

        actual = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        report(
            f"{table}: expected={expected}, actual={actual}",
            actual == expected
        )


# ==========================================
# 2. PRIMARY KEY VALIDATION
# ==========================================

def validate_primary_keys(connection):

    print("\n2. PRIMARY KEY VALIDATION")

    for table, primary_key in PRIMARY_KEYS.items():

        query = f"""
            SELECT
                COUNT(*) - COUNT(DISTINCT {primary_key})
            FROM {table}
        """

        duplicates = connection.execute(
            query
        ).fetchone()[0]

        nulls = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {table}
            WHERE {primary_key} IS NULL
               OR TRIM({primary_key}) = ''
            """
        ).fetchone()[0]

        report(
            f"{table}: unique and non-null primary keys",
            duplicates == 0 and nulls == 0
        )


# ==========================================
# 3. FOREIGN KEY VALIDATION
# ==========================================

def validate_foreign_keys(connection):

    print("\n3. FOREIGN KEY VALIDATION")

    violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    report(
        "All database foreign keys are valid",
        len(violations) == 0
    )

    if violations:
        print("Foreign key violations:", violations[:10])


# ==========================================
# 4. REQUIRED FIELD VALIDATION
# ==========================================

def validate_required_fields(connection):

    print("\n4. REQUIRED FIELD VALIDATION")

    for table, columns in REQUIRED_COLUMNS.items():

        invalid_fields = []

        for column in columns:

            query = f"""
                SELECT COUNT(*)
                FROM {table}
                WHERE {column} IS NULL
                   OR TRIM(CAST({column} AS TEXT)) = ''
            """

            count = connection.execute(
                query
            ).fetchone()[0]

            if count > 0:
                invalid_fields.append(column)

        report(
            f"{table}: all required fields populated",
            len(invalid_fields) == 0
        )

        if invalid_fields:
            print("  Missing fields:", invalid_fields)


# ==========================================
# 5. HIERARCHY VALIDATION
# ==========================================

def validate_relationships(connection):

    print("\n5. HIERARCHY VALIDATION")

    invalid_lines = connection.execute("""
        SELECT COUNT(*)
        FROM ProductionLine l
        LEFT JOIN Plant p ON l.plant_id = p.plant_id
        WHERE p.plant_id IS NULL
    """).fetchone()[0]

    invalid_machines = connection.execute("""
        SELECT COUNT(*)
        FROM Machine m
        LEFT JOIN ProductionLine l ON m.line_id = l.line_id
        WHERE l.line_id IS NULL
    """).fetchone()[0]

    invalid_sensors = connection.execute("""
        SELECT COUNT(*)
        FROM Sensor s
        LEFT JOIN Machine m ON s.machine_id = m.machine_id
        WHERE m.machine_id IS NULL
    """).fetchone()[0]

    report(
        "ProductionLine -> Plant relationships",
        invalid_lines == 0
    )

    report(
        "Machine -> ProductionLine relationships",
        invalid_machines == 0
    )

    report(
        "Sensor -> Machine relationships",
        invalid_sensors == 0
    )


# ==========================================
# 6. SENSOR VALIDATION
# ==========================================

def validate_sensors(connection):

    print("\n6. SENSOR VALIDATION")

    sensors = pd.read_sql_query(
        "SELECT * FROM Sensor",
        connection
    )

    valid_units = sensors.apply(
        lambda row:
        SENSOR_UNITS.get(row["sensor_type"]) == row["unit"],
        axis=1
    )

    report(
        "Sensor types have correct measurement units",
        bool(valid_units.all())
    )

    valid_ranges = sensors.apply(
        lambda row:
        (
            row["sensor_type"] in EXPECTED_SENSOR_RANGES
            and row["min_range"] == EXPECTED_SENSOR_RANGES[
                row["sensor_type"]
            ][0]
            and row["max_range"] == EXPECTED_SENSOR_RANGES[
                row["sensor_type"]
            ][1]
        ),
        axis=1
    )

    report(
        "Sensor measurement ranges are correct",
        bool(valid_ranges.all())
    )

    report(
        "Every machine has exactly five sensors",
        bool(
            sensors.groupby("machine_id").size().eq(5).all()
        )
    )


# ==========================================
# 7. CSV VALIDATION
# ==========================================

def validate_csv_files(connection):

    print("\n7. CSV VALIDATION")

    for table, filename in CSV_FILES.items():

        path = DATA_DIR / filename

        if not path.exists():

            report(f"{filename} exists", False)
            continue

        dataframe = pd.read_csv(path)

        report(
            f"{filename} contains expected records",
            len(dataframe) == EXPECTED_COUNTS[table]
        )

        primary_key = PRIMARY_KEYS[table]

        unique = dataframe[primary_key].is_unique

        report(
            f"{filename}: unique {primary_key}",
            bool(unique)
        )

        database_ids = set(
            row[0]
            for row in connection.execute(
                f"SELECT {primary_key} FROM {table}"
            ).fetchall()
        )

        csv_ids = set(dataframe[primary_key].dropna())

        report(
            f"{filename}: IDs match database",
            database_ids == csv_ids
        )


# ==========================================
# 8. DATE AND NUMERIC VALIDATION
# ==========================================

def validate_dates_and_numbers(connection):

    print("\n8. DATE AND NUMERIC VALIDATION")

    invalid_dates = connection.execute("""
        SELECT COUNT(*)
        FROM Machine
        WHERE date(installation_date) IS NULL
    """).fetchone()[0]

    report(
        "Machine installation dates are valid",
        invalid_dates == 0
    )

    invalid_sensors = connection.execute("""
        SELECT COUNT(*)
        FROM Sensor
        WHERE min_range >= max_range
           OR sampling_interval_sec <= 0
    """).fetchone()[0]

    report(
        "Sensor ranges and sampling intervals are valid",
        invalid_sensors == 0
    )

    invalid_parts = connection.execute("""
        SELECT COUNT(*)
        FROM Part
        WHERE unit_cost < 0
           OR stock_quantity < 0
    """).fetchone()[0]

    report(
        "Part prices and stock quantities are valid",
        invalid_parts == 0
    )


# ==========================================
# 9. MAIN VALIDATION
# ==========================================

def main():

    global passed, failed

    print("=" * 55)
    print("PREDICTIVE MAINTENANCE DATA VALIDATION")
    print("=" * 55)

    connection = load_database()

    try:

        validate_record_counts(connection)

        validate_primary_keys(connection)

        validate_foreign_keys(connection)

        validate_required_fields(connection)

        validate_relationships(connection)

        validate_sensors(connection)

        validate_csv_files(connection)

        validate_dates_and_numbers(connection)

    finally:

        connection.close()

    print("\n" + "=" * 55)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 55)

    print("Passed:", passed)
    print("Failed:", failed)

    if failed == 0:

        print("\nALL VALIDATIONS PASSED!")

    else:

        print("\nVALIDATION ISSUES FOUND.")

    print("=" * 55)

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
