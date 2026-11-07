# Predictive Maintenance System – Data Dictionary

## 1. Project Overview

**Project:** Industrial Predictive Maintenance System

**Purpose:** Identify equipment at elevated failure risk using telemetry, operating context and maintenance history.

**Dataset configuration:**
- Plants: 3
- Production lines: 12
- Machines: 100
- Sensors: 500
- Telemetry period: 90 days
- Telemetry readings: 1–3 million
- Labelled failures: 100–200
- Random seed: 20261022

---

## 2. Plant

**Purpose:** Stores manufacturing facility information.

| Field | Data type | Constraint / Validation |
|---|---|---|
| plant_id | VARCHAR(20) | PK, required, unique, PLT-001 |
| plant_name | VARCHAR(100) | Required |
| location | VARCHAR(150) | Required |
| country | VARCHAR(50) | Required |
| status | VARCHAR(20) | Active / Inactive |
| created_at | TIMESTAMP | Required |

## 3. ProductionLine

**Purpose:** Represents production lines within a plant.

| Field | Data type | Constraint / Validation |
|---|---|---|
| line_id | VARCHAR(50) | PK, unique |
| plant_id | VARCHAR(20) | FK → Plant |
| line_name | VARCHAR(100) | Required |
| production_type | VARCHAR(50) | Required |
| status | VARCHAR(20) | Active / Inactive |
| effective_from | TIMESTAMP | Required |
| effective_to | TIMESTAMP | Optional, must be after effective_from |

## 4. Machine

**Purpose:** Stores equipment details.

| Field | Data type | Constraint / Validation |
|---|---|---|
| machine_id | VARCHAR(80) | PK, unique |
| line_id | VARCHAR(50) | FK → ProductionLine |
| machine_name | VARCHAR(100) | Required |
| machine_type | VARCHAR(50) | Required |
| manufacturer | VARCHAR(100) | Optional |
| installation_date | DATE | Required |
| lifecycle_state | VARCHAR(30) | Running / Idle / Shutdown / Under_Maintenance / Retired |
| criticality | VARCHAR(20) | Low / Medium / High |
| created_at | TIMESTAMP | Required |

## 5. Sensor

**Purpose:** Stores sensors assigned to machines.

| Field | Data type | Constraint / Validation |
|---|---|---|
| sensor_id | VARCHAR(100) | PK, unique |
| machine_id | VARCHAR(80) | FK → Machine |
| sensor_type | VARCHAR(30) | Temperature / Vibration / Pressure / Current / Speed |
| unit | VARCHAR(20) | °C / mm/s / bar / A / RPM |
| min_range | FLOAT | Required |
| max_range | FLOAT | Must be greater than min_range |
| sampling_interval_sec | INTEGER | Positive |
| installation_date | DATE | Required |
| sensor_status | VARCHAR(20) | Active / Faulty / Replaced / Retired |

## 6. TelemetryEvent

**Purpose:** Stores timestamped sensor readings.

| Field | Data type | Constraint / Validation |
|---|---|---|
| telemetry_id | VARCHAR(150) | PK, unique |
| sensor_id | VARCHAR(100) | FK → Sensor |
| machine_id | VARCHAR(80) | FK → Machine |
| timestamp | TIMESTAMP | Required |
| reading_value | FLOAT | Required |
| unit | VARCHAR(20) | Must match sensor unit |
| operating_state | VARCHAR(30) | Running / Idle / Shutdown / Maintenance |
| quality_status | VARCHAR(30) | Valid / Out_of_Range / Sensor_Fault / Unknown_Sensor |
| issue_type | VARCHAR(50) | Optional |
| created_at | TIMESTAMP | Required |

## 7. OperatingShift

**Purpose:** Records machine operating shifts.

| Field | Data type | Constraint / Validation |
|---|---|---|
| shift_id | VARCHAR(50) | PK, unique |
| plant_id | VARCHAR(20) | FK → Plant |
| shift_name | VARCHAR(30) | Morning / Evening / Night |
| start_time | TIMESTAMP | Required |
| end_time | TIMESTAMP | Must be after start_time |
| supervisor_id | VARCHAR(50) | Optional FK → Technician |

## 8. MaintenanceWorkOrder

**Purpose:** Stores maintenance activities.

| Field | Data type | Constraint / Validation |
|---|---|---|
| work_order_id | VARCHAR(30) | PK, unique |
| machine_id | VARCHAR(80) | FK → Machine |
| technician_id | VARCHAR(50) | FK → Technician |
| failure_id | VARCHAR(50) | Optional FK → FailureEvent |
| maintenance_type | VARCHAR(30) | Preventive / Corrective / Inspection |
| start_time | TIMESTAMP | Required |
| end_time | TIMESTAMP | Optional, after start_time |
| status | VARCHAR(30) | Open / In_Progress / Completed / Cancelled |
| downtime_minutes | INTEGER | Non-negative |
| maintenance_notes | TEXT | Optional |

## 9. FailureEvent

**Purpose:** Records actual machine failure incidents.

| Field | Data type | Constraint / Validation |
|---|---|---|
| failure_id | VARCHAR(50) | PK, unique |
| machine_id | VARCHAR(80) | FK → Machine |
| failure_time | TIMESTAMP | Required |
| failure_type | VARCHAR(50) | Required |
| severity | VARCHAR(20) | Low / Medium / High / Critical |
| root_cause | VARCHAR(100) | Optional |
| downtime_minutes | INTEGER | Non-negative |
| resolution_status | VARCHAR(30) | Open / Resolved / Investigating |
| recorded_at | TIMESTAMP | Required |

## 10. Part

**Purpose:** Stores replacement components.

| Field | Data type | Constraint / Validation |
|---|---|---|
| part_id | VARCHAR(50) | PK, unique |
| part_name | VARCHAR(100) | Required |
| part_category | VARCHAR(50) | Required |
| unit_cost | DECIMAL(12,2) | Non-negative |
| stock_quantity | INTEGER | Non-negative |
| supplier | VARCHAR(100) | Optional |
| status | VARCHAR(20) | Available / Out_of_Stock / Discontinued |

## 11. Technician

**Purpose:** Stores maintenance personnel details.

| Field | Data type | Constraint / Validation |
|---|---|---|
| technician_id | VARCHAR(50) | PK, unique |
| technician_name | VARCHAR(100) | Required |
| specialization | VARCHAR(50) | Required |
| experience_years | INTEGER | Non-negative |
| availability_status | VARCHAR(20) | Available / Busy / Inactive |

---

## 12. Bridge Tables

### WorkOrderPart

Connects maintenance work orders with replacement parts.

| Field | Data type | Constraint |
|---|---|---|
| work_order_id | VARCHAR(30) | FK → MaintenanceWorkOrder |
| part_id | VARCHAR(50) | FK → Part |
| quantity_used | INTEGER | Positive |
| unit_cost_at_use | DECIMAL(12,2) | Non-negative |

Composite primary key: (work_order_id, part_id).

### WorkOrderTechnician

Connects work orders with multiple technicians.

| Field | Data type | Constraint |
|---|---|---|
| work_order_id | VARCHAR(30) | FK → MaintenanceWorkOrder |
| technician_id | VARCHAR(50) | FK → Technician |
| assigned_at | TIMESTAMP | Required |
| role | VARCHAR(30) | Required |

Composite primary key: (work_order_id, technician_id).

### MachineShift

Connects machines to operating shifts.

| Field | Data type | Constraint |
|---|---|---|
| machine_id | VARCHAR(80) | FK → Machine |
| shift_id | VARCHAR(50) | FK → OperatingShift |
| effective_from | TIMESTAMP | Required |
| effective_to | TIMESTAMP | Optional |

Composite primary key: (machine_id, shift_id, effective_from).

---

## 13. Entity Relationships

| Parent | Child | Cardinality |
|---|---|---|
| Plant | ProductionLine | 1:N |
| ProductionLine | Machine | 1:N |
| Machine | Sensor | 1:N |
| Sensor | TelemetryEvent | 1:N |
| Plant | OperatingShift | 1:N |
| Machine | MaintenanceWorkOrder | 1:N |
| Machine | FailureEvent | 1:N |
| Technician | MaintenanceWorkOrder | 1:N optional |
| MaintenanceWorkOrder | Part | N:M |
| MaintenanceWorkOrder | Technician | N:M |
| Machine | OperatingShift | N:M |

## 14. Data Quality Rules

1. All primary keys must be unique and non-null.
2. All foreign keys must reference existing parent records.
3. Sensor units must match their assigned sensor type.
4. Telemetry timestamps must be consistent with the sensor's installation and retirement periods.
5. Maintenance end time must not precede start time.
6. Failure events must have valid machine IDs.
7. Failure labels must not appear in model input features.
8. Sensor faults must be distinguished from machine failures.
9. Missing telemetry must remain missing, not be silently replaced with zero.
10. Derived downtime must reconcile with source maintenance and failure records.

## 15. Reproducibility

Random seed: `20261022`

All IDs must be generated deterministically.

The generator must produce identical data when executed repeatedly with the same configuration and seed.

Ground-truth labels must be stored separately from model input data.

---

**End of Data Dictionary**