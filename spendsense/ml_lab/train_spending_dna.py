
from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

# ============================================================
# SPENDSENSE INTELLIGENCE LAB
# Spending DNA - K-Means Clustering Training
#
# Dataset: Synthetic student spending profiles
# Learning type: Unsupervised learning
# Algorithm: K-Means
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_DIR = BASE_DIR / "models" / "spending_dna"
DATA_DIR = BASE_DIR / "data"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

FEATURE_COLUMNS = [
    f"{category.lower()}_pct"
    for category in CATEGORIES
]

# These archetypes are used ONLY to generate synthetic
# training examples. They are NOT the K-Means output labels.
#
# K-Means will independently discover clusters.

SYNTHETIC_ARCHETYPES = {
    "Food-focused": {
        "Food": 0.38,
        "Groceries": 0.14,
        "Transport": 0.12,
        "Shopping": 0.08,
        "Bills": 0.10,
        "Health": 0.04,
        "Education": 0.08,
        "Entertainment": 0.06,
    },
    "Shopping-focused": {
        "Food": 0.12,
        "Groceries": 0.08,
        "Transport": 0.10,
        "Shopping": 0.36,
        "Bills": 0.10,
        "Health": 0.04,
        "Education": 0.08,
        "Entertainment": 0.12,
    },
    "Education-focused": {
        "Food": 0.13,
        "Groceries": 0.10,
        "Transport": 0.11,
        "Shopping": 0.06,
        "Bills": 0.10,
        "Health": 0.05,
        "Education": 0.39,
        "Entertainment": 0.06,
    },
    "Essentials-focused": {
        "Food": 0.15,
        "Groceries": 0.23,
        "Transport": 0.16,
        "Shopping": 0.05,
        "Bills": 0.24,
        "Health": 0.06,
        "Education": 0.07,
        "Entertainment": 0.04,
    },
}

def generate_synthetic_students(n_students=400):
    """
    Generate synthetic student spending profiles.

    Each student has:
    - A randomly generated monthly expense total
    - Category spending amounts
    - Category spending proportions

    Dirichlet sampling creates variation while ensuring
    all category proportions sum to approximately 1.
    """

    rows = []
    archetypes = list(SYNTHETIC_ARCHETYPES.items())

    for student_index in range(n_students):
        archetype_name, template = archetypes[
            student_index % len(archetypes)
        ]

        center = np.array(
            [template[c] for c in CATEGORIES],
            dtype=float,
        )

        # Larger concentration means profiles stay closer
        # to their archetype while retaining variation.
        concentration = center * 85.0

        proportions = rng.dirichlet(concentration)

        monthly_expenses = float(
            rng.uniform(6000, 35000)
        )

        row = {
            "student_id": f"S{student_index + 1:04d}",
            "synthetic_archetype": archetype_name,
            "monthly_expenses": round(
                monthly_expenses, 2
            ),
        }

        for category, proportion in zip(
            CATEGORIES, proportions
        ):
            row[f"{category.lower()}_amount"] = round(
                monthly_expenses * float(proportion), 2
            )

            row[f"{category.lower()}_pct"] = float(
                proportion
            )

        rows.append(row)

    return pd.DataFrame(rows)


def train():
    print("\n" + "=" * 60)
    print("SPENDSENSE - SPENDING DNA TRAINING")
    print("=" * 60)

    # --------------------------------------------------------
    # STEP 1: Generate synthetic data
    # --------------------------------------------------------

    df = generate_synthetic_students()

    dataset_path = (
        DATA_DIR / "spending_dna_synthetic_students.csv"
    )

    df.to_csv(dataset_path, index=False)

    print(f"\nStudents generated: {len(df)}")
    print(f"Features: {len(FEATURE_COLUMNS)}")
    print(f"Dataset saved: {dataset_path}")

    # --------------------------------------------------------
    # STEP 2: Feature engineering
    # --------------------------------------------------------

    X = df[FEATURE_COLUMNS].to_numpy(
        dtype=float
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # --------------------------------------------------------
    # STEP 3: Compare possible numbers of clusters
    # --------------------------------------------------------

    candidate_results = []

    print("\nEvaluating candidate cluster counts:")

    for k in range(2, 9):
        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_SEED,
            n_init=20,
        )

        labels = model.fit_predict(X_scaled)

        score = silhouette_score(
            X_scaled, labels
        )

        candidate_results.append({
            "k": k,
            "silhouette_score": float(score),
            "inertia": float(model.inertia_),
        })

        print(
            f"K={k} | "
            f"Silhouette={score:.4f} | "
            f"Inertia={model.inertia_:.2f}"
        )

    best_candidate = max(
        candidate_results,
        key=lambda item: item["silhouette_score"],
    )

    best_k = best_candidate["k"]

    print(f"\nSelected K: {best_k}")

    # --------------------------------------------------------
    # STEP 4: Train final K-Means model
    # --------------------------------------------------------

    final_model = KMeans(
        n_clusters=best_k,
        random_state=RANDOM_SEED,
        n_init=20,
    )

    df["cluster"] = final_model.fit_predict(
        X_scaled
    )

    # --------------------------------------------------------
    # STEP 5: Interpret discovered clusters
    # --------------------------------------------------------

    cluster_profiles = {}

    for cluster_id in range(best_k):
        members = df[
            df["cluster"] == cluster_id
        ]

        means = members[
            FEATURE_COLUMNS
        ].mean()

        percentages = {
            category: round(
                float(means[f"{category.lower()}_pct"]) * 100,
                2,
            )
            for category in CATEGORIES
        }

        ranked = sorted(
            percentages.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        dominant_category = ranked[0][0]

        # Descriptive label based on the cluster's
        # actual dominant spending category.
        profile_name = (
            f"{dominant_category} Focused"
        )

        cluster_profiles[str(cluster_id)] = {
            "name": profile_name,
            "dominant_category": dominant_category,
            "student_count": int(len(members)),
            "average_monthly_expenses": round(
                float(members["monthly_expenses"].mean()),
                2,
            ),
            "category_percentages": percentages,
        }

    # --------------------------------------------------------
    # STEP 6: Save model and metadata
    # --------------------------------------------------------

    joblib.dump(
        final_model,
        MODEL_DIR / "kmeans_model.joblib",
    )

    joblib.dump(
        scaler,
        MODEL_DIR / "scaler.joblib",
    )

    metadata = {
        "model_name": "SpendSense Spending DNA",
        "algorithm": "K-Means Clustering",
        "learning_type": "Unsupervised",
        "dataset_type": "Synthetic",
        "students": len(df),
        "features": FEATURE_COLUMNS,
        "categories": CATEGORIES,
        "selected_k": int(best_k),
        "silhouette_score": float(
            silhouette_score(
                X_scaled,
                final_model.labels_,
            )
        ),
        "candidate_results": candidate_results,
        "cluster_profiles": cluster_profiles,
        "limitations": [
            "Training data is synthetic.",
            "Synthetic archetypes influence the patterns.",
            "Silhouette score is measured on training data.",
            "Clusters do not establish real student personalities.",
            "No real-world generalization has been validated.",
        ],
    }

    with open(
        MODEL_DIR / "metadata.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    df.to_csv(
        DATA_DIR / "spending_dna_clustered_students.csv",
        index=False,
    )

    # --------------------------------------------------------
    # STEP 7: Print discovered clusters
    # --------------------------------------------------------

    print("\nDISCOVERED CLUSTERS")
    print("-" * 60)

    for cluster_id, profile in cluster_profiles.items():
        print(
            f"\nCluster {cluster_id}: "
            f"{profile['name']}"
        )

        print(
            "Students:",
            profile["student_count"],
        )

        print(
            "Dominant category:",
            profile["dominant_category"],
        )

        print(
            "Average monthly expenses:",
            profile["average_monthly_expenses"],
        )

        print("Category percentages:")

        for category, value in (
            profile["category_percentages"].items()
        ):
            print(f"  {category}: {value:.2f}%")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print("\nSaved model:")
    print(MODEL_DIR / "kmeans_model.joblib")

    print("\nSaved scaler:")
    print(MODEL_DIR / "scaler.joblib")

    print("\nSaved metadata:")
    print(MODEL_DIR / "metadata.json")

    print(
        "\nFinal silhouette score:",
        round(metadata["silhouette_score"], 4),
    )


if __name__ == "__main__":
    train()
