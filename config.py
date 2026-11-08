
from pathlib import Path

# Project configuration
RANDOM_SEED = 20261022

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
EXPORTS_DIR = DATA_DIR / "exports"

DATABASE_PATH = RAW_DATA_DIR / "predictive_maintenance.db"

# Telemetry configuration
NUM_PLANTS = 3
NUM_PRODUCTION_LINES = 12
NUM_MACHINES = 100
NUM_SENSORS = 500

TELEMETRY_DAYS = 90
TELEMETRY_INTERVAL_MINUTES = 30

# Prediction configuration
PREDICTION_HORIZON_DAYS = 7
RISK_LOW_THRESHOLD = 30
RISK_MEDIUM_THRESHOLD = 60
