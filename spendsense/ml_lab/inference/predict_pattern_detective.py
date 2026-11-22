
"""
SpendSense Pattern Detective - Isolation Forest Inference

Uses the trained pipeline from:
ml_lab/models/pattern_detective/isolation_forest_pipeline.joblib

Run from spendsense:
python -m ml_lab.inference.predict_pattern_detective

Predictions:
  -1 = anomaly
   1 = typical

Scores:
  decision_function < 0 = anomaly
  Higher anomaly_score = more anomalous

This model was trained on synthetic student expenses.
"""

import json
import math
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_DIR = BASE_DIR / "models" / "pattern_detective"
MODEL_PATH = MODEL_DIR / "isolation_forest_pipeline.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"

CATEGORIES = {
    "Food",
    "Groceries",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Entertainment",
}

FEATURE_COLUMNS = [
    "log_amount",
    "category",
    "day_of_week",
    "day_of_month",
]


@lru_cache(maxsize=1)
def load_pattern_model():
    """Load trusted, locally trained model artifacts once."""

    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Pattern Detective model not found: {MODEL_PATH}"
        )

    if not METADATA_PATH.is_file():
        raise FileNotFoundError(
            f"Pattern Detective metadata not found: {METADATA_PATH}"
        )

    pipeline = joblib.load(MODEL_PATH)

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    return pipeline, metadata


def prepare_expenses(transactions):
    """
    Validate saved transaction records and build ML features.

    Returns:
        features: DataFrame matching training feature schema
        accepted: original transaction data for each feature row
        excluded: count of unsupported/invalid expense records
        excluded_reasons: reason counts

    Income is not considered an expense and is not
    counted as an excluded expense.
    """

    rows = []
    accepted = []
    excluded_reasons = {
        "unsupported_category": 0,
        "invalid_amount": 0,
        "invalid_date": 0,
    }

    for transaction in transactions:
        if str(transaction.get("kind", "")).strip().lower() != "expense":
            continue

        category = str(transaction.get("category", "")).strip()

        if category not in CATEGORIES:
            excluded_reasons["unsupported_category"] += 1
            continue

        try:
            amount = float(transaction.get("amount"))
        except (ValueError, TypeError, OverflowError):
            excluded_reasons["invalid_amount"] += 1
            continue

        if not math.isfinite(amount) or amount <= 0:
            excluded_reasons["invalid_amount"] += 1
            continue

        raw_date = transaction.get("date")

        try:
            if isinstance(raw_date, datetime):
                parsed_date = raw_date.date()
            elif isinstance(raw_date, date):
                parsed_date = raw_date
            else:
                parsed_date = date.fromisoformat(
                    str(raw_date).strip()[:10]
                )
        except (TypeError, ValueError):
            excluded_reasons["invalid_date"] += 1
            continue

        rows.append({
            "log_amount": float(np.log1p(amount)),
            "category": category,
            "day_of_week": parsed_date.weekday(),
            "day_of_month": parsed_date.day,
        })

        accepted.append({
            "id": transaction.get("id"),
            "date": parsed_date.isoformat(),
            "description": str(
                transaction.get("description") or ""
            ),
            "merchant": str(
                transaction.get("merchant") or ""
            ),
            "category": category,
            "kind": "Expense",
            "amount": round(amount, 2),
        })

    features = pd.DataFrame(
        rows,
        columns=FEATURE_COLUMNS,
    )

    return (
        features,
        accepted,
        sum(excluded_reasons.values()),
        excluded_reasons,
    )


def predict_pattern_detective(transactions):
    """
    Score expense transactions using the trained Isolation Forest.

    The pipeline's preprocessing is saved with the model,
    so numeric scaling and category encoding match training.

    No invented confidence or anomaly probabilities.
    """

    (
        features,
        accepted,
        excluded_count,
        excluded_reasons,
    ) = prepare_expenses(transactions)

    if features.empty:
        return {
            "status": "insufficient_data",
            "message": (
                "No supported expenses available for anomaly "
                "detection. Add dated transactions in one of "
                "the eight supported categories."
            ),
            "total_analyzed": 0,
            "anomaly_count": 0,
            "typical_count": 0,
            "excluded_transactions": excluded_count,
            "excluded_reasons": excluded_reasons,
            "transactions": [],
        }

    pipeline, metadata = load_pattern_model()

    predictions = pipeline.predict(features)

    # Higher values = more anomalous.
    anomaly_scores = -pipeline.decision_function(features)

    # Original sklearn score_samples: lower = more anomalous.
    raw_scores = pipeline.score_samples(features)

    results = []

    for transaction, prediction, score, raw_score in zip(
        accepted,
        predictions,
        anomaly_scores,
        raw_scores,
    ):
        flagged = int(prediction) == -1

        results.append({
            **transaction,
            "is_anomaly": flagged,
            "prediction": (
                "Review" if flagged else "Typical"
            ),
            "anomaly_score": round(float(score), 6),
            "raw_isolation_score": round(
                float(raw_score), 6
            ),
            "decision_threshold": 0.0,
            "reason": (
                "This transaction is unusual relative "
                "to the model's synthetic training distribution."
                if flagged else
                "This transaction falls within the model's "
                "typical region for synthetic training data."
            ),
        })

    # Highest anomaly scores first.
    results.sort(
        key=lambda item: item["anomaly_score"],
        reverse=True,
    )

    anomaly_count = sum(
        item["is_anomaly"] for item in results
    )

    return {
        "status": "ok",
        "model": {
            "name": metadata.get(
                "model_name",
                "SpendSense Pattern Detective",
            ),
            "algorithm": "Isolation Forest",
            "training_data": metadata.get(
                "training_data",
                "Synthetic typical expenses",
            ),
            "contamination": metadata.get(
                "contamination", 0.05
            ),
            "features": metadata.get(
                "features", FEATURE_COLUMNS
            ),
        },
        "total_analyzed": len(results),
        "anomaly_count": anomaly_count,
        "typical_count": len(results) - anomaly_count,
        "excluded_transactions": excluded_count,
        "excluded_reasons": excluded_reasons,
        "transactions": results,
        "disclaimer": (
            "Anomaly flags describe deviations from a "
            "synthetic training distribution. They are not "
            "fraud predictions, personal financial diagnoses, "
            "or calibrated probabilities."
        ),
    }


def main():
    """Smoke test using illustrative transactions."""

    sample_transactions = [
        {
            "id": 1,
            "date": "2026-11-20",
            "description": "Campus lunch",
            "kind": "Expense",
            "category": "Food",
            "amount": 350,
        },
        {
            "id": 2,
            "date": "2026-11-21",
            "description": "Large restaurant bill",
            "kind": "Expense",
            "category": "Food",
            "amount": 8500,
        },
        {
            "id": 3,
            "date": "2026-11-22",
            "description": "Bus fare",
            "kind": "Expense",
            "category": "Transport",
            "amount": 180,
        },
    ]

    result = predict_pattern_detective(
        sample_transactions
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
