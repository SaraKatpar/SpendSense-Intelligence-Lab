
"""
SpendSense Intelligence Lab
Pattern Detective - Isolation Forest Training

Unsupervised anomaly detection for student expenses.

Training data: synthetic
Evaluation: synthetic normal expenses + injected anomalies

Run from the spendsense directory:

python -m ml_lab.train_pattern_detective
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
)
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)
from sklearn.pipeline import Pipeline


# ============================================================
# 1. CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models" / "pattern_detective"
EVAL_DIR = BASE_DIR / "evaluation"

for folder in (DATA_DIR, MODEL_DIR, EVAL_DIR):
    folder.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

CATEGORIES = [
    "Food",
    "Groceries",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Entertainment",
]

FEATURES = [
    "log_amount",
    "category",
    "day_of_week",
    "day_of_month",
]

# Synthetic typical amounts in PKR.
# These are assumptions, not measured student spending.
CATEGORY_CONFIG = {
    "Food": (350, 0.40),
    "Groceries": (950, 0.45),
    "Transport": (250, 0.45),
    "Shopping": (1400, 0.60),
    "Bills": (1800, 0.40),
    "Health": (700, 0.55),
    "Education": (1100, 0.55),
    "Entertainment": (650, 0.55),
}

CATEGORY_PROBABILITIES = [
    0.28,
    0.13,
    0.18,
    0.10,
    0.10,
    0.05,
    0.09,
    0.07,
]


# ============================================================
# 2. SYNTHETIC DATA GENERATION
# ============================================================

def generate_expenses(
    count,
    inject_anomalies=False,
    anomaly_fraction=0.10,
):
    """
    Generate synthetic student expense transactions.

    Labels:
      0 = generated typical expense
      1 = deliberately injected anomaly

    Labels are ONLY used for evaluation.
    """

    categories = rng.choice(
        CATEGORIES,
        size=count,
        p=CATEGORY_PROBABILITIES,
    )

    dates = pd.to_datetime("2026-01-01") + pd.to_timedelta(
        rng.integers(0, 300, size=count),
        unit="D",
    )

    amounts = []

    for category in categories:
        median, sigma = CATEGORY_CONFIG[category]

        amount = rng.lognormal(
            mean=np.log(median),
            sigma=sigma,
        )

        amounts.append(round(max(10, amount), 2))

    frame = pd.DataFrame({
        "date": dates,
        "category": categories,
        "amount": amounts,
        "injected_anomaly": np.zeros(
            count, dtype=int
        ),
    })

    if inject_anomalies:
        anomaly_count = round(
            count * anomaly_fraction
        )

        anomaly_indices = rng.choice(
            count,
            size=anomaly_count,
            replace=False,
        )

        # Inject unusually large amounts.
        # This is only one type of possible anomaly.
        multipliers = rng.uniform(
            8, 20, size=anomaly_count
        )

        frame.loc[
            anomaly_indices, "amount"
        ] = (
            frame.loc[
                anomaly_indices, "amount"
            ].to_numpy() * multipliers
        ).round(2)

        frame.loc[
            anomaly_indices, "injected_anomaly"
        ] = 1

    return frame


# ============================================================
# 3. FEATURE ENGINEERING
# ============================================================

def build_features(frame):
    """
    Convert expense transactions into ML features.

    Uses the same transformations during training
    and later inference.
    """

    result = frame.copy()

    result["date"] = pd.to_datetime(
        result["date"],
        errors="raise",
    )

    result["amount"] = pd.to_numeric(
        result["amount"],
        errors="raise",
    )

    if (
        result["amount"].isna().any()
        or (result["amount"] <= 0).any()
        or not np.isfinite(
            result["amount"].to_numpy()
        ).all()
    ):
        raise ValueError(
            "Expense amounts must be finite and positive."
        )

    result["log_amount"] = np.log1p(
        result["amount"]
    )

    result["day_of_week"] = (
        result["date"].dt.dayofweek
    )

    result["day_of_month"] = (
       result["date"].dt.day_of_week
    )

    return result[FEATURES]


# ============================================================
# 4. CREATE TRAIN / TEST DATA
# ============================================================

def prepare_data():
    print("\nGenerating synthetic student expenses...")

    train = generate_expenses(
        count=10000,
        inject_anomalies=False,
    )

    test = generate_expenses(
        count=2500,
        inject_anomalies=True,
        anomaly_fraction=0.10,
    )

    train.to_csv(
        DATA_DIR / "pattern_detective_train.csv",
        index=False,
    )

    test.to_csv(
        DATA_DIR / "pattern_detective_test.csv",
        index=False,
    )

    print("Training transactions:", len(train))
    print("Test transactions:", len(test))
    print(
        "Injected test anomalies:",
        int(test["injected_anomaly"].sum()),
    )

    return train, test


# ============================================================
# 5. PREPROCESSING PIPELINE
# ============================================================

def create_pipeline():
    numeric_features = [
        "log_amount",
        "day_of_week",
        "day_of_month",
    ]

    categorical_features = [
        "category",
    ]

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                numeric_features,
            ),
            (
                "category",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                categorical_features,
            ),
        ],
        sparse_threshold=0,
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    return Pipeline([
        ("preprocessor", preprocessing),
        ("model", model),
    ])


# ============================================================
# 6. TRAIN MODEL
# ============================================================

def train_model(train):
    print("\nTraining Isolation Forest...")

    pipeline = create_pipeline()

    X_train = build_features(train)

    pipeline.fit(X_train)

    print("Training complete.")

    return pipeline


# ============================================================
# 7. EVALUATE MODEL
# ============================================================

def evaluate_model(pipeline, test):
    print("\nEvaluating injected anomalies...")

    X_test = build_features(test)

    y_true = test[
        "injected_anomaly"
    ].to_numpy()

    predictions = pipeline.predict(X_test)

    # IsolationForest:
    #  1 = inlier
    # -1 = outlier
    y_pred = (
        predictions == -1
    ).astype(int)

    # Lower decision_function = more anomalous.
    # Negate to make higher values mean more anomalous.
    anomaly_scores = -pipeline.decision_function(
        X_test
    )

    precision = precision_score(
        y_true, y_pred, zero_division=0
    )

    recall = recall_score(
        y_true, y_pred, zero_division=0
    )

    f1 = f1_score(
        y_true, y_pred, zero_division=0
    )

    roc_auc = roc_auc_score(
        y_true, anomaly_scores
    )

    pr_auc = average_precision_score(
        y_true, anomaly_scores
    )

    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    )

    report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=[
            "Typical",
            "Injected anomaly",
        ],
        zero_division=0,
        output_dict=True,
    )

    metrics = {
        "model_name": "SpendSense Pattern Detective",
        "algorithm": "Isolation Forest",
        "learning_type": "Unsupervised anomaly detection",
        "training_data": "Synthetic typical expenses",
        "evaluation_data": (
            "Synthetic holdout with injected large expenses"
        ),
        "training_samples": 10000,
        "test_samples": len(test),
        "injected_anomalies": int(y_true.sum()),
        "contamination": 0.05,
        "features": FEATURES,
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "f1_score": round(float(f1), 6),
        "roc_auc": round(float(roc_auc), 6),
        "average_precision": round(
            float(pr_auc), 6
        ),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "limitations": [
            "All training and test transactions are synthetic.",
            "Injected anomalies are unusually large amounts.",
            "Results do not establish real-world anomaly detection quality.",
            "An anomaly is not evidence of fraud or irresponsible spending.",
            "The model is not personalized to an individual student.",
        ],
    }

    print("\nEvaluation results:")
    print(
        "Precision:",
        f"{precision:.4f}"
    )
    print(
        "Recall:",
        f"{recall:.4f}"
    )
    print(
        "F1 score:",
        f"{f1:.4f}"
    )
    print(
        "ROC AUC:",
        f"{roc_auc:.4f}"
    )
    print(
        "Average Precision:",
        f"{pr_auc:.4f}"
    )

    print("\nConfusion matrix:")
    print(matrix)

    return metrics, anomaly_scores, y_pred


# ============================================================
# 8. SAVE MODEL AND EVALUATION
# ============================================================

def save_outputs(
    pipeline,
    metrics,
    test,
    anomaly_scores,
    predictions,
):
    model_path = (
        MODEL_DIR / "isolation_forest_pipeline.joblib"
    )

    metadata_path = (
        MODEL_DIR / "metadata.json"
    )

    evaluation_path = (
        EVAL_DIR / "pattern_detective_evaluation.json"
    )

    predictions_path = (
        DATA_DIR / "pattern_detective_test_predictions.csv"
    )

    joblib.dump(
        pipeline,
        model_path,
    )

    with metadata_path.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )

    with evaluation_path.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )

    predictions_frame = test.copy()

    predictions_frame["anomaly_score"] = (
        anomaly_scores
    )

    predictions_frame["predicted_anomaly"] = (
        predictions
    )

    predictions_frame.to_csv(
        predictions_path,
        index=False,
    )

    print("\nSaved artifacts:")
    print("Model:", model_path)
    print("Metadata:", metadata_path)
    print("Evaluation:", evaluation_path)
    print("Test predictions:", predictions_path)


# ============================================================
# 9. MAIN
# ============================================================

def main():
    train, test = prepare_data()

    pipeline = train_model(train)

    metrics, scores, predictions = evaluate_model(
        pipeline, test
    )

    save_outputs(
        pipeline,
        metrics,
        test,
        scores,
        predictions,
    )

    print("\n" + "=" * 50)
    print("PATTERN DETECTIVE TRAINING COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    main()
