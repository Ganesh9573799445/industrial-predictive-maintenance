
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = BASE_DIR / "data" / "processed" / "feature_dataset.csv"
MODEL_FILE = BASE_DIR / "data" / "processed" / "models" / "best_model.joblib"
METADATA_FILE = BASE_DIR / "data" / "processed" / "models" / "model_metadata.json"


def main():
    # Load feature dataset
    df = pd.read_csv(DATA_FILE)
    df["date"] = pd.to_datetime(df["date"])

    # Load model metadata
    with open(METADATA_FILE, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    # Load trained model
    model = joblib.load(MODEL_FILE)
    feature_columns = metadata["feature_columns"]

    # Recreate chronological test split
    unique_dates = np.sort(df["date"].unique())
    split_index = int(len(unique_dates) * 0.80)
    test_start = pd.Timestamp(unique_dates[split_index])

    test_df = df[df["date"] >= test_start].copy()

    X_test = test_df[feature_columns]
    y_test = test_df["target_failure_next_7d"].astype(int)

    # Generate predictions
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    test_df["predicted_probability"] = probabilities
    test_df["predicted_class"] = predictions

    # Historical test data summary
    print("\n" + "=" * 60)
    print("HISTORICAL TEST DATA")
    print("=" * 60)

    print("Test start:", test_start)
    print("Test end:", test_df["date"].max())
    print("Test rows:", len(test_df))
    print("Actual positive labels:", int(y_test.sum()))
    print("Actual negative labels:", int((y_test == 0).sum()))

    # Probability distribution
    print("\nPROBABILITY DISTRIBUTION")
    print(test_df["predicted_probability"].describe())

    # Prediction counts
    print("\nPREDICTION COUNTS")
    print(pd.Series(predictions).value_counts().sort_index())

    # Actual labels vs probability
    print("\nACTUAL LABEL VS PREDICTED PROBABILITY")
    print(
        test_df.groupby("target_failure_next_7d")[
            "predicted_probability"
        ].describe()
    )

    # Top 15 risk predictions
    print("\nTOP 15 HISTORICAL RISK PREDICTIONS")
    print(
        test_df.sort_values(
            "predicted_probability", ascending=False
        )[
            [
                "machine_id",
                "date",
                "target_failure_next_7d",
                "predicted_probability",
                "predicted_class",
            ]
        ].head(15).to_string(index=False)
    )

    # Check positive labels with zero probability
    zero_positive = test_df[
        (test_df["target_failure_next_7d"] == 1)
        & (test_df["predicted_probability"] == 0)
    ]

    print("\nPOSITIVE LABELS WITH ZERO PROBABILITY")
    print("Count:", len(zero_positive))

    # Final evaluation metrics
    print("\n" + "=" * 60)
    print("FINAL MODEL EVALUATION")
    print("=" * 60)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions, zero_division=0
    )
    recall = recall_score(
        y_test, predictions, zero_division=0
    )
    f1 = f1_score(
        y_test, predictions, zero_division=0
    )
    roc_auc = roc_auc_score(y_test, probabilities)
    pr_auc = average_precision_score(y_test, probabilities)

    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print(f"PR-AUC:    {pr_auc:.4f}")

    # Confusion matrix
    print("\nCONFUSION MATRIX")
    matrix = confusion_matrix(y_test, predictions)
    print(matrix)

    print("\nConfusion matrix interpretation:")
    print("Rows = Actual classes [0, 1]")
    print("Columns = Predicted classes [0, 1]")
    print("TN:", matrix[0, 0])
    print("FP:", matrix[0, 1])
    print("FN:", matrix[1, 0])
    print("TP:", matrix[1, 1])

    # Classification report
    print("\nCLASSIFICATION REPORT")
    print(
        classification_report(
            y_test,
            predictions,
            target_names=["No Failure", "Failure"],
            zero_division=0,
        )
    )


if __name__ == "__main__":
    main()
