
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Predictive Maintenance Dashboard",
    page_icon="🏭",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"

PREDICTION_FILE = DATA_DIR / "processed" / "predictions.csv"
MACHINE_FILE = DATA_DIR / "raw" / "machines.csv"
PLANT_FILE = DATA_DIR / "raw" / "plants.csv"
LINE_FILE = DATA_DIR / "raw" / "production_lines.csv"
TELEMETRY_FILE = DATA_DIR / "raw" / "telemetry_events.csv"
FAILURE_FILE = DATA_DIR / "raw" / "failure_events.csv"
MAINTENANCE_FILE = DATA_DIR / "raw" / "maintenance_work_orders.csv"


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data
def load_data():
    predictions = pd.read_csv(PREDICTION_FILE)
    machines = pd.read_csv(MACHINE_FILE)
    plants = pd.read_csv(PLANT_FILE)
    lines = pd.read_csv(LINE_FILE)
    failures = pd.read_csv(FAILURE_FILE)
    maintenance = pd.read_csv(MAINTENANCE_FILE)

    return predictions, machines, plants, lines, failures, maintenance


try:
    (
        predictions,
        machines,
        plants,
        lines,
        failures,
        maintenance
    ) = load_data()

except FileNotFoundError as error:
    st.error(f"Required data file not found: {error}")
    st.stop()


# --------------------------------------------------
# DATA PREPARATION
# --------------------------------------------------

# Merge machine information into predictions
if "machine_id" in predictions.columns and "machine_id" in machines.columns:
    machine_columns = [
        column for column in [
            "machine_id",
            "line_id",
            "machine_type",
            "machine_name",
            "status"
        ]
        if column in machines.columns
    ]

    predictions = predictions.merge(
        machines[machine_columns],
        on="machine_id",
        how="left",
        suffixes=("", "_machine")
    )

# Convert probability to percentage
if "failure_probability" in predictions.columns:
    predictions["risk_probability"] = (
        predictions["failure_probability"] * 100
    )
elif "probability" in predictions.columns:
    predictions["risk_probability"] = (
        predictions["probability"] * 100
    )
elif "failure_probability_percent" in predictions.columns:
    predictions["risk_probability"] = predictions[
        "failure_probability_percent"
    ]
else:
    predictions["risk_probability"] = 0.0

# Support different risk column names
if "risk_level" not in predictions.columns:
    if "risk_category" in predictions.columns:
        predictions["risk_level"] = predictions["risk_category"]
    else:
        predictions["risk_level"] = pd.cut(
            predictions["risk_probability"],
            bins=[-0.01, 30, 60, 100],
            labels=["Low", "Medium", "High"]
        ).astype(str)

# Normalize risk labels
predictions["risk_level"] = (
    predictions["risk_level"].astype(str).str.title()
)

# Convert dates
if "date" in predictions.columns:
    predictions["date"] = pd.to_datetime(
        predictions["date"], errors="coerce"
    )


# --------------------------------------------------
# DASHBOARD HEADER
# --------------------------------------------------

st.title("🏭 Industrial Predictive Maintenance")
st.caption(
    "Machine health monitoring | Failure risk prediction | "
    "Maintenance intelligence"
)

st.divider()


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.header("Dashboard Filters")

selected_risks = st.sidebar.multiselect(
    "Risk Level",
    options=["Low", "Medium", "High"],
    default=["Low", "Medium", "High"]
)

filtered_predictions = predictions[
    predictions["risk_level"].isin(selected_risks)
].copy()

if "plant_id" in machines.columns:
    plant_options = ["All"] + sorted(
        machines["plant_id"].dropna().astype(str).unique().tolist()
    )

    selected_plant = st.sidebar.selectbox(
        "Plant",
        plant_options
    )

    if selected_plant != "All" and "plant_id" in predictions.columns:
        filtered_predictions = filtered_predictions[
            filtered_predictions["plant_id"].astype(str) == selected_plant
        ]


# --------------------------------------------------
# KPI METRICS
# --------------------------------------------------

total_plants = len(plants)
total_lines = len(lines)
total_machines = machines["machine_id"].nunique()

high_risk = (
    filtered_predictions["risk_level"] == "High"
).sum()

medium_risk = (
    filtered_predictions["risk_level"] == "Medium"
).sum()

low_risk = (
    filtered_predictions["risk_level"] == "Low"
).sum()

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Plants", total_plants)
col2.metric("Production Lines", total_lines)
col3.metric("Machines", total_machines)
col4.metric("High Risk", int(high_risk))
col5.metric("Medium Risk", int(medium_risk))
col6.metric("Low Risk", int(low_risk))

st.divider()


# --------------------------------------------------
# RISK DISTRIBUTION
# --------------------------------------------------

st.subheader("Machine Failure Risk Distribution")

left, right = st.columns(2)

with left:
    risk_counts = (
        filtered_predictions["risk_level"]
        .value_counts()
        .reindex(["Low", "Medium", "High"], fill_value=0)
        .reset_index()
    )

    risk_counts.columns = ["Risk Level", "Machine Count"]

    fig = px.pie(
        risk_counts,
        names="Risk Level",
        values="Machine Count",
        hole=0.45,
        title="Risk Category Distribution"
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        risk_counts,
        x="Risk Level",
        y="Machine Count",
        title="Machines by Risk Category",
        text="Machine Count"
    )

    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# MACHINE RISK TABLE
# --------------------------------------------------

st.subheader("Machine-wise Failure Risk")

display_columns = [
    column for column in [
        "machine_id",
        "machine_type",
        "line_id",
        "date",
        "risk_probability",
        "risk_level"
    ]
    if column in filtered_predictions.columns
]

st.dataframe(
    filtered_predictions[display_columns].sort_values(
        "risk_probability",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# FAILURE HISTORY
# --------------------------------------------------

st.divider()
st.subheader("Historical Failure Analysis")

if not failures.empty and "failure_time" in failures.columns:

    failures["failure_time"] = pd.to_datetime(
        failures["failure_time"], errors="coerce"
    )

    failures["failure_date"] = failures["failure_time"].dt.date

    failure_trend = (
        failures.groupby("failure_date")
        .size()
        .reset_index(name="Failure Count")
    )

    fig = px.line(
        failure_trend,
        x="failure_date",
        y="Failure Count",
        markers=True,
        title="Daily Machine Failures"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Failure history is unavailable.")


# --------------------------------------------------
# MAINTENANCE INFORMATION
# --------------------------------------------------

st.divider()
st.subheader("Maintenance Work Orders")

maintenance_col1, maintenance_col2, maintenance_col3 = st.columns(3)

maintenance_col1.metric(
    "Total Work Orders",
    len(maintenance)
)

if "status" in maintenance.columns:
    open_orders = maintenance["status"].astype(str).str.lower().isin(
        ["open", "in progress", "pending"]
    ).sum()
else:
    open_orders = 0

maintenance_col2.metric(
    "Open Work Orders",
    int(open_orders)
)

if "maintenance_type" in maintenance.columns:
    corrective_orders = (
        maintenance["maintenance_type"]
        .astype(str)
        .str.lower()
        .eq("corrective")
        .sum()
    )
else:
    corrective_orders = 0

maintenance_col3.metric(
    "Corrective Maintenance",
    int(corrective_orders)
)

st.dataframe(
    maintenance.head(100),
    use_container_width=True,
    hide_index=True
)



# --------------------------------------------------
# MACHINE SENSOR MONITORING
# --------------------------------------------------

st.divider()
st.header("Machine Sensor Monitoring")

SENSOR_TYPES = {
    "TEMP": "Temperature",
    "VIB": "Vibration",
    "PRES": "Pressure",
    "CURR": "Current",
    "SPEED": "Speed",
}


@st.cache_data(show_spinner="Loading machine telemetry...")
def load_machine_telemetry(machine_id):
    required_columns = [
        "sensor_id",
        "machine_id",
        "timestamp",
        "reading_value",
        "unit",
        "operating_state",
        "quality_status",
    ]

    machine_chunks = []

    for chunk in pd.read_csv(
        TELEMETRY_FILE,
        usecols=required_columns,
        chunksize=200_000
    ):
        machine_data = chunk[
            chunk["machine_id"] == machine_id
        ]

        if not machine_data.empty:
            machine_chunks.append(machine_data)

    if not machine_chunks:
        return pd.DataFrame(columns=required_columns)

    result = pd.concat(machine_chunks, ignore_index=True)

    result["timestamp"] = pd.to_datetime(
        result["timestamp"], errors="coerce"
    )

    # Identify sensor type from sensor ID
    result["sensor_code"] = (
        result["sensor_id"]
        .astype(str)
        .str.upper()
        .str.extract(r"-(TEMP|VIB|PRES|CURR|SPEED)-")[0]
    )

    result["sensor_type"] = result["sensor_code"].map(
        SENSOR_TYPES
    )

    result["reading_value"] = pd.to_numeric(
        result["reading_value"], errors="coerce"
    )

    return result.dropna(
        subset=["timestamp", "reading_value", "sensor_type"]
    )


# Select machine
available_machines = sorted(
    machines["machine_id"].dropna().unique().tolist()
)

selected_machine = st.selectbox(
    "Select Machine",
    available_machines,
    key="sensor_machine"
)

telemetry = load_machine_telemetry(selected_machine)

if telemetry.empty:
    st.warning("No telemetry records found for this machine.")

else:
    # Date range selection
    min_date = telemetry["timestamp"].min().date()
    max_date = telemetry["timestamp"].max().date()

    selected_dates = st.date_input(
        "Select Monitoring Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="sensor_date_range"
    )

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates

        filtered_telemetry = telemetry[
            (telemetry["timestamp"].dt.date >= start_date)
            & (telemetry["timestamp"].dt.date <= end_date)
        ].copy()

    else:
        filtered_telemetry = telemetry.copy()

    # Sensor summary
    st.subheader("Sensor Summary")

    sensor_summary = (
        filtered_telemetry.groupby(
            ["sensor_type", "unit"]
        )["reading_value"]
        .agg(["mean", "min", "max", "count"])
        .reset_index()
    )

    sensor_summary.columns = [
        "Sensor",
        "Unit",
        "Average",
        "Minimum",
        "Maximum",
        "Readings"
    ]

    st.dataframe(
        sensor_summary.round(2),
        use_container_width=True,
        hide_index=True
    )

    # Sensor trend charts
    st.subheader("Sensor Reading Trends")

    for sensor_type in SENSOR_TYPES.values():

        sensor_data = filtered_telemetry[
            filtered_telemetry["sensor_type"] == sensor_type
        ].sort_values("timestamp")

        if sensor_data.empty:
            continue

        unit = sensor_data["unit"].mode().iloc[0]

        fig = px.line(
            sensor_data,
            x="timestamp",
            y="reading_value",
            title=f"{sensor_type} Monitoring ({unit})",
            labels={
                "timestamp": "Timestamp",
                "reading_value": f"Reading ({unit})"
            },
            hover_data=[
                "operating_state",
                "quality_status"
            ]
        )

        fig.update_layout(
            hovermode="x unified",
            height=350
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # Operating state distribution
    st.subheader("Operating State Distribution")

    state_counts = (
        filtered_telemetry["operating_state"]
        .value_counts()
        .reset_index()
    )

    state_counts.columns = ["Operating State", "Readings"]

    fig = px.pie(
        state_counts,
        names="Operating State",
        values="Readings",
        hole=0.4,
        title="Machine Operating States"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Sensor data quality
    st.subheader("Sensor Data Quality")

    quality_counts = (
        filtered_telemetry["quality_status"]
        .value_counts()
        .reset_index()
    )

    quality_counts.columns = ["Quality Status", "Readings"]

    st.dataframe(
        quality_counts,
        use_container_width=True,
        hide_index=True
    )



# --------------------------------------------------
# MACHINE-SPECIFIC RISK DETAILS
# --------------------------------------------------

st.divider()
st.header("Machine Health and Risk Details")

# Use the machine selected in Sensor Monitoring
machine_prediction = predictions[
    predictions["machine_id"] == selected_machine
].copy()

if machine_prediction.empty:
    st.warning("Prediction details are unavailable for this machine.")

else:
    machine_prediction = machine_prediction.sort_values(
        "date"
    )

    latest_prediction = machine_prediction.iloc[-1]

    risk_probability = float(
        latest_prediction["risk_probability"]
    )

    risk_level = latest_prediction["risk_level"]

    prediction_date = latest_prediction["date"]

    # Machine information
    machine_info = machines[
        machines["machine_id"] == selected_machine
    ]

    st.subheader(f"Machine: {selected_machine}")

    if not machine_info.empty:
        info = machine_info.iloc[0]

        info1, info2, info3 = st.columns(3)

        info1.metric(
            "Machine Type",
            str(info.get("machine_type", "N/A"))
        )

        info2.metric(
            "Production Line",
            str(info.get("line_id", "N/A"))
        )

        info3.metric(
            "Machine Status",
            str(info.get("status", "N/A"))
        )

    # Risk information
    st.subheader("Failure Risk Assessment")

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    risk_col1.metric(
        "Failure Probability",
        f"{risk_probability:.2f}%"
    )

    risk_col2.metric(
        "Risk Level",
        risk_level
    )

    risk_col3.metric(
        "Prediction Date",
        str(prediction_date)[:10]
    )

    # Risk progress bar
    st.write("Failure Risk Probability")

    st.progress(
        min(max(risk_probability / 100, 0.0), 1.0)
    )

    # Recommended action
    st.subheader("Maintenance Recommendation")

    if risk_level == "High":
        st.error(
            "HIGH RISK: Inspect this machine immediately. "
            "Schedule preventive maintenance and investigate "
            "abnormal sensor readings."
        )

    elif risk_level == "Medium":
        st.warning(
            "MEDIUM RISK: Monitor sensor readings closely. "
            "Plan a maintenance inspection."
        )

    else:
        st.success(
            "LOW RISK: Machine is currently classified as low risk. "
            "Continue routine monitoring and scheduled maintenance."
        )

    # Latest sensor readings
    st.subheader("Latest Sensor Readings")

    machine_telemetry = telemetry[
        telemetry["machine_id"] == selected_machine
    ].copy()

    if not machine_telemetry.empty:

        latest_sensor_readings = (
            machine_telemetry.sort_values("timestamp")
            .groupby("sensor_type")
            .tail(1)
            .sort_values("sensor_type")
        )

        latest_sensor_readings = latest_sensor_readings[
            [
                "sensor_type",
                "reading_value",
                "unit",
                "timestamp",
                "operating_state",
                "quality_status"
            ]
        ]

        st.dataframe(
            latest_sensor_readings,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No sensor readings found for this machine.")

    # Historical failures
    st.subheader("Machine Failure History")

    machine_failures = failures[
        failures["machine_id"] == selected_machine
    ].copy()

    if not machine_failures.empty:

        if "failure_time" in machine_failures.columns:
            machine_failures["failure_time"] = pd.to_datetime(
                machine_failures["failure_time"],
                errors="coerce"
            )

        st.dataframe(
            machine_failures,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No recorded failures for this machine.")

    # Maintenance work orders
    st.subheader("Machine Maintenance History")

    machine_maintenance = maintenance[
        maintenance["machine_id"] == selected_machine
    ].copy()

    if not machine_maintenance.empty:

        st.dataframe(
            machine_maintenance,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No maintenance work orders found for this machine.")

    # Historical risk trend
    st.subheader("Historical Failure Risk Trend")

    if len(machine_prediction) > 1:

        fig = px.line(
            machine_prediction,
            x="date",
            y="risk_probability",
            markers=True,
            title=f"Failure Risk Trend - {selected_machine}",
            labels={
                "date": "Date",
                "risk_probability": "Failure Probability (%)"
            }
        )

        fig.update_yaxes(range=[0, 100])

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        st.info("Not enough prediction history to display a trend.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Predictive Maintenance System | "
    "Machine Learning: Random Forest | "
    "Prediction Horizon: Next 7 Days"
)
