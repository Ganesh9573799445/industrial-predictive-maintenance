
PRAGMA foreign_keys = ON;

-- =========================================
-- 1. PLANT
-- =========================================
CREATE TABLE IF NOT EXISTS Plant (
    plant_id TEXT PRIMARY KEY,
    plant_name TEXT NOT NULL,
    location TEXT NOT NULL,
    country TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active'
        CHECK(status IN ('Active', 'Inactive')),
    created_at TEXT NOT NULL
);

-- =========================================
-- 2. PRODUCTION LINE
-- =========================================
CREATE TABLE IF NOT EXISTS ProductionLine (
    line_id TEXT PRIMARY KEY,
    plant_id TEXT NOT NULL,
    line_name TEXT NOT NULL,
    production_type TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK(status IN ('Active', 'Inactive')),
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    FOREIGN KEY (plant_id) REFERENCES Plant(plant_id),
    CHECK(effective_to IS NULL OR effective_to > effective_from),
    UNIQUE(plant_id, line_name)
);

-- =========================================
-- 3. MACHINE
-- =========================================
CREATE TABLE IF NOT EXISTS Machine (
    machine_id TEXT PRIMARY KEY,
    line_id TEXT NOT NULL,
    machine_name TEXT NOT NULL,
    machine_type TEXT NOT NULL,
    manufacturer TEXT,
    installation_date TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL
        CHECK(lifecycle_state IN (
            'Running', 'Idle', 'Shutdown',
            'Under_Maintenance', 'Retired'
        )),
    criticality TEXT NOT NULL
        CHECK(criticality IN ('Low', 'Medium', 'High')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (line_id) REFERENCES ProductionLine(line_id)
);

-- =========================================
-- 4. TECHNICIAN
-- =========================================
CREATE TABLE IF NOT EXISTS Technician (
    technician_id TEXT PRIMARY KEY,
    technician_name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    experience_years INTEGER NOT NULL
        CHECK(experience_years >= 0),
    availability_status TEXT NOT NULL
        CHECK(availability_status IN (
            'Available', 'Busy', 'Inactive'
        ))
);

-- =========================================
-- 5. SENSOR
-- =========================================
CREATE TABLE IF NOT EXISTS Sensor (
    sensor_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL
        CHECK(sensor_type IN (
            'Temperature', 'Vibration',
            'Pressure', 'Current', 'Speed'
        )),
    unit TEXT NOT NULL,
    min_range REAL NOT NULL,
    max_range REAL NOT NULL,
    sampling_interval_sec INTEGER NOT NULL
        CHECK(sampling_interval_sec > 0),
    installation_date TEXT NOT NULL,
    sensor_status TEXT NOT NULL
        CHECK(sensor_status IN (
            'Active', 'Faulty', 'Replaced', 'Retired'
        )),
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id),
    CHECK(max_range > min_range)
);

-- =========================================
-- 6. OPERATING SHIFT
-- =========================================
CREATE TABLE IF NOT EXISTS OperatingShift (
    shift_id TEXT PRIMARY KEY,
    plant_id TEXT NOT NULL,
    shift_name TEXT NOT NULL
        CHECK(shift_name IN ('Morning', 'Evening', 'Night')),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    supervisor_id TEXT,
    FOREIGN KEY (plant_id) REFERENCES Plant(plant_id),
    FOREIGN KEY (supervisor_id)
        REFERENCES Technician(technician_id),
    CHECK(end_time > start_time)
);

-- =========================================
-- 7. FAILURE EVENT
-- =========================================
CREATE TABLE IF NOT EXISTS FailureEvent (
    failure_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    failure_time TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    root_cause TEXT,
    downtime_minutes INTEGER NOT NULL DEFAULT 0
        CHECK(downtime_minutes >= 0),
    resolution_status TEXT NOT NULL
        CHECK(resolution_status IN (
            'Open', 'Resolved', 'Investigating'
        )),
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id)
);

-- =========================================
-- 8. MAINTENANCE WORK ORDER
-- =========================================
CREATE TABLE IF NOT EXISTS MaintenanceWorkOrder (
    work_order_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    technician_id TEXT,
    failure_id TEXT,
    maintenance_type TEXT NOT NULL
        CHECK(maintenance_type IN (
            'Preventive', 'Corrective', 'Inspection'
        )),
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL
        CHECK(status IN (
            'Open', 'In_Progress', 'Completed', 'Cancelled'
        )),
    downtime_minutes INTEGER NOT NULL DEFAULT 0
        CHECK(downtime_minutes >= 0),
    maintenance_notes TEXT,
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id),
    FOREIGN KEY (technician_id) REFERENCES Technician(technician_id),
    FOREIGN KEY (failure_id) REFERENCES FailureEvent(failure_id),
    CHECK(end_time IS NULL OR end_time >= start_time),
    UNIQUE(failure_id)
);

-- =========================================
-- 9. PART
-- =========================================
CREATE TABLE IF NOT EXISTS Part (
    part_id TEXT PRIMARY KEY,
    part_name TEXT NOT NULL,
    part_category TEXT NOT NULL,
    unit_cost REAL NOT NULL CHECK(unit_cost >= 0),
    stock_quantity INTEGER NOT NULL CHECK(stock_quantity >= 0),
    supplier TEXT,
    status TEXT NOT NULL
        CHECK(status IN (
            'Available', 'Out_of_Stock', 'Discontinued'
        ))
);

-- =========================================
-- 10. TELEMETRY EVENT
-- =========================================
CREATE TABLE IF NOT EXISTS TelemetryEvent (
    telemetry_id TEXT PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    reading_value REAL NOT NULL,
    unit TEXT NOT NULL,
    operating_state TEXT NOT NULL
        CHECK(operating_state IN (
            'Running', 'Idle', 'Shutdown', 'Maintenance'
        )),
    quality_status TEXT NOT NULL
        CHECK(quality_status IN (
            'Valid', 'Out_of_Range',
            'Sensor_Fault', 'Unknown_Sensor'
        )),
    issue_type TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (sensor_id) REFERENCES Sensor(sensor_id),
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id)
);

-- =========================================
-- 11. WORK ORDER - PART BRIDGE
-- =========================================
CREATE TABLE IF NOT EXISTS WorkOrderPart (
    work_order_id TEXT NOT NULL,
    part_id TEXT NOT NULL,
    quantity_used INTEGER NOT NULL CHECK(quantity_used > 0),
    unit_cost_at_use REAL NOT NULL CHECK(unit_cost_at_use >= 0),
    PRIMARY KEY (work_order_id, part_id),
    FOREIGN KEY (work_order_id)
        REFERENCES MaintenanceWorkOrder(work_order_id),
    FOREIGN KEY (part_id) REFERENCES Part(part_id)
);

-- =========================================
-- 12. WORK ORDER - TECHNICIAN BRIDGE
-- =========================================
CREATE TABLE IF NOT EXISTS WorkOrderTechnician (
    work_order_id TEXT NOT NULL,
    technician_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    role TEXT NOT NULL,
    PRIMARY KEY (work_order_id, technician_id),
    FOREIGN KEY (work_order_id)
        REFERENCES MaintenanceWorkOrder(work_order_id),
    FOREIGN KEY (technician_id)
        REFERENCES Technician(technician_id)
);

-- =========================================
-- 13. MACHINE - SHIFT BRIDGE
-- =========================================
CREATE TABLE IF NOT EXISTS MachineShift (
    machine_id TEXT NOT NULL,
    shift_id TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    PRIMARY KEY (machine_id, shift_id, effective_from),
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id),
    FOREIGN KEY (shift_id) REFERENCES OperatingShift(shift_id),
    CHECK(effective_to IS NULL OR effective_to > effective_from)
);

-- =========================================
-- 14. MACHINE STATE HISTORY
-- =========================================
CREATE TABLE IF NOT EXISTS MachineStateHistory (
    state_event_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    change_reason TEXT,
    FOREIGN KEY (machine_id) REFERENCES Machine(machine_id)
);

-- =========================================
-- 15. SENSOR STATE HISTORY
-- =========================================
CREATE TABLE IF NOT EXISTS SensorStateHistory (
    state_event_id TEXT PRIMARY KEY,
    sensor_id TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    change_reason TEXT,
    FOREIGN KEY (sensor_id) REFERENCES Sensor(sensor_id)
);

-- =========================================
-- 16. WORK ORDER STATUS HISTORY
-- =========================================
CREATE TABLE IF NOT EXISTS WorkOrderStatusHistory (
    status_event_id TEXT PRIMARY KEY,
    work_order_id TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    change_reason TEXT,
    FOREIGN KEY (work_order_id)
        REFERENCES MaintenanceWorkOrder(work_order_id)
);

-- =========================================
-- INDEXES FOR FASTER QUERIES
-- =========================================
CREATE INDEX IF NOT EXISTS idx_line_plant
ON ProductionLine(plant_id);

CREATE INDEX IF NOT EXISTS idx_machine_line
ON Machine(line_id);

CREATE INDEX IF NOT EXISTS idx_sensor_machine
ON Sensor(machine_id);

CREATE INDEX IF NOT EXISTS idx_telemetry_sensor_time
ON TelemetryEvent(sensor_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_telemetry_machine_time
ON TelemetryEvent(machine_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_failure_machine_time
ON FailureEvent(machine_id, failure_time);

CREATE INDEX IF NOT EXISTS idx_workorder_machine
ON MaintenanceWorkOrder(machine_id);

CREATE INDEX IF NOT EXISTS idx_shift_plant
ON OperatingShift(plant_id);
