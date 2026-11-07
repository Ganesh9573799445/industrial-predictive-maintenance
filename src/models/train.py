
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)
from sklearn.pipeline import Pipeline


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022
TEST_SIZE = 0.20
PREDICTION_HORIZON_DAYS = 7

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "data" / "processed" / "feature_dataset.csv"
MODEL_DIR = BASE_DIR / "data" / "processed" / "models"
METRICS_DIR = BASE_DIR / "data" / "processed" / "metrics"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "target_failure_next_7d"

DROP_COLUMNS = [
    "machine_id",
    "date",
    TARGET
]


# --------------------------------------------------
# STEP 1: LOAD DATA
# --------------------------------------------------

def load_dataset():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE)
    df["date"] = pd.to_datetime(df["date"])

    if df.empty:
        raise ValueError("Feature dataset is empty.")

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    if df[TARGET].nunique() < 2:
        raise ValueError("Target must contain both classes.")

    print("Dataset loaded successfully.")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Machines:", df["machine_id"].nunique())
    print("Positive labels:", int(df[TARGET].sum()))

    return df


# --------------------------------------------------
# STEP 2: CHRONOLOGICAL TRAIN/TEST SPLIT
# --------------------------------------------------

def split_dataset(df):

    unique_dates = np.sort(df["date"].unique())

    split_index = int(
        len(unique_dates) * (1 - TEST_SIZE)
    )

    test_start = pd.Timestamp(unique_dates[split_index])

    training_cutoff = (
        test_start
        - pd.Timedelta(days=PREDICTION_HORIZON_DAYS)
    )

    train_df = df[
        df["date"] < training_cutoff
    ].copy()

    test_df = df[
        df["date"] >= test_start
    ].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("Train/test split produced an empty dataset.")

    X_train = train_df.drop(columns=DROP_COLUMNS)
    y_train = train_df[TARGET]

    X_test = test_df.drop(columns=DROP_COLUMNS)
    y_test = test_df[TARGET]

    print("\nChronological split:")
    print("Training dates:", train_df["date"].min(), "to", train_df["date"].max())
    print("Testing dates:", test_df["date"].min(), "to", test_df["date"].max())
    print("Training rows:", len(X_train))
    print("Testing rows:", len(X_test))
    print("Training positive labels:", int(y_train.sum()))
    print("Testing positive labels:", int(y_test.sum()))

    if y_train.nunique() < 2:
        raise ValueError("Training set does not contain both classes.")

    if y_test.nunique() < 2:
        raise ValueError("Testing set does not contain both classes.")

    return X_train, X_test, y_train, y_test


# --------------------------------------------------
# STEP 3: DEFINE MODELS
# --------------------------------------------------

def get_models():

    models = {

        "Random Forest": Pipeline([
            (
                "imputer",
                SimpleImputer(strategy="median")
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=12,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    class_weight="balanced",
                    random_state=SEED,
                    n_jobs=-1
                )
            )
        ]),

        "Gradient Boosting": Pipeline([
            (
                "imputer",
                SimpleImputer(strategy="median")
            ),
            (
                "classifier",
                GradientBoostingClassifier(
                    n_estimators=100,
                    learning_rate=0.05,
                    max_depth=3,
                    random_state=SEED
                )
            )
        ])

    }

    return models


# --------------------------------------------------
# STEP 4: EVALUATE MODELS
# --------------------------------------------------

def evaluate_model(model, X_test, y_test):

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(
            accuracy_score(y_test, predictions)
        ),
        "precision": float(
            precision_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "recall": float(
            recall_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "f1_score": float(
            f1_score(
                y_test,
                predictions,
                zero_division=0
            )
        ),
        "roc_auc": float(
            roc_auc_score(y_test, probabilities)
        ),
        "pr_auc": float(
            average_precision_score(y_test, probabilities)
        ),
        "confusion_matrix": confusion_matrix(
            y_test,
            predictions
        ).tolist()
    }

    return metrics, predictions, probabilities


# --------------------------------------------------
# STEP 5: TRAIN AND SAVE
# --------------------------------------------------

def train():

    df = load_dataset()

    X_train, X_test, y_train, y_test = split_dataset(df)

    models = get_models()

    results = {}

    best_model_name = None
    best_model = None
    best_f1_score = -1

    for model_name, model in models.items():

        print("\n" + "=" * 50)
        print("Training:", model_name)
        print("=" * 50)

        model.fit(X_train, y_train)

        metrics, predictions, probabilities = evaluate_model(
            model,
            X_test,
            y_test
        )

        results[model_name] = metrics

        print("\nMetrics:")

        for metric_name, value in metrics.items():
            if metric_name != "confusion_matrix":
                print(f"{metric_name}: {value:.4f}")

        print("\nConfusion Matrix:")
        print(np.array(metrics["confusion_matrix"]))

        print("\nClassification Report:")
        print(
            classification_report(
                y_test,
                predictions,
                zero_division=0
            )
        )

        # Select the best model using F1-score.
        if metrics["f1_score"] > best_f1_score:
            best_f1_score = metrics["f1_score"]
            best_model_name = model_name
            best_model = model

    if best_model is None:
        raise RuntimeError("No model was successfully trained.")

    # Save best model.
    model_path = MODEL_DIR / "best_model.joblib"
    joblib.dump(best_model, model_path)

    # Save model comparison.
    metrics_path = METRICS_DIR / "model_comparison.json"

    with open(metrics_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    # Save training metadata.
    metadata = {
        "random_seed": SEED,
        "target": TARGET,
        "test_size": TEST_SIZE,
        "purge_gap_days": PREDICTION_HORIZON_DAYS,
        "best_model": best_model_name,
        "best_model_f1_score": best_f1_score,
        "feature_columns": list(X_train.columns),
        "training_rows": len(X_train),
        "testing_rows": len(X_test)
    }

    metadata_path = MODEL_DIR / "model_metadata.json"

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    print("\n" + "=" * 50)
    print("MODEL TRAINING COMPLETED")
    print("=" * 50)

    print("Best model:", best_model_name)
    print("Best F1-score:", round(best_f1_score, 4))
    print("Saved model:", model_path)
    print("Saved metrics:", metrics_path)


if __name__ == "__main__":
    train()
