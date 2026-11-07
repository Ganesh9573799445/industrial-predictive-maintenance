
import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd


# ==========================================
# 1. CONFIGURATION
# ==========================================

SEED = 20261022

PREVENTIVE_WORK_ORDERS = 50

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data/raw/predictive_maintenance.db"
OUTPUT_DIR = BASE_DIR / "data/raw"

rng = random.Random(SEED + 3)


# ==========================================
# 2. LOAD SOURCE DATA
# ==========================================

def load_source_data(connection):

    failures = pd.read_sql_query(
        "SELECT * FROM FailureEvent ORDER BY failure_time",
        connection
    )

    machines = pd.read_sql_query(
        "SELECT machine_id FROM Machine ORDER BY machine_id",
        connection
    )

    technicians = pd.read_sql_query(
        "SELECT technician_id FROM Technician ORDER BY technician_id",
        connection
    )

    parts = pd.read_sql_query(
        "SELECT * FROM Part ORDER BY part_id",
        connection
    )

    if len(failures) != 100:
        raise ValueError(
            f"Expected 100 failure events, found {len(failures)}"
        )

    if len(machines) != 100:
        raise ValueError("Expected 100 machines")

    if len(technicians) != 20:
        raise ValueError("Expected 20 technicians")

    if len(parts) != 50:
        raise ValueError("Expected 50 parts")

    return failures, machines, technicians, parts


# ==========================================
# 3. GENERATE WORK ORDERS
# ==========================================

def generate_work_orders(
    failures,
    machines,
    technicians,
    parts
):

    work_orders = []
    technician_assignments = []
    part_assignments = []
    status_history = []

    technician_ids = technicians[
        "technician_id"
    ].tolist()

    machine_ids = machines[
        "machine_id"
    ].tolist()

    # Track available stock without changing
    # the original Part master records.
    remaining_stock = dict(
        zip(parts["part_id"], parts["stock_quantity"])
    )

    part_costs = dict(
        zip(parts["part_id"], parts["unit_cost"])
    )

    available_parts = [
        part_id
        for part_id, quantity in remaining_stock.items()
        if quantity > 0
    ]

    order_counter = 0

    def create_order(
        machine_id,
        maintenance_type,
        start_time,
        downtime,
        failure_id=None
    ):

        nonlocal order_counter

        order_counter += 1

        work_order_id = f"WO-2026-{order_counter:06d}"

        start = pd.Timestamp(start_time)

        end = start + pd.Timedelta(
            minutes=downtime
        )

        start_string = start.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        end_string = end.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        # Assign 1 or 2 technicians
        assigned_technicians = rng.sample(
            technician_ids,
            rng.choice([1, 2])
        )

        primary_technician = assigned_technicians[0]

        work_orders.append({
            "work_order_id": work_order_id,
            "machine_id": machine_id,
            "technician_id": primary_technician,
            "failure_id": failure_id,
            "maintenance_type": maintenance_type,
            "start_time": start_string,
            "end_time": end_string,
            "status": "Completed",
            "downtime_minutes": downtime,
            "maintenance_notes": (
                f"Synthetic {maintenance_type.lower()} "
                "maintenance activity"
            )
        })

        # Technician bridge records
        for index, technician_id in enumerate(
            assigned_technicians
        ):

            technician_assignments.append({
                "work_order_id": work_order_id,
                "technician_id": technician_id,
                "assigned_at": start_string,
                "role": (
                    "Lead Technician"
                    if index == 0
                    else "Supporting Technician"
                )
            })

        # Allocate a replacement part if stock exists
        if available_parts:

            usable_parts = [
                part_id
                for part_id in available_parts
                if remaining_stock[part_id] > 0
            ]

            if usable_parts:

                selected_part = rng.choice(usable_parts)

                quantity = min(
                    remaining_stock[selected_part],
                    rng.randint(1, 2)
                )

                part_assignments.append({
                    "work_order_id": work_order_id,
                    "part_id": selected_part,
                    "quantity_used": quantity,
                    "unit_cost_at_use": part_costs[
                        selected_part
                    ]
                })

                remaining_stock[selected_part] -= quantity

        # Record lifecycle transitions
        opened_at = start - pd.Timedelta(minutes=30)

        in_progress_at = start

        completed_at = end

        transitions = [
            ("Open", opened_at),
            ("In_Progress", in_progress_at),
            ("Completed", completed_at)
        ]

        previous_status = None

        for index, (new_status, changed_at) in enumerate(
            transitions,
            start=1
        ):

            status_history.append({
                "status_event_id": (
                    f"WOS-{order_counter:06d}-{index:02d}"
                ),
                "work_order_id": work_order_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "changed_at": changed_at.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                ),
                "change_reason": (
                    "Work order created"
                    if index == 1
                    else "Maintenance lifecycle transition"
                )
            })

            previous_status = new_status

    # --------------------------------------
    # A. CORRECTIVE MAINTENANCE
    # --------------------------------------

    for _, failure in failures.iterrows():

        downtime = int(
            failure["downtime_minutes"]
        )

        create_order(
            machine_id=failure["machine_id"],
            maintenance_type="Corrective",
            start_time=failure["failure_time"],
            downtime=downtime,
            failure_id=failure["failure_id"]
        )

    # --------------------------------------
    # B. PREVENTIVE MAINTENANCE
    # --------------------------------------

    for _ in range(PREVENTIVE_WORK_ORDERS):

        machine_id = rng.choice(machine_ids)

        start = datetime(
            2026,
            1,
            1
        ) + timedelta(
            days=rng.randint(0, 89),
            hours=rng.randint(6, 20)
        )

        downtime = rng.randint(60, 240)

        create_order(
            machine_id=machine_id,
            maintenance_type="Preventive",
            start_time=start,
            downtime=downtime
        )

    return (
        work_orders,
        technician_assignments,
        part_assignments,
        status_history
    )


# ==========================================
# 4. INSERT RECORDS INTO SQLITE
# ==========================================

def insert_records(connection, table, records):

    if not records:
        return

    columns = list(records[0].keys())

    placeholders = ", ".join(
        ["?"] * len(columns)
    )

    query = (
        f"INSERT INTO {table} "
        f"({', '.join(columns)}) "
        f"VALUES ({placeholders})"
    )

    values = [
        tuple(record[column] for column in columns)
        for record in records
    ]

    connection.executemany(query, values)


# ==========================================
# 5. RECONCILIATION
# ==========================================

def validate_maintenance(connection):

    print("\nMAINTENANCE RECONCILIATION")

    total_orders = connection.execute(
        "SELECT COUNT(*) FROM MaintenanceWorkOrder"
    ).fetchone()[0]

    corrective = connection.execute("""
        SELECT COUNT(*)
        FROM MaintenanceWorkOrder
        WHERE maintenance_type = 'Corrective'
    """).fetchone()[0]

    preventive = connection.execute("""
        SELECT COUNT(*)
        FROM MaintenanceWorkOrder
        WHERE maintenance_type = 'Preventive'
    """).fetchone()[0]

    mismatch = connection.execute("""
        SELECT COUNT(*)
        FROM MaintenanceWorkOrder w
        JOIN FailureEvent f
          ON w.failure_id = f.failure_id
        WHERE w.downtime_minutes != f.downtime_minutes
           OR w.machine_id != f.machine_id
           OR w.start_time < f.failure_time
           OR w.maintenance_type != 'Corrective'
    """).fetchone()[0]

    invalid_parts = connection.execute("""
        SELECT COUNT(*)
        FROM WorkOrderPart
        WHERE quantity_used <= 0
    """).fetchone()[0]

    invalid_dates = connection.execute("""
        SELECT COUNT(*)
        FROM MaintenanceWorkOrder
        WHERE end_time < start_time
    """).fetchone()[0]

    print("Total work orders:", total_orders)
    print("Corrective orders:", corrective)
    print("Preventive orders:", preventive)

    if total_orders != 150:
        raise ValueError("Work order count mismatch")

    if corrective != 100 or preventive != 50:
        raise ValueError("Maintenance type count mismatch")

    if mismatch or invalid_parts or invalid_dates:
        raise ValueError("Maintenance reconciliation failed")

    print("Failure-work order reconciliation: PASSED")
    print("Part quantity validation: PASSED")
    print("Maintenance date validation: PASSED")


# ==========================================
# 6. MAIN EXECUTION
# ==========================================

def main():

    print("\nStarting maintenance generation...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    try:

        failures, machines, technicians, parts = (
            load_source_data(connection)
        )

        # Generate all records before inserting
        (
            work_orders,
            technician_assignments,
            part_assignments,
            status_history
        ) = generate_work_orders(
            failures,
            machines,
            technicians,
            parts
        )

        # Clear previous generated records in dependency order
        with connection:

            connection.execute(
                "DELETE FROM WorkOrderPart"
            )

            connection.execute(
                "DELETE FROM WorkOrderTechnician"
            )

            connection.execute(
                "DELETE FROM WorkOrderStatusHistory"
            )

            connection.execute(
                "DELETE FROM MaintenanceWorkOrder"
            )

            # Insert parent work orders first
            insert_records(
                connection,
                "MaintenanceWorkOrder",
                work_orders
            )

            # Insert dependent bridge/history records
            insert_records(
                connection,
                "WorkOrderTechnician",
                technician_assignments
            )

            insert_records(
                connection,
                "WorkOrderPart",
                part_assignments
            )

            insert_records(
                connection,
                "WorkOrderStatusHistory",
                status_history
            )

        # Export CSV files
        pd.DataFrame(work_orders).to_csv(
            OUTPUT_DIR / "maintenance_work_orders.csv",
            index=False
        )

        pd.DataFrame(technician_assignments).to_csv(
            OUTPUT_DIR / "work_order_technicians.csv",
            index=False
        )

        pd.DataFrame(part_assignments).to_csv(
            OUTPUT_DIR / "work_order_parts.csv",
            index=False
        )

        pd.DataFrame(status_history).to_csv(
            OUTPUT_DIR / "work_order_status_history.csv",
            index=False
        )

        validate_maintenance(connection)

        fk_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if fk_errors:
            raise ValueError(
                f"Foreign key errors: {fk_errors}"
            )

        print("\n======================================")
        print("MAINTENANCE GENERATION COMPLETED")
        print("======================================")

        print("Work orders:", len(work_orders))
        print("Technician assignments:", len(technician_assignments))
        print("Part assignments:", len(part_assignments))
        print("Status history records:", len(status_history))
        print("Foreign key validation: PASSED")

    finally:

        connection.close()


if __name__ == "__main__":
    main()
