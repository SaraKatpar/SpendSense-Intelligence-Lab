
from pathlib import Path
import json
import joblib
import numpy as np

# ============================================================
# SPENDSENSE INTELLIGENCE LAB
# Spending DNA - Inference
#
# Loads the trained K-Means model and analyzes
# an individual student's spending distribution.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_DIR = (
    BASE_DIR / "models" / "spending_dna"
)

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


def load_artifacts():
    model_path = (
        MODEL_DIR / "kmeans_model.joblib"
    )

    scaler_path = (
        MODEL_DIR / "scaler.joblib"
    )

    metadata_path = (
        MODEL_DIR / "metadata.json"
    )

    for path in [
        model_path,
        scaler_path,
        metadata_path,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Spending DNA artifact: {path}. "
                "Run train_spending_dna.py first."
            )

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    with open(
        metadata_path,
        "r",
        encoding="utf-8",
    ) as file:
        metadata = json.load(file)

    return model, scaler, metadata


def extract_spending_features(transactions):
    """
    Convert transactions into a category spending profile.

    Expected transaction format:

    {
        "kind": "Expense",
        "category": "Food",
        "amount": 500
    }

    Income transactions are ignored.

    Unknown categories are excluded from the feature
    totals and explicitly reported to the caller.
    """

    totals = {
        category: 0.0
        for category in CATEGORIES
    }

    ignored_transactions = 0
    valid_transactions = 0

    for transaction in transactions:
        if transaction.get("kind") != "Expense":
            continue

        category = transaction.get("category")

        try:
            amount = float(
                transaction.get("amount", 0)
            )
        except (ValueError, TypeError):
            ignored_transactions += 1
            continue

        if (
            category not in totals
            or not np.isfinite(amount)
            or amount <= 0
        ):
            ignored_transactions += 1
            continue

        totals[category] += amount
        valid_transactions += 1

    total_spending = sum(totals.values())

    if total_spending <= 0:
        raise ValueError(
            "At least one valid expense transaction "
            "is required for Spending DNA."
        )

    percentages = {
        category: (
            totals[category] / total_spending
        )
        for category in CATEGORIES
    }

    feature_vector = np.array(
        [
            percentages[category]
            for category in CATEGORIES
        ],
        dtype=float,
    ).reshape(1, -1)

    return {
        "features": feature_vector,
        "totals": totals,
        "percentages": percentages,
        "total_spending": total_spending,
        "valid_transactions": valid_transactions,
        "ignored_transactions": ignored_transactions,
    }


def predict_spending_dna(transactions):
    """
    Assign a student's spending profile to a
    discovered K-Means cluster.

    Returns the assigned cluster and descriptive
    information based on saved training metadata.
    """

    model, scaler, metadata = load_artifacts()

    extracted = extract_spending_features(
        transactions
    )

    X_scaled = scaler.transform(
        extracted["features"]
    )

    cluster_id = int(
        model.predict(X_scaled)[0]
    )

    profile = metadata[
        "cluster_profiles"
    ][str(cluster_id)]

    # Euclidean distance in standardized feature space.
    # This is NOT a calibrated confidence probability.
    centroid = model.cluster_centers_[cluster_id]

    distance = float(
        np.linalg.norm(
            X_scaled[0] - centroid
        )
    )

    return {
        "cluster_id": cluster_id,
        "profile_name": profile["name"],
        "dominant_category": profile[
            "dominant_category"
        ],
        "total_spending": round(
            extracted["total_spending"],
            2,
        ),
        "valid_transactions": extracted[
            "valid_transactions"
        ],
        "ignored_transactions": extracted[
            "ignored_transactions"
        ],
        "category_percentages": {
            category: round(
                value * 100,
                2,
            )
            for category, value in (
                extracted["percentages"].items()
            )
        },
        "category_amounts": {
            category: round(
                amount,
                2,
            )
            for category, amount in (
                extracted["totals"].items()
            )
        },
        "cluster_average_percentages": profile[
            "category_percentages"
        ],
        "distance_to_centroid": round(
            distance,
            4,
        ),
        "model": {
            "algorithm": metadata["algorithm"],
            "selected_k": metadata["selected_k"],
            "training_data": metadata["dataset_type"],
            "silhouette_score": metadata[
                "silhouette_score"
            ],
        },
        "disclaimer": (
            "This cluster assignment is based on a "
            "model trained with synthetic student profiles. "
            "It is descriptive, not a financial diagnosis "
            "or a calibrated probability."
        ),
    }


if __name__ == "__main__":
    example_transactions = [
        {
            "kind": "Expense",
            "category": "Food",
            "amount": 2500,
        },
        {
            "kind": "Expense",
            "category": "Groceries",
            "amount": 800,
        },
        {
            "kind": "Expense",
            "category": "Transport",
            "amount": 500,
        },
        {
            "kind": "Expense",
            "category": "Shopping",
            "amount": 300,
        },
        {
            "kind": "Expense",
            "category": "Bills",
            "amount": 600,
        },
        {
            "kind": "Expense",
            "category": "Education",
            "amount": 400,
        },
    ]

    result = predict_spending_dna(
        example_transactions
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
