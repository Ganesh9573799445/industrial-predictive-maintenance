
import sqlite3
import random
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd


# ==========================================
# CONFIGURATION
# ==========================================

SEED = 20261022

TOTAL_PLANTS = 3
LINES_PER_PLANT = 4
TOTAL_MACHINES = 100
SENSORS_PER_MACHINE = 5
TOTAL_TECHNICIANS = 20
TOTAL_PARTS = 50

rng = random.Random(SEED)

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "raw" / "predictive_maintenance.db"
OUTPUT_DIR = BASE_DIR / "data" / "raw"

FIXED_TIMESTAMP = "2026-01-01T00:00:00"


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def random_installation_date():
    start = date(2021, 1, 1)
    end = date(2025, 12, 31)

    days = (end - start).days

    return (
        start + timedelta(days=rng.randint(0, days))
    ).isoformat()


# ==========================================
# 1. GENERATE PLANTS
# ==========================================

def generate_plants():

    plants = []

    locations = [
        ("Hyderabad", "India"),
        ("Chennai", "India"),
        ("Pune", "India")
    ]

    for i in range(1, TOTAL_PLANTS + 1):

        location, country = locations[i - 1]

        plants.append({
            "plant_id": f"PLT-{i:03d}",
            "plant_name": f"Manufacturing Plant {i}",
            "location": location,
            "country": country,
            "status": "Active",
            "created_at": FIXED_TIMESTAMP
        })

    return plants


# ==========================================
# 2. GENERATE PRODUCTION LINES
# ==========================================

def generate_production_lines(plants):

    lines = []

    line_types = [
        "Assembly",
        "Packaging",
        "Processing",
        "Quality_Control"
    ]

    for plant in plants:

        for i in range(1, LINES_PER_PLANT + 1):

            line_id = (
                f"LINE-{plant['plant_id']}-{i:03d}"
            )

            lines.append({
                "line_id": line_id,
                "plant_id": plant["plant_id"],
                "line_name": f"Production Line {i}",
                "production_type": line_types[i - 1],
                "status": "Active",
                "effective_from": "2021-01-01",
                "effective_to": None
            })

    return lines


# ==========================================
# 3. GENERATE MACHINES
# ==========================================

def generate_machines(lines):

    machines = []

    machine_types = [
        "Conveyor",
        "Hydraulic_Press",
        "CNC_Machine",
        "Compressor",
        "Industrial_Motor",
        "Packaging_Machine",
        "Pump",
        "Cooling_System"
    ]

    manufacturers = [
        "Siemens",
        "ABB",
        "Bosch",
        "Mitsubishi",
        "Honeywell"
    ]

    machine_counter = 0

    for line_index, line in enumerate(lines):

        # Distribute 100 machines across 12 lines.
        machine_count = (
            TOTAL_MACHINES // len(lines)
            + (1 if line_index < TOTAL_MACHINES % len(lines) else 0)
        )

        for i in range(1, machine_count + 1):

            machine_counter += 1

            install_date = random_installation_date()

            machines.append({
                "machine_id": (
                    f"MCH-{line['line_id']}-{i:03d}"
                ),
                "line_id": line["line_id"],
                "machine_name": (
                    f"Machine {machine_counter:03d}"
                ),
                "machine_type": rng.choice(machine_types),
                "manufacturer": rng.choice(manufacturers),
                "installation_date": install_date,
                "lifecycle_state": rng.choices(
                    ["Running", "Idle", "Shutdown"],
                    weights=[85, 10, 5]
                )[0],
                "criticality": rng.choices(
                    ["Low", "Medium", "High"],
                    weights=[20, 50, 30]
                )[0],
                "created_at": FIXED_TIMESTAMP
            })

    return machines


# ==========================================
# 4. GENERATE SENSORS
# ==========================================

def generate_sensors(machines):

    sensors = []

    sensor_config = [
        {
            "type": "Temperature",
            "code": "TEMP",
            "unit": "C",
            "min": 0,
            "max": 150
        },
        {
            "type": "Vibration",
            "code": "VIB",
            "unit": "mm/s",
            "min": 0,
            "max": 50
        },
        {
            "type": "Pressure",
            "code": "PRES",
            "unit": "bar",
            "min": 0,
            "max": 20
        },
        {
            "type": "Current",
            "code": "CURR",
            "unit": "A",
            "min": 0,
            "max": 100
        },
        {
            "type": "Speed",
            "code": "SPEED",
            "unit": "RPM",
            "min": 0,
            "max": 5000
        }
    ]

    for machine in machines:

        for config in sensor_config:

            sensor_id = (
                f"SNS-{machine['machine_id']}-"
                f"{config['code']}-01"
            )

            sensors.append({
                "sensor_id": sensor_id,
                "machine_id": machine["machine_id"],
                "sensor_type": config["type"],
                "unit": config["unit"],
                "min_range": config["min"],
                "max_range": config["max"],
                "sampling_interval_sec": 300,
                "installation_date": machine["installation_date"],
                "sensor_status": "Active"
            })

    return sensors


# ==========================================
# 5. GENERATE TECHNICIANS
# ==========================================

def generate_technicians():

    technicians = []

    specializations = [
        "Mechanical",
        "Electrical",
        "Instrumentation",
        "Hydraulics",
        "Automation"
    ]

    for i in range(1, TOTAL_TECHNICIANS + 1):

        technicians.append({
            "technician_id": f"TECH-{i:03d}",
            "technician_name": f"Technician {i:03d}",
            "specialization": rng.choice(specializations),
            "experience_years": rng.randint(1, 20),
            "availability_status": "Available"
        })

    return technicians


# ==========================================
# 6. GENERATE PARTS
# ==========================================

def generate_parts():

    parts = []

    categories = [
        "Bearing",
        "Motor",
        "Belt",
        "Filter",
        "Valve",
        "Sensor",
        "Gear",
        "Pump"
    ]

    for i in range(1, TOTAL_PARTS + 1):

        category = rng.choice(categories)

        parts.append({
            "part_id": f"PART-{i:03d}",
            "part_name": f"Industrial {category} {i:03d}",
            "part_category": category,
            "unit_cost": round(
                rng.uniform(100, 25000), 2
            ),
            "stock_quantity": rng.randint(0, 100),
            "supplier": f"Supplier {rng.randint(1, 10):02d}",
            "status": "Available"
        })

    return parts


# ==========================================
# 7. SAVE CSV FILES
# ==========================================

def save_csv(data, filename):

    dataframe = pd.DataFrame(data)

    path = OUTPUT_DIR / filename

    dataframe.to_csv(path, index=False)

    print(f"Saved: {filename} ({len(data)} rows)")


# ==========================================
# 8. INSERT INTO SQLITE DATABASE
# ==========================================

def insert_records(connection, table_name, records):

    if not records:
        return

    columns = list(records[0].keys())

    column_names = ", ".join(columns)

    placeholders = ", ".join(
        ["?"] * len(columns)
    )

    query = (
        f"INSERT OR IGNORE INTO {table_name} "
        f"({column_names}) VALUES ({placeholders})"
    )

    values = [
        tuple(record[column] for column in columns)
        for record in records
    ]

    connection.executemany(query, values)


# ==========================================
# 9. MAIN EXECUTION
# ==========================================

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nGenerating master data...\n")

    plants = generate_plants()

    lines = generate_production_lines(plants)

    machines = generate_machines(lines)

    sensors = generate_sensors(machines)

    technicians = generate_technicians()

    parts = generate_parts()

    # Export CSV files

    save_csv(plants, "plants.csv")

    save_csv(lines, "production_lines.csv")

    save_csv(machines, "machines.csv")

    save_csv(sensors, "sensors.csv")

    save_csv(technicians, "technicians.csv")

    save_csv(parts, "parts.csv")

    # Insert into database

    connection = sqlite3.connect(DB_PATH)

    try:

        connection.execute("PRAGMA foreign_keys = ON")

        with connection:

            insert_records(connection, "Plant", plants)

            insert_records(connection, "ProductionLine", lines)

            insert_records(connection, "Machine", machines)

            insert_records(connection, "Technician", technicians)

            insert_records(connection, "Sensor", sensors)

            insert_records(connection, "Part", parts)

        print("\nDatabase insertion completed!")

        # Verify record counts

        print("\nDATABASE RECORD COUNTS")

        for table in [
            "Plant",
            "ProductionLine",
            "Machine",
            "Sensor",
            "Technician",
            "Part"
        ]:

            count = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            print(f"{table}: {count}")

        # Foreign key validation

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise ValueError(
                f"Foreign key violations: {violations}"
            )

        print("\nForeign key validation: PASSED")

    finally:

        connection.close()

    print("\nMaster data generation completed successfully!")


if __name__ == "__main__":
    main()
